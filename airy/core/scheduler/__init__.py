from __future__ import annotations

import asyncio
import datetime
import logging
import re
import typing as t

import Levenshtein as lev
import dateparser
import hikari
from hikari.internal.enums import Enum

from airy.core.models import TimerModel, UserModel
from airy.core.tasks import IntervalLoop
from airy.utils import utcnow
from .consts import *
from .timers import BaseTimerEvent, timers

if t.TYPE_CHECKING:
    from ..bot import Airy


__all__ = ("ConversionMode",
           "Scheduler",
           "BaseTimerEvent")

BaseTimerEventT = t.TypeVar('BaseTimerEventT', bound=BaseTimerEvent)
logger = logging.getLogger("airy.core.Scheduler")


class ConversionMode(int, Enum):
    """All possible time conversion modes."""

    RELATIVE = 0
    ABSOLUTE = 1


class Scheduler:
    """
    All timer-related functionality, including time conversion from strings,
    creation, scheduling & dispatching of timers.
    Essentially the internal scheduler of the bot.
    """

    compiled = re.compile(r"""(?:(?P<years>[0-9])(?:years?|y))?               # e.g. 2y
                                 (?:(?P<months>[0-9]{1,2})(?:months?|mo))?     # e.g. 2mo
                                 (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?        # e.g. 10w
                                 (?:(?P<days>[0-9]{1,5})(?:days?|d))?          # e.g. 14d
                                 (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?        # e.g. 12h
                                 (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?    # e.g. 10m
                                 (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?    # e.g. 15s
                              """, re.VERBOSE)

    def __init__(self, bot: Airy) -> None:
        self.bot: Airy = bot
        self._current_timer: t.Optional[TimerModel] = None  # Currently, active timer that is being awaited
        self._dispatching_task: t.Optional[asyncio.Task] = None  # Current task that is handling current_timer
        self._timer_loop: IntervalLoop = IntervalLoop(self._wait_for_active_timers, hours=1.0)

    @property
    def current_timer(self):
        return self._current_timer

    async def start(self):
        self._timer_loop.start()

    async def restart(self) -> None:
        """
        Restart the scheduler system.
        """
        if self._dispatching_task is not None:
            self._dispatching_task.cancel()
        self._dispatching_task = None
        self._current_timer = None
        self._timer_loop.cancel()
        self._timer_loop.start()
        logger.info("The scheduler was restarted.")

    def prepare_timer(self, model: TimerModel) -> t.Optional[BaseTimerEvent]:
        cls = timers.get(model.event)

        if cls is None:
            return

        return cls(id=model.id,
                   app=self.bot,
                   expires=model.expires,
                   created=model.created,
                   args=model.extra.get("args"),
                   kwargs=model.extra.get("kwargs"))

    async def get_latest_timer(self, days: int = 7) -> t.Optional[BaseTimerEvent]:
        """Gets the latest timer in the specified range of days.

        Parameters
        ----------
        days : int, optional
            The maximum expiry of the timer, by default 5

        Returns
        -------
        Optional[Timer]
            The timer object that was found, if any.
        """
        await self.bot.wait_until_started()
        model = await TimerModel.filter(expires__lt=utcnow() + datetime.timedelta(days=days)).first()

        return self.prepare_timer(model)

    async def _call_timer(self, timer: BaseTimerEvent) -> None:
        """Calls the provided timer, dispatches TimerCompleteEvent, and removes the timer object from
        the database.

        Parameters
        ----------
        timer : BaseTimerEvent
            The timer to be called.
        """

        await TimerModel.filter(id=timer.id).delete()
        await self.bot.dispatch(timer)

        self._current_timer = None

        await self.bot.dispatch(timer)
        logger.info(f"Dispatched TimerCompleteEvent for {timer.event} (ID: {timer.id})")

    async def short_timer_optimisation(self, seconds: t.Union[int, float], timer: BaseTimerEvent):
        await asyncio.sleep(seconds)
        await self.bot.dispatch(timer)

    async def _dispatch_timers(self):
        """
        A task that loops, waits for, and calls pending timers.
        """
        try:
            while self.bot.is_ready:
                timer = await self.get_latest_timer(days=30)
                self._current_timer = timer

                now = utcnow()

                if not timer:
                    break

                if timer.expires >= now:
                    sleep_time = (timer.expires - now).total_seconds()
                    logger.info(f"Awaiting next timer: '{timer.event}' (ID: {timer.id}), which is in {sleep_time}s")
                    await asyncio.sleep(sleep_time)

                # TODO: Maybe some sort of queue system so we do not spam out timers like crazy after restart?
                logger.info(f"Dispatching timer: {timer.event} (ID: {timer.id})")
                await self._call_timer(timer)

        except asyncio.CancelledError:
            raise
        except (OSError, hikari.GatewayServerClosedConnectionError):
            if self._dispatching_task:
                self._dispatching_task.cancel()
            self._dispatching_task = asyncio.create_task(self._dispatch_timers())

    async def _wait_for_active_timers(self) -> None:
        """
        Check every hour to see if new timers meet criteria in the database.
        """
        await self.bot.wait_until_started()

        if self._dispatching_task is None:
            self._current_task = asyncio.create_task(self._dispatch_timers())

    async def create_timer(self, cls: t.Type[BaseTimerEventT],
                           expires: datetime.datetime,
                           *args,
                           **kwargs,
                           ) -> BaseTimerEvent:
        """Create a new timer and schedule it.

        Parameters
        ----------
        cls: typing.Type[BaseTimerEventT]
            The expiry date of the timer. Must be in the future.
        expires : datetime.datetime
            The expiry date of the timer. Must be in the future.
        Returns
        -------
        Timer
            The timer object that got created.
        """

        expires = expires.astimezone(datetime.timezone.utc)
        now = utcnow()

        timer = cls(expires=expires, created=now, args=args, kwargs=kwargs)
        delta = (expires - now).total_seconds()

        if delta <= 120:
            # a shortcut for small scheduler
            self.bot.create_task(self.short_timer_optimisation(delta, timer))
            return timer

        model = await TimerModel.create(event=timer.event,
                                        expires=expires,
                                        now=now,
                                        extra={'args': args, 'kwargs': kwargs})

        timer.id = model.id

        # If there is already a timer in queue, and it has an expiry that is further than the timer we just created
        # then we restart the dispatch_timers() to re-check for the latest timer.
        if self._current_timer and timer.expires < self._current_timer.expires:
            logger.debug("Reshuffled timers, created timer is now the latest timer.")
            if self._dispatching_task:
                self._dispatching_task.cancel()
            self._dispatching_task = asyncio.create_task(self._dispatch_timers())

        elif self._current_timer is None:
            self._dispatching_task = asyncio.create_task(self._dispatch_timers())

        return timer

    async def update_timer(self, timer: BaseTimerEvent) -> None:
        """Update a currently running timer, replacing it with the specified timer object.
        If needed, reshuffles timers.

        Parameters
        ----------
        timer : Timer
            The timer object to update.
        """
        await TimerModel.filter(id=timer.id).update(args=timer.args,
                                                    kwargs=timer.kwargs,
                                                    expires=timer.expires)

        if self._current_timer and timer.expires < self._current_timer.expires:
            logger.debug("Reshuffled timers, created timer is now the latest timer.")
            if self._dispatching_task:
                self._dispatching_task.cancel()
            self._dispatching_task = asyncio.create_task(self._dispatch_timers())

    async def get_timer(self, timer_id: int) -> t.Optional[BaseTimerEvent]:
        """Retrieve a currently pending timer.

        Parameters
        ----------
        timer_id : int
            The ID of the timer object.

        Returns
        -------
        Timer
            The located timer object.
        """

        model = await TimerModel.filter(id=timer_id).first()

        if model is None:
            return

        return self.prepare_timer(model)

    async def cancel_timer(self, timer_id: int) -> t.Optional[TimerModel]:
        """Prematurely cancel a timer before expiry. Returns the cancelled timer.

        Parameters
        ----------
        timer_id : int
            The ID of the timer to be cancelled.

        Returns
        -------
        Timer
            The cancelled timer object.
        """
        model = await TimerModel.filter(id=timer_id).first()

        if model is None:
            return

        await model.delete()

        cls = timers.get(model.event)

        if cls is None:
            return

        return cls(id=model.id,
                   app=self.bot,
                   expires=model.expires,
                   created=model.created,
                   args=model.extra.get("args"),
                   kwargs=model.extra.get("kwargs"))

    async def convert_time(
            self,
            time_string: str,
            *,
            user: t.Optional[hikari.SnowflakeishOr[hikari.PartialUser]] = None,
            conversion_mode: t.Optional[ConversionMode] = ConversionMode.RELATIVE,
            future_time: bool = False,
    ) -> datetime.datetime:
        """Try converting a string of human-readable time to a datetime object.

        Parameters
        ----------
        time_string : str
            The string containing the time.
        user : t.Optional[hikari.SnowflakeishOr[hikari.PartialUser]], optional
            The user whose preferences will be used in the case of timezones, by default None
        conversion_mode : t.Optional[str], optional
            If specified, forces either 'relative' or 'absolute' conversion, by default None
        future_time : bool, optional
            If True and the time specified is in the past, raise an error, by default False

        Returns
        -------
        datetime.datetime
            The converted datetime.datetime object.

        Raises
        ------
        ValueError
            Time could not be parsed using relative conversion.
        ValueError
            Time could not be parsed using absolute conversion.
        ValueError
            Time is not in the future.
        """
        user_id = hikari.Snowflake(user) if user else None
        logger.debug(f"String passed for time conversion: {time_string}")

        if conversion_mode == ConversionMode.RELATIVE:
            matches = self.compiled.fullmatch(time_string)
            data = {k: int(v) for k, v in matches.groupdict(default=0).items()}
            time = 0

            for val, category in data:
                val = val.replace(",", ".")  # Replace commas with periods to correctly register decimal places
                # If this is a single letter

                if len(category) == 1:
                    if category in time_letter_dict.keys():
                        time += time_letter_dict[category] * float(val)

                else:
                    # If a partial match is found with any of the keys
                    # Reason for making the same code here is because
                    # words are case-insensitive, as opposed to single letters

                    for string in time_word_dict.keys():
                        if (
                                lev.distance(category.lower(), string.lower()) <= 1
                        ):  # If str has 1 or less different letters (For plural)
                            time += time_word_dict[string] * float(val)
                            break

            if time > 0:  # If we found time
                return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=time)

            if conversion_mode == ConversionMode.RELATIVE:
                raise ValueError("Failed time conversion.")

        if conversion_mode == ConversionMode.ABSOLUTE:

            timezone = "UTC"
            if user_id:
                model = await UserModel.filter(user_id=user_id).first()
                if model:
                    timezone = model.tz
                    assert timezone is not None  # Fucking pointless, I hate you pyright

            time = dateparser.parse(
                time_string, settings={"RETURN_AS_TIMEZONE_AWARE": True, "TIMEZONE": timezone, "NORMALIZE": True}
            )

            if not time:
                raise ValueError("Time could not be parsed. (absolute)")

            if future_time and time < datetime.datetime.now(datetime.timezone.utc):
                raise ValueError("Time is not in the future!")

            return time

        raise ValueError("Time conversion failed.")
