import logging

import hikari
import lightbulb
import miru

from airy.core import AirySlashContext, AiryPlugin, ActionMenusModel, ActionMenusButtonModel
from airy.utils import RateLimiter, BucketType, helpers, has_permissions, RespondEmbed, FieldPageSource, \
    AiryPages
from .enums import button_styles
from .menu import MenuView

logger = logging.getLogger(__name__)

role_buttons = AiryPlugin("RoleButtons")

role_button_ratelimiter = RateLimiter(2, 1, BucketType.MEMBER, wait=False)


@role_buttons.listener(hikari.RoleDeleteEvent)
async def rolebutton_role_delete_listener(event: hikari.RoleDeleteEvent) -> None:
    models = await ActionMenusModel.filter(guild_id=event.guild_id).all().prefetch_related("buttons")
    for model in models:
        for button in model.buttons:
            if button.payload == str(event.role_id):
                if len(model.buttons) == 1:
                    try:
                        await event.app.rest.delete_message(channel=model.channel_id, message=model.message_id)
                    except (hikari.NotFoundError, hikari.ForbiddenError):
                        pass
                    except hikari.HTTPError:
                        pass
                    await model.delete()
                    return
                else:
                    await button.delete()
                    return


@role_buttons.listener(miru.ComponentInteractionCreateEvent, bind=True)
async def rolebutton_listener(plugin: AiryPlugin, event: miru.ComponentInteractionCreateEvent) -> None:
    """Statelessly listen for rolebutton interactions"""

    if not event.interaction.custom_id.startswith("ACM:"):
        return

    role_id = int(event.interaction.custom_id.split(":")[2])

    if not event.context.guild_id:
        return

    role = plugin.app.cache.get_role(role_id)

    if not role:
        embed = RespondEmbed.error(title="Orphaned",
                                   description="The role this button was pointing to was deleted!")
        await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    me = plugin.app.cache.get_member(event.context.guild_id, plugin.bot.user_id)

    if not helpers.includes_permissions(lightbulb.utils.permissions_for(me), hikari.Permissions.MANAGE_ROLES):
        embed = RespondEmbed.error(title="Missing Permissions",
                                   description="Bot does not have `Manage Roles` permissions!")
        await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    await role_button_ratelimiter.acquire(event.context)
    if role_button_ratelimiter.is_rate_limited(event.context):
        embed = RespondEmbed.cooldown(title="Slow Down!",
                                      description="You are clicking too fast!", )

        await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    await event.context.defer(hikari.ResponseType.DEFERRED_MESSAGE_CREATE, flags=hikari.MessageFlag.EPHEMERAL)

    try:
        assert event.context.member is not None

        if role.id in event.context.member.role_ids:
            await event.context.member.remove_role(role, reason=f"Removed by role-button")
            embed = RespondEmbed.success(title="Role removed",
                                         description=f"Removed role: {role.mention}", )
            await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)

        else:
            await event.context.member.add_role(role, reason=f"Granted by role-button")
            embed = RespondEmbed.success(title="Role added",
                                         description=f"Added role: {role.mention}", )
            embed.set_footer(text="If you would like it removed, click the button again!")
            await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)

    except (hikari.ForbiddenError, hikari.HTTPError):
        embed = RespondEmbed.error(title="Insufficient permissions",
                                   description="""Failed adding role due to an issue with permissions and/or role hierarchy! 
                                                  Please contact an administrator!""")
        await event.context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


@role_buttons.command
@lightbulb.command("rolebuttons", "Commands relating to rolebuttons.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def rolebutton(ctx: AirySlashContext) -> None:
    pass


@rolebutton.child
@lightbulb.add_checks(has_permissions(hikari.Permissions.MANAGE_ROLES))
@lightbulb.option("buttonstyle", "The style of the button.", choices=["Blurple", "Grey", "Red", "Green"])
@lightbulb.option("label", "The label that should appear on the button.", required=False)
@lightbulb.option("emoji", "The emoji that should appear in the button.", type=hikari.Emoji, required=False)
@lightbulb.option("role", "The role that should be handed out by the button.", type=hikari.Role)
@lightbulb.option("channel", "The text channel, the message with rolebutton will be attached here.",
                  type=hikari.OptionType.CHANNEL,
                  channel_types=[hikari.ChannelType.GUILD_TEXT])
@lightbulb.command("create", "Creates message with rolebutton in specified channel", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def rolebutton_create(ctx: AirySlashContext,
                            buttonstyle: str,
                            role: hikari.Role,
                            channel: hikari.TextableChannel,
                            emoji: str = None,
                            label: str = None) -> None:
    buttonstyle = buttonstyle or "Grey"
    if emoji:
        try:
            emoji = hikari.Emoji.parse(emoji)
        except ValueError:
            emoji = None
    style = button_styles[buttonstyle.capitalize()]
    view = miru.View()
    button = miru.Button(
        custom_id=f"ACM:{channel.id}:{role.id}",
        emoji=emoji,
        label=label if label else None,
        style=style,
    )
    view.add_item(button)

    embed = hikari.Embed(title="Role buttons")
    try:
        message = await ctx.bot.rest.create_message(channel, embed=embed, components=view.build())
    except hikari.ForbiddenError:
        embed = RespondEmbed.error(
            title="Insufficient permissions",
            description=f"The bot cannot edit the provided message due to insufficient permissions.")
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    model = ActionMenusModel(guild_id=ctx.guild_id, channel_id=channel.id, message_id=message.id)
    await model.save()

    await ActionMenusButtonModel.create(menus_id=model.id,
                                        payload=str(role.id),
                                        style=style,
                                        label=label if label else "",
                                        emoji=emoji)

    embed = RespondEmbed.success(
        title="Done!",
        description=f"A new role button for role {ctx.options.role.mention} in channel "
                    f"<#{message.channel_id}> has been created!", )
    await ctx.respond(embed=embed)


@rolebutton.child
@lightbulb.add_checks(has_permissions(hikari.Permissions.MANAGE_ROLES))
@lightbulb.option("message_link",
                  "The link of a message that MUST be from the bot, the rolebutton will be attached here.")
@lightbulb.command("manage", "Manages the specified message with rolebuttons", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def rolebutton_manage(ctx: AirySlashContext, message_link) -> None:
    message = await helpers.parse_message_link(ctx, message_link)
    if message:
        view = MenuView(ctx, message.channel_id, message.id)
        await view.initial_send()


@rolebutton.child
@lightbulb.add_checks(has_permissions(hikari.Permissions.MANAGE_ROLES))
@lightbulb.command("list", "List all registered rolebuttons on this server.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def rolebutton_list(ctx: AirySlashContext) -> None:
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)

    models = await ActionMenusModel.filter(guild_id=ctx.guild_id).all().prefetch_related("buttons")
    if len(models) == 0:
        await ctx.respond(embed=RespondEmbed.error("Button roles are missing"))
        return

    entries = []
    for model in models:
        buttons_description = []
        for index, button in enumerate(model.buttons, 1):
            buttons_description.append(f"**{index}.** {button.display()}")

        description = f'<#{model.channel_id}>\n'
        description += f'[Message URL](https://discord.com/channels/{model.guild_id}/{model.channel_id}/{model.message_id})\n>>> '
        description += '\n'.join(buttons_description)
        entries.append(hikari.EmbedField(name='\u200b', value=description, inline=True))

    source = FieldPageSource(entries, per_page=1)
    source.embed.title = 'Button Roles'
    pages = AiryPages(source=source, ctx=ctx, compact=True)
    await pages.send(ctx.interaction, responded=True)
