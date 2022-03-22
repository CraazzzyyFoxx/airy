async def settings_automod_policy(self, policy: t.Optional[str] = None) -> None:
    """Settings for an automoderation policy"""

    assert isinstance(self.app, SnedBot) and self.last_ctx is not None and self.last_ctx.guild_id is not None

    if not policy:
        return await self.settings_automod()

    automod = self.app.get_plugin("Auto-Moderation")

    assert automod is not None

    policies: t.Dict[str, t.Any] = await automod.d.actions.get_policies(self.last_ctx.guild_id)
    policy_data = policies[policy]
    embed = hikari.Embed(
        title=f"Options for: {policy_strings[policy]['name']}",
        description=policy_strings[policy]["description"],
        color=const.EMBED_BLUE,
    )

    state = policy_data["state"]
    buttons = []

    if state == "disabled":
        embed.add_field(
            name="ℹ️ Disclaimer:",
            value="More configuration options will appear if you enable/change the state of this entry!",
            inline=False,
        )

    elif state == "escalate" and policies["escalate"]["state"] == "disabled":
        embed.add_field(
            name="⚠️ Warning:",
            value='Escalation action was not set! Please select the "Escalation" policy and set an action!',
            inline=False,
        )

    elif state in ["flag", "notice"]:
        userlog = self.app.get_plugin("Logging")
        assert userlog is not None
        channel_id = await userlog.d.actions.get_log_channel_id("flags", self.last_ctx.guild_id)
        if not channel_id:
            embed.add_field(
                name="⚠️ Warning:",
                value="State is set to flag or notice, but auto-mod flags are not logged! Please set a log-channel for it in `Logging` settings!",
                inline=False,
            )

    embed.add_field(name="State:", value=state.capitalize(), inline=False)
    buttons.append(OptionButton(label="State", custom_id="state", style=hikari.ButtonStyle.SECONDARY))

    # Conditions for certain attributes to appear
    predicates = {
        "temp_dur": lambda s: s in ["timeout", "tempban"]
                              or s == "escalate" and policies["escalate"]["state"] in ["timeout", "tempban"],
    }

    if policy_data.get("excluded_channels") is not None and policy_data.get("excluded_roles") is not None:
        """Exclusions calculations"""

        excluded_channels = [
            self.app.cache.get_guild_channel(channel_id) for channel_id in policy_data["excluded_channels"]
        ]
        excluded_roles = [self.app.cache.get_role(role_id) for role_id in policy_data["excluded_roles"]]
        excluded_channels = list(filter(None, excluded_channels))
        excluded_roles = list(filter(None, excluded_roles))

        all_channels = [
            channel
            for channel in self.app.cache.get_guild_channels_view_for_guild(self.last_ctx.guild_id).values()
            if isinstance(channel, hikari.TextableGuildChannel)
        ]
        included_channels = list(set(all_channels) - set(excluded_channels))  # type: ignore

        all_roles = [
            role
            for role in self.app.cache.get_roles_view_for_guild(self.last_ctx.guild_id).values()
            if role.id != self.last_ctx.guild_id
        ]
        included_roles = list(set(all_roles) - set(excluded_roles))

    if state != "disabled":
        for key in policy_data:
            if key == "state":
                continue

            if predicate := predicates.get(key):
                if not predicate(state):
                    continue

            if key in ["excluded_channels", "excluded_roles"]:
                continue

            value = (
                policy_data[key]
                if not isinstance(policy_data[key], dict)
                else "\n".join(
                    [
                        f"{polkey.replace('_', ' ').title()}: `{str(value)}`"
                        for polkey, value in policy_data[key].items()
                    ]
                )
            )
            value = value if not isinstance(policy_data[key], list) else ", ".join(policy_data[key])
            if len(str(value)) > 512:  # Account for long field values
                value = str(value)[: 512 - 3] + "..."

            embed.add_field(
                name=policy_fields[key]["name"],
                value=policy_fields[key]["value"].format(value=value),
                inline=False,
            )
            buttons.append(
                OptionButton(label=policy_fields[key]["label"], custom_id=key, style=hikari.ButtonStyle.SECONDARY)
            )

        if policy_data.get("excluded_channels") is not None and policy_data.get("excluded_roles") is not None:
            display_channels = ", ".join(
                [channel.mention for channel in excluded_channels])  # type: ignore it's not unbound, trust me c:
            display_roles = ", ".join([role.mention for role in excluded_roles])  # type: ignore

            if len(display_channels) > 512:
                display_channels = display_channels[: 512 - 3] + "..."

            if len(display_roles) > 512:
                display_roles = display_roles[: 512 - 3] + "..."

            embed.add_field(
                name=policy_fields["excluded_channels"]["name"],
                value=display_channels if excluded_channels else "*None set*",  # type: ignore
                inline=False,
            )

            embed.add_field(
                name=policy_fields["excluded_roles"]["name"],
                value=display_roles if excluded_roles else "*None set*",  # type: ignore
                inline=False,
            )

            buttons.append(
                OptionButton(
                    label="Channel",
                    emoji="➕",
                    custom_id="add_channel",
                    style=hikari.ButtonStyle.SUCCESS,
                    row=4,
                    disabled=not included_channels,  # type: ignore
                )
            )
            buttons.append(
                OptionButton(
                    label="Role",
                    emoji="➕",
                    custom_id="add_role",
                    style=hikari.ButtonStyle.SUCCESS,
                    row=4,
                    disabled=not included_roles,  # type: ignore
                )
            )
            buttons.append(
                OptionButton(
                    label="Channel",
                    emoji="➖",
                    custom_id="del_channel",
                    style=hikari.ButtonStyle.DANGER,
                    row=4,
                    disabled=not excluded_channels,  # type: ignore
                )
            )
            buttons.append(
                OptionButton(
                    label="Role",
                    emoji="➖",
                    custom_id="del_role",
                    style=hikari.ButtonStyle.DANGER,
                    row=4,
                    disabled=not excluded_roles,  # type: ignore
                )
            )

    if settings_help["policies"].get(policy) is not None:
        buttons.append(OptionButton(label="Help", custom_id="show_help", emoji="❓"))

    self.add_buttons(buttons, parent="Auto-Moderation")
    await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
    await self.wait_for_input()

    if not self.value:
        return

    sql = """
    INSERT INTO mod_config (automod_policies, guild_id)
    VALUES ($1, $2) 
    ON CONFLICT (guild_id) DO
    UPDATE SET automod_policies = $1"""

    # The option that is to be changed
    assert self.last_item is not None
    opt = self.last_item.custom_id

    # Question types
    actions = {
        "show_help": ["show_help"],
        "boolean": ["delete"],
        "text_input": ["temp_dur", "words_list", "words_list_wildcard", "count", "persp_bounds"],
        "ask": ["add_channel", "add_role", "del_channel", "del_role"],
        "select": ["state"],
    }

    # Values that should be converted from & to lists
    # This is only valid for text_input action type
    list_inputs = ["words_list", "words_list_wildcard"]

    # Expected return type for a question
    expected_types = {
        "temp_dur": int,
        "words_list": list,
        "words_list_wildcard": list,
        "count": int,
        "excluded_channels": str,
        "excluded_roles": str,
    }

    action = [key for key in actions if opt in actions[key]][0]

    if opt == "state":  # State changing is a special case, ignore action

        options = [
            miru.SelectOption(
                value=state,
                label=policy_states[state]["name"],
                description=policy_states[state]["description"],
                emoji=policy_states[state]["emoji"],
            )
            for state in policy_states.keys()
            if policy not in policy_states[state]["excludes"]
        ]
        self.select_screen(
            OptionsSelect(options=options, placeholder="Select the state of this policy..."),
            parent="Auto-Moderation",
        )
        embed = hikari.Embed(
            title="Select state...", description="Select a new state for this policy...", color=const.EMBED_BLUE
        )
        await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
        await self.wait_for_input()

        if not self.value:
            return

        policies[policy]["state"] = self.value

    elif action == "boolean":
        policies[policy][opt] = not policies[policy][opt]

    elif opt == "persp_bounds":
        modal = PerspectiveBoundsModal(self, policy_data["persp_bounds"], title="Changing Perspective Bounds...")
        assert isinstance(self.last_ctx, miru.ViewContext)
        await self.last_ctx.respond_with_modal(modal)
        await self.wait_for_input()

        if not self.value:
            return

        try:
            assert isinstance(self.value, dict)
            for key, value in self.value.items():
                self.value[key] = float(value.replace(",", "."))
                if not (0.1 <= float(self.value[key]) <= 1.0):
                    raise ValueError
        except (ValueError, TypeError):
            embed = hikari.Embed(
                title="❌ Invalid Type",
                description=f"One or more values were not floating-point numbers, or were not between `0.1`-`1.0`!",
                color=const.ERROR_COLOR,
            )
            return await self.error_screen(embed, parent="Auto-Moderation Policies", policy=policy)

        policies["perspective"]["persp_bounds"] = self.value

    elif action == "text_input":
        assert opt is not None

        modal = OptionsModal(self, f"Changing {policy_fields[opt]['label']}...")
        # Deepcopy because we store instances for convenience
        text_input = copy.deepcopy(policy_text_inputs[opt])
        # Prefill only bad words
        if opt in list_inputs:
            text_input.value = ", ".join(policies[policy][opt])
        modal.add_item(text_input)

        assert isinstance(self.last_ctx, miru.ViewContext)
        await self.last_ctx.respond_with_modal(modal)
        await self.wait_for_input()

        if not self.value:
            return

        assert isinstance(self.value, dict)
        value = list(self.value.values())[0]

        if opt in list_inputs:
            value = [list_item.strip().lower() for list_item in value.split(",")]
            value = list(filter(None, value))  # Remove empty values

        try:
            value = expected_types[opt](value)
            if isinstance(value, int):
                value = abs(value)
                if value == 0:
                    raise ValueError

        except (TypeError, ValueError):
            embed = hikari.Embed(
                title="❌ Invalid Type",
                description=f"Expected a **number** (that is not zero) for option `{policy_fields[opt]['label']}`.",
                color=const.ERROR_COLOR,
            )
            return await self.error_screen(embed, parent="Auto-Moderation Policies", policy=policy)

        policies[policy][opt] = value

    elif action == "ask":

        if opt in ["add_channel", "add_role", "del_channel", "del_role"]:
            match opt:
                case "add_channel":
                    options = [
                        miru.SelectOption(label=channel.name, value=channel.id, emoji=const.EMOJI_CHANNEL)
                        for channel in included_channels  # type: ignore
                    ]
                    embed = hikari.Embed(
                        title="Auto-Moderation Settings",
                        description="Choose a channel to add to excluded channels!",
                        color=const.EMBED_BLUE,
                    )
                    return_type = hikari.TextableGuildChannel
                case "del_channel":
                    options = [
                        miru.SelectOption(label=channel.name, value=channel.id, emoji=const.EMOJI_CHANNEL)
                        for channel in excluded_channels  # type: ignore
                    ]
                    embed = hikari.Embed(
                        title="Auto-Moderation Settings",
                        description="Choose a channel to remove from excluded channels!",
                        color=const.EMBED_BLUE,
                    )
                    return_type = hikari.TextableGuildChannel
                case "add_role":
                    options = [
                        miru.SelectOption(label=role.name, value=role.id, emoji=const.EMOJI_MENTION)
                        for role in included_roles  # type: ignore
                    ]
                    embed = hikari.Embed(
                        title="Auto-Moderation Settings",
                        description="Choose a role to add to excluded roles!",
                        color=const.EMBED_BLUE,
                    )
                    return_type = hikari.Role
                case "del_role":
                    options = [
                        miru.SelectOption(label=role.name, value=role.id, emoji=const.EMOJI_MENTION)
                        for role in excluded_roles  # type: ignore
                    ]
                    embed = hikari.Embed(
                        title="Auto-Moderation Settings",
                        description="Choose a role to remove from excluded roles!",
                        color=const.EMBED_BLUE,
                    )
                    return_type = hikari.Role

            try:
                value = await ask_settings(
                    self,
                    self.last_ctx,
                    options=options,  # type: ignore
                    embed_or_content=embed,
                    return_type=return_type,  # type: ignore
                    placeholder="Select a value...",
                    ephemeral=self.ephemeral,
                )
                if opt.startswith("add_"):
                    policies[policy][f"excluded_{opt.split('_')[1]}s"].append(value.id)
                elif opt.startswith("del_"):
                    policies[policy][f"excluded_{opt.split('_')[1]}s"].remove(value.id)

            except (TypeError, ValueError):
                embed = hikari.Embed(
                    title="❌ Invalid Type",
                    description=f"Cannot find the channel/role specified or it is not in the excluded roles/channels.",
                    color=const.ERROR_COLOR,
                )
                return await self.error_screen(embed, parent="Auto-Moderation Policies", policy=policy)

    elif action == "show_help":
        embed = settings_help["policies"][policy]
        return await self.error_screen(embed, parent="Auto-Moderation Policies", policy=policy)

    await self.app.pool.execute(sql, json.dumps(policies), self.last_ctx.guild_id)
    await self.app.db_cache.refresh(table="mod_config", guild_id=self.last_ctx.guild_id)
    return await self.settings_automod_policy(policy)