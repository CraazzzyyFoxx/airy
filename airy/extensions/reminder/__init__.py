from __future__ import annotations

import textwrap

import hikari
import lightbulb

from tortoise.expressions import Q

from airy.core import Airy, AirySlashContext, TimerModel, AiryPlugin
from airy.core.scheduler import ConversionMode
from airy.core.scheduler.timers import ReminderEvent
from airy.utils import ColorEnum, RespondEmbed, time, formats


class ReminderPlugin(AiryPlugin):
    """Reminders to do something."""

    def __init__(self):
        super().__init__(name='Reminder')


plugin = ReminderPlugin()


@plugin.command()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.command("reminder", "Reminds you of something after a certain amount of time.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def reminder(_: lightbulb.SlashContext):
    pass


@reminder.child()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("expires", "Time after which the timer will work. Times are in UTC.", str)
@lightbulb.option("message", "Message", str)
@lightbulb.command("create", "Creates reminders", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_create(ctx: AirySlashContext, expires: str, message: str):
    """Reminds you of something after a certain amount of time.

    The input can be any direct date (e.g. YYYY-MM-DD) or a human-readable offset.

    Examples:
    - "next thursday at 3pm do something funny"
    - "do the dishes tomorrow"
    - "in 3 days do the thing"
    - "2d unmute someone"

    Times are in UTC.
    """

    expires = await ctx.bot.scheduler.convert_time(expires,
                                                   user=ctx.author,
                                                   conversion_mode=ConversionMode.RELATIVE)

    timer = await ctx.bot.scheduler.create_timer(ReminderEvent, expires, ctx.author.id, message)

    delta = time.human_timedelta(expires, source=timer.created)
    await ctx.respond(f"Alright {ctx.author.mention}, in {delta}: {message}")


@reminder.child()
@lightbulb.command("list", "Shows the 10 latest currently running reminders.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_list(ctx: AirySlashContext):
    """Shows the 10 latest currently running reminders."""

    records = (await TimerModel
               .filter(Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]}))
               .order_by('expires')
               .limit(10))
    if len(records) == 0:
        return await ctx.respond('No currently running reminders.', flags=hikari.MessageFlag.EPHEMERAL)

    e = hikari.Embed(colour=ColorEnum.blurple.value, title='Reminders')

    if len(records) == 10:
        e.set_footer(text='Only showing up to 10 reminders.')
    else:
        e.set_footer(text=f'{len(records)} reminder{"s" if len(records) > 1 else ""}')

    for model in records:
        shorten = textwrap.shorten(model.extra.get('args')[1], width=512)
        e.add_field(name=f'{model.id}: {time.format_relative(model.expires)}', value=shorten, inline=False)

    await ctx.respond(embed=e)


@reminder.child()
@lightbulb.option("id", "Reminder ID", int)
@lightbulb.command(name='delete', description="Deletes a reminder by its ID.", pass_options=True)
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_delete(ctx: AirySlashContext, id: int):
    """Deletes a reminder by its ID.

    To get a reminder ID, use the reminder list command.

    You must own the reminder to delete it, obviously.
    """

    timer = await ctx.bot.scheduler.cancel_timer(timer_id=id)

    if not timer:
        return await ctx.respond(embed=RespondEmbed.error('Could not delete any reminders with that ID.'),
                                 flags=hikari.MessageFlag.EPHEMERAL)

    await ctx.respond(embed=RespondEmbed.success('Successfully deleted reminder.'))


@reminder.child()
@lightbulb.command(name='clear', description="Clears all reminders you have set.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_clear(ctx: AirySlashContext):
    """Clears all reminders you have set."""

    # For UX purposes this has to be two queries.
    total = await TimerModel.filter(Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]})).count()

    if total == 0:
        return await ctx.respond(embed=RespondEmbed.error('You do not have any reminders to delete.'))

    status = await ctx.confirm(f'Are you sure you want to delete {formats.Plural(total):reminder}?')
    if status:
        await TimerModel.filter(Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]})).delete()

        # Check if the current timer is the one being cleared and cancel it if so
        if ctx.bot.scheduler.current_timer and ctx.bot.scheduler.current_timer.author_id == ctx.author.id:
            await ctx.bot.scheduler.restart()

        await ctx.respond(embed=RespondEmbed.success(title=f"Successfully",
                                                     description=f"Deleted `{formats.Plural(total):reminder}`."),
                          components=[])

    else:
        await ctx.respond(embed=RespondEmbed.error('Aborting'), components=[])


@plugin.listener(ReminderEvent)
async def on_reminder_timer_complete(timer: ReminderEvent):
    author_id, message = timer.args

    author = plugin.bot.cache.get_user(author_id) or (await plugin.bot.rest.fetch_user(author_id))

    try:
        await author.send(f'{timer.human_delta}: {message}')
    except hikari.HTTPError:
        return


def load(bot: Airy):
    bot.add_plugin(plugin)


def unload(bot: Airy):
    bot.remove_plugin(plugin)
