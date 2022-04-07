from datetime import datetime, timezone

import lightbulb
import parsedatetime as pdt
from dateutil.relativedelta import relativedelta

from airy.utils.formats import format_dt
from airy.utils.formats import human_join, Plural
from .ShortTime import ShortTime
from .now import utcnow

units = pdt.pdtLocales['en_US'].units
units['minutes'].append('mins')
units['seconds'].append('secs')


class HumanTime:
    calendar = pdt.Calendar(version=pdt.VERSION_CONTEXT_STYLE)

    def __init__(self, argument, *, now=None):
        now = now or datetime.utcnow()
        dt, status = self.calendar.parseDT(argument, sourceTime=now)
        if not status.hasDateOrTime:
            raise TypeError('invalid time provided, try e.g. "tomorrow" or "3 days"')

        if not status.hasTime:
            # replace it with the current time
            dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

        self.dt = dt
        self._past = dt < now

    @classmethod
    async def convert(cls, ctx, argument):
        return cls(argument, now=ctx.message.created_at)


class Time(HumanTime):
    def __init__(self, argument, *, now=None):
        try:
            o = ShortTime(argument=argument)
        except Exception as e:
            super().__init__(argument, now=now)
        else:
            self.dt = o.dt
            self._past = False


class FutureTime(Time):
    def __init__(self, argument, *, now=None):
        super().__init__(argument, now=now)

        if self._past:
            raise TypeError('this time is in the past')


class UserFriendlyTime(lightbulb.converters.BaseConverter[datetime]):
    """That way quotes aren't absolutely necessary."""

    def __init__(self, context) -> None:
        super().__init__(context)

    async def convert(self, arg) -> datetime:
        # Create a copy of ourselves to prevent race conditions from two
        # events modifying the same instance of a converter
        try:
            calendar = HumanTime.calendar
            regex = ShortTime.compiled
            now = utcnow()

            match = regex.match(arg)
            if match is not None and match.group(0):
                data = {k: int(v) for k, v in match.groupdict(default=0).items()}
                dt = now + relativedelta(**data)
                return dt

            # apparently nlp does not like "from now"
            # it likes "from x" in other cases though so let me handle the 'now' case
            if arg.endswith('from now'):
                arg = arg[:-8].strip()

            if arg[0:2] == 'me':
                # starts with "me to", "me in", or "me at "
                if arg[0:6] in ('me to ', 'me in ', 'me at '):
                    arg = arg[6:]

            elements = calendar.nlp(arg, sourceTime=now)
            if elements is None or len(elements) == 0:
                raise ValueError('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            # handle the following cases:
            # "date time" foo
            # date time foo
            # foo date time

            # first the first two cases:
            dt, status, begin, end, dt_string = elements[0]

            if not status.hasDateOrTime:
                raise ValueError('Invalid time provided, try e.g. "tomorrow" or "3 days".')

            if begin not in (0, 1) and end != len(arg):
                raise ValueError('Time is either in an inappropriate location, which '
                                 'must be either at the end or beginning of your input, '
                                 'or I just flat out did not understand what you meant. Sorry.')

            if not status.hasTime:
                # replace it with the current time
                dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond)

            # if midnight is provided, just default to next day
            if status.accuracy == pdt.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=now.day + 1)

            dt = dt.replace(tzinfo=timezone.utc)

            return dt
        except:
            import traceback
            traceback.print_exc()
            raise


def human_timedelta(dt, *, source=None, accuracy=3, brief=False, suffix=True):
    now = source or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Microsecond free zone
    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    # This implementation uses relative-delta instead of the much more obvious
    # div-mod approach with seconds because the seconds approach is not entirely
    # accurate once you go over 1 week in terms of accuracy since you have to
    # hardcode a month as 30 or 31 days.
    # A query like "11 months" can be interpreted as "!1 months and 6 days"
    if dt > now:
        delta = relativedelta(dt, now)
        suffix = ''
    else:
        delta = relativedelta(now, dt)
        suffix = ' ago' if suffix else ''

    attrs = [
        ('year', 'y'),
        ('month', 'mo'),
        ('day', 'd'),
        ('hour', 'h'),
        ('minute', 'm'),
        ('second', 's'),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + 's')
        if not elem:
            continue

        if attr == 'day':
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                if not brief:
                    output.append(format(Plural(weeks), 'week'))
                else:
                    output.append(f'{weeks}w')

        if elem <= 0:
            continue

        if brief:
            output.append(f'{elem}{brief_attr}')
        else:
            output.append(format(Plural(elem), attr))

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return 'now'
    else:
        if not brief:
            return human_join(output, final='and') + suffix
        else:
            return ' '.join(output) + suffix


def format_relative(dt):
    return format_dt(dt, 'R')


def format_date(dt):
    return format_dt(dt, 'f')
