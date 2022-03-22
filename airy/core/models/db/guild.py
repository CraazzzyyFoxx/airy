import typing as t

import enum

from tortoise import fields
from tortoise.models import Model


class RaidMode(enum.IntEnum):
    off = 0
    on = 1
    strict = 2


class GuildModel(Model):
    """Defining a guild model to store settings of the guild"""

    guild_id = fields.BigIntField(pk=True)
    raid_mode = fields.IntEnumField(RaidMode, default=RaidMode.off)
    broadcast_channel = fields.BigIntField(null=True)
    mention_count = fields.SmallIntField(null=True)
    mute_role_id = fields.BigIntField(null=True)
    extra: dict = fields.JSONField(default={'muted_members': [], "safe_mention_channel_ids": []})

    @property
    def muted_members(self) -> t.List[int]:
        return self.extra.get('muted_members')

    @muted_members.setter
    def muted_members(self, value):
        self.muted_members = value

    @muted_members.deleter
    def muted_members(self):
        self.muted_members = self.extra['muted_members'] = []

    @property
    def safe_mention_channel_ids(self) -> t.List[int]:
        return self.extra.get('safe_mention_channel_ids')

    @safe_mention_channel_ids.setter
    def safe_mention_channel_ids(self, value):
        self.muted_members = value

    @safe_mention_channel_ids.deleter
    def safe_mention_channel_ids(self):
        self.muted_members = self.extra['safe_mention_channel_ids'] = []

    class Meta:
        """Metaclass to set table name and description"""

        table = "guild"
        table_description = "Stores information about the guild"
