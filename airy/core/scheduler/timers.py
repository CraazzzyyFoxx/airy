from __future__ import annotations

import abc
import datetime
import typing as t

import attr
import hikari

from airy.utils import time, utcnow

if t.TYPE_CHECKING:
    from airy.core import Airy


__all__ = ("BaseTimerEvent",
           "ReminderEvent",
           "timers",
           "MuteEvent",
           )


@attr.define(kw_only=True)
class BaseTimerEvent(hikari.Event):
    app: Airy = attr.field(default=None)

    id = attr.field(eq=True, default=None)
    args: list[t.Any] = attr.field()
    kwargs: dict = attr.field()
    created: datetime.datetime = attr.field(eq=False)
    expires: datetime.datetime = attr.field(eq=False)

    @property
    def human_delta(self):
        return time.format_relative(self.created)

    @property
    def delta(self) -> t.Union[float, int]:
        return (self.expires - utcnow()).total_seconds()

    @property
    @abc.abstractmethod
    def event(self) -> str:
        """Event name

        Returns
        -------
        str
        """


@attr.define()
class ReminderEvent(BaseTimerEvent):
    @property
    def author_id(self):
        if self.args:
            return int(self.args[0])
        return None

    @property
    def event(self):
        return 'reminder'


@attr.define()
class MuteEvent(BaseTimerEvent):
    @property
    def author_id(self):
        if self.args:
            return int(self.args[0])
        return None

    @property
    def muted_user_id(self):
        if self.args:
            return int(self.args[1])
        return None

    @property
    def guild_id(self):
        if self.args:
            return int(self.args[2])
        return None

    @property
    def role_id(self):
        if self.args:
            return int(self.args[3])
        return None

    @property
    def event(self):
        return 'mute'


timers = {'reminder': ReminderEvent,
          'mute': MuteEvent,
          }
