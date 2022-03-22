    async def settings_mod(self) -> None:
        """Show and handle Moderation menu."""
        assert isinstance(self.app, SnedBot) and self.last_ctx is not None and self.last_ctx.guild_id is not None

        mod = self.app.get_plugin("Moderation")
        assert mod is not None
        mod_settings = await mod.d.actions.get_settings(self.last_ctx.guild_id)

        embed = hikari.Embed(
            title="Moderation Settings",
            description="""Below you can see the current moderation settings, to change any of them, press the corresponding button!

Enabling the DM-ing of users will notify them in a direct message when they are punished through any of Sned's moderation commands or auto-moderation.
This does not apply to manually punishing them through Discord built-in commands/tools.

Enabling **ephemeral responses** will show all moderation command responses in a manner where they will be invisible to every user except for the one who used the command.""",
            color=const.EMBED_BLUE,
        )
        buttons = []
        for key, value in mod_settings.items():
            buttons.append(BooleanButton(state=value, label=mod_settings_strings[key]))
            embed.add_field(name=mod_settings_strings[key], value=str(value), inline=True)

        self.add_buttons(buttons, parent="Main")
        await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
        await self.wait_for_input()

        if not self.value:
            return

        option = get_key(mod_settings_strings, self.value[0])

        await self.app.pool.execute(
            f"""
            INSERT INTO mod_config (guild_id, {option})
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO
            UPDATE SET {option} = $2""",
            self.last_ctx.guild_id,
            not mod_settings[option],
        )
        await self.app.db_cache.refresh(table="mod_config", guild_id=self.last_ctx.guild_id)

        await self.settings_mod()

    async def settings_starboard(self) -> None:

        assert isinstance(self.app, SnedBot) and self.last_ctx is not None and self.last_ctx.guild_id is not None

        records = await self.app.db_cache.get(table="starboard", guild_id=self.last_ctx.guild_id, limit=1)
        settings = (
            records[0]
            if records
            else {"is_enabled": False, "channel_id": None, "star_limit": 5, "excluded_channels": []}
        )

        starboard_channel = self.app.cache.get_guild_channel(settings["channel_id"]) if settings["channel_id"] else None
        is_enabled = settings["is_enabled"] if settings["channel_id"] else False

        excluded_channels = (
            [self.app.cache.get_guild_channel(channel_id) for channel_id in settings["excluded_channels"]]
            if settings["excluded_channels"]
            else []
        )
        all_channels = [
            channel
            for channel in self.app.cache.get_guild_channels_view_for_guild(self.last_ctx.guild_id).values()
            if isinstance(channel, hikari.TextableGuildChannel)
        ]
        included_channels = list(set(all_channels) - set(excluded_channels))  # type: ignore

        embed = hikari.Embed(
            title="Starboard Settings",
            description="Below you can see the current settings for this server's starboard! If enabled, users can star messages by reacting with ⭐, and if the number of reactions reaches the specified limit, the message will be sent into the specified starboard channel.",
            color=const.EMBED_BLUE,
        )
        buttons = [
            BooleanButton(state=is_enabled, label="Enable", disabled=not starboard_channel),
            OptionButton(style=hikari.ButtonStyle.SECONDARY, label="Set Channel", emoji=const.EMOJI_CHANNEL),
            OptionButton(style=hikari.ButtonStyle.SECONDARY, label="Limit", emoji="⭐"),
            OptionButton(
                style=hikari.ButtonStyle.SUCCESS,
                label="Excluded",
                emoji="➕",
                row=1,
                custom_id="add_excluded",
                disabled=not included_channels,
            ),
            OptionButton(
                style=hikari.ButtonStyle.DANGER,
                label="Excluded",
                emoji="➖",
                row=1,
                custom_id="del_excluded",
                disabled=not excluded_channels,
            ),
        ]
        embed.add_field(
            "Starboard Channel", starboard_channel.mention if starboard_channel else "*Not set*", inline=True
        )
        embed.add_field("Star Limit", settings["star_limit"], inline=True)
        embed.add_field(
            "Excluded Channels",
            " ".join([channel.mention for channel in excluded_channels if channel])[:512]
            if excluded_channels
            else "*Not set*",
            inline=True,
        )
        self.add_buttons(buttons, parent="Main")
        await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
        await self.wait_for_input()

        if self.value is None:
            return

        if isinstance(self.value, tuple) and self.value[0] == "Enable":
            await self.app.pool.execute(
                """INSERT INTO starboard (is_enabled, guild_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO
                UPDATE SET is_enabled = $1""",
                self.value[1],
                self.last_ctx.guild_id,
            )
            await self.app.db_cache.refresh(table="starboard", guild_id=self.last_ctx.guild_id)
            return await self.settings_starboard()

        if self.value == "Limit":
            modal = OptionsModal(self, title="Changing star limit...")
            modal.add_item(
                miru.TextInput(
                    label="Star Limit",
                    required=True,
                    max_length=3,
                    value=settings["star_limit"],
                    placeholder="Enter a positive integer to be set as the minimum required amount of stars...",
                )
            )
            assert isinstance(self.last_ctx, miru.ViewContext)
            await self.last_ctx.respond_with_modal(modal)
            await self.wait_for_input()

            if not self.value:
                return

            assert isinstance(self.value, dict)
            limit = list(self.value.values())[0]

            try:
                limit = abs(int(limit))
                if limit == 0:
                    raise ValueError

            except (TypeError, ValueError):
                embed = hikari.Embed(
                    title="❌ Invalid Type",
                    description=f"Expected a non-zero **number**.",
                    color=const.ERROR_COLOR,
                )
                return await self.error_screen(embed, parent="Starboard")

            await self.app.pool.execute(
                """INSERT INTO starboard (star_limit, guild_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO
                UPDATE SET star_limit = $1""",
                limit,
                self.last_ctx.guild_id,
            )
            await self.app.db_cache.refresh(table="starboard", guild_id=self.last_ctx.guild_id)
            return await self.settings_starboard()

        if self.value == "Set Channel":
            embed = hikari.Embed(
                title="Starboard Settings",
                description=f"Please select a channel where starred messages will be sent.",
                color=const.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=str(channel.name), value=str(channel.id), emoji=const.EMOJI_CHANNEL)
                for channel in all_channels
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
                embed = hikari.Embed(
                    title="❌ Channel not found.",
                    description="Unable to locate channel. Please type a channel mention or ID.",
                    color=const.ERROR_COLOR,
                )
                return await self.error_screen(embed, parent="Starboard")
            else:
                await self.app.pool.execute(
                    """INSERT INTO starboard (channel_id, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO
                    UPDATE SET channel_id = $1""",
                    channel.id,
                    self.last_ctx.guild_id,
                )
            await self.app.db_cache.refresh(table="starboard", guild_id=self.last_ctx.guild_id)
            return await self.settings_starboard()

        assert self.last_item is not None
        if self.last_item.custom_id == "add_excluded":

            embed = hikari.Embed(
                title="Starboard Settings",
                description="Select a new channel to be added to the list of excluded channels. Users will not be able to star messages from these channels.",
                color=const.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=channel.name, value=channel.id, emoji=const.EMOJI_CHANNEL)
                for channel in included_channels
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
                assert isinstance(channel, hikari.TextableGuildChannel)
                excluded_channels.append(channel)
            except TypeError:
                embed = hikari.Embed(
                    title="❌ Channel not found.",
                    description="Unable to locate channel. Please type a channel mention or ID.",
                    color=const.ERROR_COLOR,
                )
                return await self.error_screen(embed, parent="Starboard")

        elif self.last_item.custom_id == "del_excluded":

            embed = hikari.Embed(
                title="Starboard Settings",
                description="Remove a channel from the list of excluded channels.",
                color=const.EMBED_BLUE,
            )

            options = [
                miru.SelectOption(label=str(channel.name), value=str(channel.id), emoji=const.EMOJI_CHANNEL)
                for channel in excluded_channels
                if channel
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
                if channel in excluded_channels:
                    assert isinstance(channel, hikari.TextableGuildChannel)
                    excluded_channels.remove(channel)
                else:
                    raise TypeError

            except TypeError:
                embed = hikari.Embed(
                    title="❌ Channel not found.",
                    description="Unable to locate channel. Please type a channel mention or ID.",
                    color=const.ERROR_COLOR,
                )
                return await self.error_screen(embed, parent="Starboard")

        await self.app.pool.execute(
            """INSERT INTO starboard (excluded_channels, guild_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO
            UPDATE SET excluded_channels = $1""",
            [channel.id for channel in excluded_channels if channel],
            self.last_ctx.guild_id,
        )

        await self.app.db_cache.refresh(table="starboard", guild_id=self.last_ctx.guild_id)
        await self.settings_starboard()