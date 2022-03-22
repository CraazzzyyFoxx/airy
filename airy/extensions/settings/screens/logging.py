async def settings_logging(self) -> None:
    """Show and handle Logging menu."""

    assert isinstance(self.app, SnedBot) and self.last_ctx is not None and self.last_ctx.guild_id is not None

    userlog = self.app.get_plugin("Logging")
    assert userlog is not None

    log_channels = await userlog.d.actions.get_log_channel_ids_view(self.last_ctx.guild_id)

    embed = hikari.Embed(
        title="Logging Settings",
        description="Below you can see a list of logging events and channels associated with them. To change where a certain event's logs should be sent, click on the corresponding button.",
        color=const.EMBED_BLUE,
    )

    me = self.app.cache.get_member(self.last_ctx.guild_id, self.app.user_id)
    assert me is not None
    perms = lightbulb.utils.permissions_for(me)
    if not (perms & hikari.Permissions.VIEW_AUDIT_LOG):
        embed.add_field(
            name="⚠️ Warning!",
            value=f"The bot currently has no permissions to view the audit logs! This will severely limit logging capabilities. Please consider enabling `View Audit Log` for the bot in your server's settings!",
            inline=False,
        )

    options = []

    for log_category, channel_id in log_channels.items():
        channel = self.app.cache.get_guild_channel(channel_id) if channel_id else None
        embed.add_field(
            name=f"{log_event_strings[log_category]}",
            value=channel.mention if channel else "*Not set*",
            inline=True,
        )
        options.append(miru.SelectOption(label=log_event_strings[log_category], value=log_category))

    self.select_screen(OptionsSelect(options=options, placeholder="Select a category..."), parent="Main")
    is_color = await userlog.d.actions.is_color_enabled(self.last_ctx.guild_id)
    self.add_item(BooleanButton(state=is_color, label="Color logs"))

    await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
    await self.wait_for_input()

    if not self.value:
        return

    if isinstance(self.value, tuple) and self.value[0] == "Color logs":
        await self.app.pool.execute(
            """INSERT INTO log_config (color, guild_id) 
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO
            UPDATE SET color = $1""",
            self.value[1],
            self.last_ctx.guild_id,
        )
        await self.app.db_cache.refresh(table="log_config", guild_id=self.last_ctx.guild_id)
        return await self.settings_logging()

    log_event = self.value

    options = []
    options.append(miru.SelectOption(label="Disable", value="disable", description="Stop logging this event."))
    options += [
        miru.SelectOption(label=str(channel.name), value=str(channel.id), emoji=const.EMOJI_CHANNEL)
        for channel in self.app.cache.get_guild_channels_view_for_guild(self.last_ctx.guild_id).values()
        if isinstance(channel, hikari.TextableGuildChannel)
    ]

    embed = hikari.Embed(
        title="Logging Settings",
        description=f"Please select a channel where the following event should be logged: `{log_event_strings[log_event]}`",
        color=const.EMBED_BLUE,
    )

    try:
        channel = await ask_settings(
            self,
            self.last_ctx,
            options=options,
            return_type=hikari.TextableGuildChannel,
            embed_or_content=embed,
            placeholder="Select a channel...",
            ignore=["disable"],
            ephemeral=self.ephemeral,
        )
    except TypeError:
        embed = hikari.Embed(
            title="❌ Channel not found.",
            description="Unable to locate channel. Please type a channel mention or ID.",
            color=const.ERROR_COLOR,
        )
        return await self.error_screen(embed, parent="Logging")
    else:
        channel_id = channel.id if channel != "disable" else None
        userlog = self.app.get_plugin("Logging")
        assert userlog is not None
        await userlog.d.actions.set_log_channel(log_event, self.last_ctx.guild_id, channel_id)

        await self.settings_logging()