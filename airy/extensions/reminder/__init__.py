from __future__ import annotations

import datetime
import textwrap
import asyncio

import typing as t

import hikari
import lightbulb

from lightbulb import decorators

from tortoise import exceptions
from tortoise.expressions import Q

from airy.utils import time, formats
from airy.core import TimerModel, AiryPlugin
from airy.utils.time import utcnow

from airy.core import Airy, AirySlashContext
from airy.core.scheduler.timers import BaseTimerEvent, ReminderEvent, timers
from airy.utils import ColorEnum


class ReminderPlugin(AiryPlugin):
    """Reminders to do something."""

    def __init__(self, name):
        super().__init__(name=name)
        self.have_data = asyncio.Event()
        self.current_timer: BaseTimerEvent = None  # type: ignore
        self.task: asyncio.Task = None  # type: ignore

    async def dispatch_timers(self):
        try:
            while True:
                # can only asyncio.sleep for up to ~48 days reliably,
                # so we're gonna to cap it off at 40 days
                # see: http://bugs.python.org/issue20493
                timer = self.current_timer = await self.wait_for_active_timers(days=40)
                now = utcnow()
                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, hikari.GatewayServerClosedConnectionError, exceptions.DBConnectionError):
            self.task.cancel()
            self.task = self.bot.create_task(self.dispatch_timers())

    async def call_timer(self, timer: BaseTimerEvent):
        await TimerModel.filter(id=timer.id).delete()
        await self.bot.dispatch(timer)

    async def get_active_timer(self, days=7):
        record = await TimerModel.filter(expires__lt=utcnow() + datetime.timedelta(days=days)).first()

        if record is None:
            return

        cls = timers.get(record.event)

        if cls is None:
            return

        return cls(id=record.id,
                   app=self.bot,
                   expires=record.expires,
                   created=record.created,
                   args=record.extra.get("args"),
                   kwargs=record.extra.get("kwargs"))

    async def wait_for_active_timers(self, *, days=7):
        timer = await self.get_active_timer(days=days)
        if timer is not None:
            self.have_data.set()
            return timer

        self.have_data.clear()
        self.current_timer = None
        await self.have_data.wait()
        return await self.get_active_timer(days=days)

    async def short_timer_optimisation(self, seconds: t.Union[int, float], timer: ReminderEvent):
        await asyncio.sleep(seconds)
        await self.bot.dispatch(timer)

    async def create_timer(self, cls, when: datetime.datetime, *args, **kwargs):
        # Remove timezone information since the database does not deal with it
        when = when.astimezone(datetime.timezone.utc)
        now = utcnow()

        timer = cls(expires=when, created=now, args=args, kwargs=kwargs)
        delta = (when - now).total_seconds()

        if delta <= 120:
            # a shortcut for small scheduler
            self.bot.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        row = await TimerModel.create(event=timer.event,
                                      extra={'args': args, 'kwargs': kwargs},
                                      expires=when,
                                      now=utcnow())

        timer.id = row.id

        # only set the data check if it can be waited on
        if delta <= (86400 * 40):  # 40 days
            self.have_data.set()

        # check if this timer is earlier than our currently run timer
        if self.current_timer and timer.expires < self.current_timer.expires:
            # cancel the task and re-run it
            self.task.cancel()
            self.task = self.bot.create_task(self.dispatch_timers())

        return timer


plugin = ReminderPlugin(name='Reminder')


@plugin.command()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@decorators.command("reminder", "Reminds you of something after a certain amount of time.")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def reminder(_: lightbulb.SlashContext):
    pass


@reminder.child()
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("when", "Time after which the timer will work. Times are in UTC.", str)
@lightbulb.option("message", "Message", str)
@decorators.command("create", "Creates reminders")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_create(ctx: lightbulb.SlashContext):
    """Reminds you of something after a certain amount of time.

    The input can be any direct date (e.g. YYYY-MM-DD) or a human-readable offset.

    Examples:
    - "next thursday at 3pm do something funny"
    - "do the dishes tomorrow"
    - "in 3 days do the thing"
    - "2d unmute someone"

    Times are in UTC.
    """

    when = await time.UserFriendlyTime(ctx).convert(ctx.options.when)
    message = ctx.options.message

    timer = await plugin.create_timer(ReminderEvent, when, ctx.author.id, message)  # type: ignore
    delta = time.human_timedelta(when, source=timer.created)
    await ctx.respond(f"Alright {ctx.author.mention}, in {delta}: {message}")


@reminder.child()
@decorators.command("list", "Shows the 10 latest currently running reminders.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_list(ctx: lightbulb.SlashContext):
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
@lightbulb.option("id", "Reminder ID", int, required=True)
@decorators.command(name='delete', description="Deletes a reminder by its ID.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_delete(ctx: lightbulb.SlashContext):
    """Deletes a reminder by its ID.

    To get a reminder ID, use the reminder list command.

    You must own the reminder to delete it, obviously.
    """

    status = (await TimerModel
              .filter(Q(id=ctx.options.id) & Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]}))
              .delete())

    if status == 0:
        return await ctx.respond('Could not delete any reminders with that ID.', flags=hikari.MessageFlag.EPHEMERAL)

    # if the current timer is being deleted
    if plugin.current_timer and plugin.current_timer.id == ctx.options.id:
        # cancel the task and re-run it
        plugin.task.cancel()
        plugin.task = plugin.bot.create_task(plugin.dispatch_timers())

    await ctx.respond('Successfully deleted reminder.')


@reminder.child()
@decorators.command(name='clear', description="Clears all reminders you have set.")
@lightbulb.implements(lightbulb.SlashSubCommand)
async def reminder_clear(ctx: AirySlashContext):
    """Clears all reminders you have set."""

    # For UX purposes this has to be two queries.
    total = await TimerModel.filter(Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]})).count()

    if total == 0:
        return await ctx.respond('You do not have any reminders to delete.')

    status = await ctx.confirm(f'Are you sure you want to delete {formats.Plural(total):reminder}?')
    if status:
        await TimerModel.filter(Q(event='reminder') & Q(extra__contains={"args": [ctx.author.id]})).delete()

        # Check if the current timer is the one being cleared and cancel it if so
        if plugin.current_timer and plugin.current_timer.author_id == ctx.author.id:
            plugin.task.cancel()
            plugin.task = plugin.bot.create_task(plugin.dispatch_timers())

        await ctx.respond(f"Successfully deleted {formats.Plural(total):reminder}.", components=[])

    else:
        await ctx.respond('Aborting', components=[])


@plugin.listener(hikari.StartedEvent)
async def on_started(_: hikari.StartedEvent):
    plugin.task = asyncio.create_task(plugin.dispatch_timers())


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
