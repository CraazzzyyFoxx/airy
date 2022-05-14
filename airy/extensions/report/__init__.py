import logging
import typing as t

import hikari
import lightbulb
import miru

from airy.core import AirySlashContext, AiryMessageContext, AiryContext, ReportModel
from airy.static import ColorEnum
from airy.utils import helpers, RespondEmbed

logger = logging.getLogger(__name__)

reports = lightbulb.Plugin("Reports")


class ReportModal(miru.Modal):
    def __init__(self, member: hikari.Member) -> None:
        super().__init__(f"Reporting {member}", autodefer=False)
        self.add_item(
            miru.TextInput(
                label="Reason for the Report",
                placeholder="Please enter why you believe this user should be investigated...",
                style=hikari.TextInputStyle.PARAGRAPH,
                max_length=1000,
                required=True,
            )
        )
        self.add_item(
            miru.TextInput(
                label="Additional Context",
                placeholder="If you have any additional information or proof (e.g. screenshots), please link them here.",
                style=hikari.TextInputStyle.PARAGRAPH,
                max_length=1000,
            )
        )
        self.reason: t.Optional[str] = None
        self.info: t.Optional[str] = None

    async def callback(self, ctx: miru.ModalContext) -> None:
        if not ctx.values:
            return

        for item, value in ctx.values.items():
            assert isinstance(item, miru.TextInput)

            if item.label == "Reason for the Report":
                self.reason = value
            elif item.label == "Additional Context":
                self.info = value

        await ctx.defer(flags=hikari.MessageFlag.EPHEMERAL)


async def report_error(ctx: AiryContext) -> None:
    guild = ctx.get_guild()
    assert guild is not None

    embed = RespondEmbed.error(title="Oops!",
                               description=f"It looks like the moderators of **{guild.name}** "
                                           f"did not enable this functionality.", )

    await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


async def report_perms_error(ctx: AiryContext) -> None:
    embed = RespondEmbed.error(title="Oops!",
                               description=f"It looks like I do not have permissions "
                                           f"to create a message in the reports channel. Please notify a moderator!", )
    await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


async def report(ctx: AiryContext, member: hikari.Member, message: t.Optional[hikari.Message] = None) -> None:
    assert ctx.member is not None and ctx.guild_id is not None

    if member.id == ctx.member.id or member.is_bot:
        embed = RespondEmbed.error(title="Huh?",
                                   description=f"I'm not sure how that would work...", )
        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    record = await ReportModel.filter(guild_id=ctx.guild_id).first()

    if not record or not record.is_enabled:
        return await report_error(ctx)

    channel = ctx.app.cache.get_guild_channel(record.channel_id)
    assert isinstance(channel, hikari.TextableGuildChannel)

    if not channel:
        await ReportModel.update_or_create(defaults={"is_enabled": False}, guild_id=ctx.guild_id)
        return await report_error(ctx)

    me = ctx.app.cache.get_member(ctx.guild_id, ctx.app.user_id)
    assert me is not None

    perms = lightbulb.utils.permissions_in(channel, me)

    if not (perms & hikari.Permissions.SEND_MESSAGES):
        return await report_perms_error(ctx)

    assert ctx.interaction is not None

    modal = ReportModal(member)
    await modal.send(ctx.interaction)
    await modal.wait()

    if not modal.reason:  # Modal was closed/timed out
        return

    role_ids = record.pinged_role_ids
    roles = filter(lambda r: r is not None, [ctx.app.cache.get_role(role_id) for role_id in role_ids])
    role_mentions = [role.mention for role in roles if role is not None]

    embed = hikari.Embed(
        title="⚠️ New Report",
        description=f"""
**Reporter:** {ctx.member.mention} `({ctx.member.id})`
**Reported User:**  {member.mention} `({member.id})`
**Reason:** ```{modal.reason}```
**Additional Context:** ```{modal.info or "Not provided."}```""",
        color=ColorEnum.WARN,
    )

    feedback_embed = hikari.Embed(
        title="✅ Report Submitted",
        description="A moderator will review your report shortly!",
        color=ColorEnum.EMBED_GREEN,
    )

    components = hikari.UNDEFINED

    if message:
        components = (
            miru.View().add_item(miru.Button(label="Associated Message", url=message.make_link(ctx.guild_id))).build()
        )

    await channel.send(
        " ".join(role_mentions) or hikari.UNDEFINED, embed=embed, components=components, role_mentions=True
    )
    await modal.get_response_context().respond(embed=feedback_embed, flags=hikari.MessageFlag.EPHEMERAL)


@reports.command
@lightbulb.option("user", "The user that is to be reported.", type=hikari.Member, required=True)
@lightbulb.command("report", "Report a user to the moderation team of this server.", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def report_cmd(ctx: AirySlashContext, user: hikari.Member) -> None:
    helpers.is_member(user)
    await report(ctx, user)


@reports.command
@lightbulb.command("Report User", "Report the targeted user to the moderation team of this server.", pass_options=True)
@lightbulb.implements(lightbulb.UserCommand)
async def report_user_cmd(ctx: AirySlashContext, target: hikari.Member) -> None:
    helpers.is_member(target)
    await report(ctx, ctx.options.target)


@reports.command
@lightbulb.command(
    "Report Message", "Report the targeted message to the moderation team of this server.", pass_options=True
)
@lightbulb.implements(lightbulb.MessageCommand)
async def report_msg_cmd(ctx: AiryMessageContext, target: hikari.Message) -> None:
    assert ctx.guild_id is not None
    member = ctx.app.cache.get_member(ctx.guild_id, target.author)
    if not member:
        embed = RespondEmbed.error(title="Oops!",
                                   description="It looks like the author of this message already left the server!", )

        await ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
        return

    await report(ctx, member, ctx.options.target)


# def load(bot: Airy) -> None:
#     bot.add_plugin(reports)
#
#
# def unload(bot: Airy) -> None:
#     bot.remove_plugin(reports)
