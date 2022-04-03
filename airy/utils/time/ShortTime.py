import re

from datetime import datetime, timezone

import lightbulb
from dateutil.relativedelta import relativedelta


class ShortTime(lightbulb.converters.BaseConverter[datetime]):
    compiled = re.compile(r"""(?:(?P<years>[0-9])(?:years?|y))?               # e.g. 2y
                             (?:(?P<months>[0-9]{1,2})(?:months?|mo))?     # e.g. 2mo
                             (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?        # e.g. 10w
                             (?:(?P<days>[0-9]{1,5})(?:days?|d))?          # e.g. 14d
                             (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?        # e.g. 12h
                             (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?    # e.g. 10m
                             (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?    # e.g. 15s
                          """, re.VERBOSE)

    def __init__(self, context=None, argument=None, *, now=None):
        super().__init__(context)

        match = self.compiled.fullmatch(argument)
        if match is None or not match.group(0):
            raise TypeError('invalid time provided')

        data = {k: int(v) for k, v in match.groupdict(default=0).items()}
        now = now or datetime.now(timezone.utc)
        self.dt = now + relativedelta(**data)

    @classmethod
    async def convert(cls, argument):
        return cls(argument, now=datetime.utcnow())
