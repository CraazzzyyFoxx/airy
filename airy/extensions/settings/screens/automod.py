async def settings_automod(self) -> None:
    """Open and handle automoderation main menu"""

    assert isinstance(self.app, SnedBot) and self.last_ctx is not None and self.last_ctx.guild_id is not None

    automod = self.app.get_plugin("Auto-Moderation")

    assert automod is not None

    policies = await automod.d.actions.get_policies(self.last_ctx.guild_id)
    embed = hikari.Embed(
        title="Automoderation Settings",
        description="Below you can see a summary of the current automoderation settings. To see more details about a specific entry or change their settings, select it below!",
        color=const.EMBED_BLUE,
    )

    options = []
    for key in policies.keys():
        embed.add_field(
            name=policy_strings[key]["name"],
            value=policies[key]["state"].capitalize(),
            inline=True,
        )
        # TODO: Add emojies maybe?
        options.append(miru.SelectOption(label=policy_strings[key]["name"], value=key))

    self.select_screen(OptionsSelect(options=options, placeholder="Select a policy..."), parent="Main")
    await self.last_ctx.edit_response(embed=embed, components=self.build(), flags=self.flags)
    await self.wait_for_input()

    if not self.value:
        return
    await self.settings_automod_policy(self.value)