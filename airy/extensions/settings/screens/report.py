from __future__ import annotations

import asyncio
import copy
import json
import logging
import typing as t

import hikari
import lightbulb
import miru
from lightbulb.utils.parser import CONVERTER_TYPE_MAPPING

from airy.core import Airy, AirySlashContext, ReportModel
from airy.utils import helpers, ColorEnum, EmojisEnum, RespondEmbed
from airy.core.models.components import *
from airy.etc.settings_static import *

from . import BaseScreen, SettingsView


class ReportScreen(BaseScreen):
    def __init__(self, settings_view: SettingsView):
        super().__init__(settings_view)

    async def start(self, parent: str = "MAIN"):
        assert isinstance(self.app, Airy) and self.last_ctx is not None and self.last_ctx.guild_id is not None

        model = ReportModel.filter(guild_id=self.last_ctx.guild_id).first()

        if not model:
            model = ReportModel(guild_id=self.last_ctx.guild_id,
                                is_enabled=False,
                                channel_id=None)
            model.pinged_role_ids = []

        all_roles = [
            role.id
            for role in list(self.app.cache.get_roles_view_for_guild(self.last_ctx.guild_id).values())
            if role.id != self.last_ctx.guild_id
        ]
        unadded_roles = list(set(all_roles) - set(model.pinged_role_ids))

        channel = self.app.cache.get_guild_channel(model.channel_id) if model.channel_id else None

        embed = hikari.Embed(
            title="Reports Settings",
            description="Below you can see all settings for configuring the reporting of other users or messages. "
                        "This allows other users to flag suspicious content for review.",
            color=ColorEnum.EMBED_BLUE,
        )
        embed.add_field("Channel", value=channel.mention if channel else "*Not set*", inline=True)
        embed.add_field(name="​", value="​", inline=True)  # Spacer
        embed.add_field(
            "Pinged Roles", value=" ".join([f"<@&{role}>" for role in model.pinged_role_ids if role]) or "*None set*", inline=True
        )

        buttons = [
            BooleanButton(state=model.is_enabled if channel else False, label="Enable", disabled=not channel),
            OptionButton(label="Set Channel", emoji=EmojisEnum.TEXT_CHANNEL, style=hikari.ButtonStyle.SECONDARY),
            OptionButton(
                label="Role",
                disabled=not unadded_roles,
                custom_id="add_r",
                emoji="➕",
                style=hikari.ButtonStyle.SUCCESS
            ),
            OptionButton(
                label="Role",
                disabled=not model.pinged_role_ids,
                custom_id="del_r",
                emoji="➖",
                style=hikari.ButtonStyle.DANGER
            ),
        ]
        self.add_buttons(buttons, parent="Main")
        await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
        await self.wait_for_input()

        if not self.value:
            return

        if isinstance(self.value, tuple) and self.value[0] == "Enable":
            await self.app.pool.execute(
                """INSERT INTO reports (is_enabled, guild_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO
                UPDATE SET is_enabled = $1""",
                self.value[1],
                self.last_ctx.guild_id,
            )
            await self.app.db_cache.refresh(table="reports", guild_id=self.last_ctx.guild_id)
            return await self.settings_report()

        if self.value == "Set Channel":
            embed = hikari.Embed(
                title="Reports Settings",
                description=f"Please select a channel where reports will be sent.",
                color=ColorEnum.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=channel.name, value=channel.id, emoji=const.EMOJI_CHANNEL)  # type: ignore
                for channel in self.app.cache.get_guild_channels_view_for_guild(self.last_ctx.guild_id).values()
                if isinstance(channel, hikari.TextableGuildChannel)
            ]

            try:
                channel = await ask_settings(
                    self,
                    self.last_ctx,
                    options=options,
                    return_type=hikari.TextableGuildChannel,
                    embed_or_content=embed,
                    placeholder="Select a channel...",
                    ephemeral=self.ephemeral,
                )
            except TypeError:
                embed = RespondEmbed.error(title="Channel not found.",
                                           description="Unable to locate channel. Please type a channel mention or ID.", )
                return await self.error_screen(embed, parent="Reports")

            else:
                await self.app.pool.execute(
                    """INSERT INTO reports (channel_id, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO
                    UPDATE SET channel_id = $1""",
                    channel.id,
                    self.last_ctx.guild_id,
                )
            await self.app.db_cache.refresh(table="reports", guild_id=self.last_ctx.guild_id)
            return await self.settings_report()

        assert self.last_item and self.last_item.custom_id

        if self.last_item.custom_id == "add_r":

            embed = hikari.Embed(
                title="Reports Settings",
                description="Select a role to add to the list of roles that will be mentioned when a new report is made.",
                color=ColorEnum.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=role.name, value=str(role.id), emoji=const.EMOJI_MENTION)
                for role in unadded_roles
            ]

            try:
                role = await ask_settings(
                    self,
                    self.last_ctx,
                    options=options,
                    return_type=hikari.Role,
                    embed_or_content=embed,
                    placeholder="Select a role...",
                    ephemeral=self.ephemeral,
                )
                assert isinstance(role, hikari.Role)
                pinged_roles.append(role)
            except TypeError:
                embed = RespondEmbed.error(title="Role not found.",
                                           description="Unable to locate role. Please type a role mention or ID.")
                return await self.error_screen(embed, parent="Reports")

        elif self.last_item.custom_id == "del_r":

            embed = hikari.Embed(
                title="Reports Settings",
                description="Remove a role from the list of roles that is mentioned when a new report is made.",
                color=ColorEnum.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=role.name, value=str(role.id), emoji=const.EMOJI_MENTION)
                for role in pinged_roles
                if role is not None
            ]

            try:
                role = await ask_settings(
                    self,
                    self.last_ctx,
                    options=options,
                    return_type=hikari.Role,
                    embed_or_content=embed,
                    placeholder="Select a role...",
                    ephemeral=self.ephemeral,
                )
                if role in pinged_roles:
                    assert isinstance(role, hikari.Role)
                    pinged_roles.remove(role)
                else:
                    raise TypeError

            except TypeError:
                embed = RespondEmbed.error(title="Role not found.",
                                           description="Unable to locate role. Please type a role mention or ID.", )
                return await self.error_screen(embed, parent="Reports")

        await self.app.pool.execute(
            """INSERT INTO reports (pinged_role_ids, guild_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO
            UPDATE SET pinged_role_ids = $1""",
            [role.id for role in pinged_roles if role is not None],
            self.last_ctx.guild_id,
        )

        await self.app.db_cache.refresh(table="reports", guild_id=self.last_ctx.guild_id)
        await self.settings_report()


