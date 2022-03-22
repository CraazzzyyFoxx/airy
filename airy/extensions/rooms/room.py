import asyncio

import typing as t

import hikari

from airy.core.models import VoiceChannelCreatorModel
from .cache import Cache


class VoiceCategory:
    def __init__(self,
                 cache: Cache,
                 config: VoiceChannelCreatorModel):

        self.cache = cache
        self.config = config

        self.category: hikari.GuildCategory
        self.rooms: t.List[VoiceRoom] = []

    @property
    def bot(self):
        return self.cache.bot

    @property
    def id(self):
        return self.category.id

    def get_perms(self, invoked_channel: hikari.GuildChannel):
        if self.config.sync_permissions:
            return invoked_channel.permission_overwrites.values()
        return hikari.UNDEFINED

    def get_free_channel_number(self):
        if self.rooms is None:
            number = 1
        else:
            if len(self.rooms) == 0:
                return 1
            numbers = [room.number for room in self.rooms]

            if len(self.rooms) == max(numbers):
                number = max(numbers) + 1
            else:
                full_numbers = [number for number in range(1, max(len(numbers), max(numbers)))]
                number = min(set(full_numbers) - set(numbers))

        return number

    async def create(self, invoked_channel: hikari.GuildChannel):
        if invoked_channel.parent_id:
            position = self.bot.cache.get_guild_channel(invoked_channel.parent_id).position
        else:
            position = invoked_channel.position

        position = position + self.cache.get_category_position(invoked_channel.id)

        self.category = await self.bot.rest.create_guild_category(guild=self.config.guild_id,
                                                                  name=self.config.additional_category_name,
                                                                  position=position,
                                                                  permission_overwrites=self.get_perms(invoked_channel)
                                                                  )
        self.cache.add_category(invoked_channel.id, self)

    async def delete(self):
        if len(self.rooms) == 0:
            channels = self.bot.cache.get_guild_channels_view_for_guild(self.category.guild_id)

            tasks = [self.bot.create_task(channel.delete()) for channel in channels.values()
                     if channel.parent_id == self.category.id]

            if len(tasks) > 0:
                await asyncio.wait(tasks)

            await self.bot.rest.delete_channel(self.category.id)

            self.cache.remove_category(self.config.channel_id, self)
            del self

    @classmethod
    def from_dict(cls, data: dict):
        pass

    def to_dict(self):
        pass


class VoiceRoom:
    def __init__(self,
                 cache: Cache,
                 config: VoiceChannelCreatorModel,
                 owner: hikari.Member,
                 ):

        self.cache = cache
        self.config = config
        self.owner = owner

        self._is_live = True
        self.members: t.List[hikari.Member] = [owner]

        self.number: int
        self.channel: hikari.GuildVoiceChannel

        self.bot.create_task(self._loop())

    def __repr__(self):
        return f'<VoiceRoom guild_id={self.config.guild_id}, channel={self.channel.id}, owner={self.owner.id}, ' \
               f'user_limit={self.config.user_limit}, number={self.number}>'

    @property
    def bot(self):
        return self.cache.bot

    @property
    def base_perms(self):
        return hikari.Permissions.MANAGE_CHANNELS if self.config.editable else hikari.Permissions.NONE

    def get_perms(self, invoked_channel):
        perms = [hikari.PermissionOverwrite(id=self.owner.id,
                                            type=hikari.PermissionOverwriteType.MEMBER,
                                            allow=self.base_perms)]
        if len(self.members) > 1:
            for member in self.members.copy().remove(self.owner):
                perms.append(hikari.PermissionOverwrite(id=member.id,
                                                        type=hikari.PermissionOverwriteType.MEMBER,
                                                        deny=self.base_perms))

        if self.config.sync_permissions:
            perms.extend(invoked_channel.permission_overwrites.values())

        return perms

    async def create(self, channel_id):
        invoked_channel = self.bot.cache.get_guild_channel(channel_id)
        category = self.cache.get_free_category(channel_id=invoked_channel.id)
        if category is None:
            category = VoiceCategory(self.cache, self.config)
            await category.create(invoked_channel=invoked_channel)

        self.number = category.get_free_channel_number()
        name = f'{self.config.channel_name} {self.number}' if self.config.auto_inc else self.config.channel_name

        self.channel = await self.bot.rest.create_guild_voice_channel(guild=self.config.guild_id,
                                                                      category=category.category,
                                                                      name=name,
                                                                      user_limit=self.config.user_limit,
                                                                      permission_overwrites=self.get_perms(invoked_channel)
                                                                      )
        category.rooms.append(self)
        self.category = category

        await self.bot.rest.edit_member(guild=self.config.guild_id,
                                        voice_channel=self.channel.id,
                                        user=self.owner)

    async def delete(self):
        # await asyncio.sleep(10)

        self.category.rooms.remove(self)
        await self.channel.delete()

        invoked_channel = self.bot.cache.get_guild_channel(self.config.channel_id)
        if self.channel.parent_id != invoked_channel.parent_id:
            await self.category.delete()

    async def _loop(self):
        await self.create(self.config.channel_id)

        while self._is_live:
            await self._check_state()

        await self.delete()
        del self

    async def _check_state(self):
        event: hikari.VoiceStateUpdateEvent = await self.bot.wait_for(hikari.VoiceStateUpdateEvent,
                                                                      timeout=None)

        if event.state is not None:
            if event.state.channel_id == self.channel.id:
                self.members.append(event.state.member)
        if event.old_state:
            if event.old_state.channel_id == self.channel.id:
                self.members.remove(event.state.member)

            if len(self.members) == 0:
                self._is_live = False
                return

            if self.owner not in self.members:
                self.owner = self.members[0]

        return

    @classmethod
    def from_dict(cls, data: dict):
        pass

    def to_dict(self):
        pass
