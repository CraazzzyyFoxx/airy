from ..enums import Enum

from datetime import datetime, timedelta
from discord.ext.commands import BadArgument
from pytz import timezone, utc
from core.errors import TimeInPast, TimeInFuture

from .human_timedelta import format_date

_MSK_timezone = timezone('Europe/Moscow')
_UTC_timezone = utc


class Accuracy(str, Enum):
    microseconds = '%H:%M:%S.%f'
    seconds = '%H:%M:%S'
    minutes = '%H:%M'


class Formats(list[str], Enum):
    year = ['%d.%m %H:%M:%S', '%d.%m %H:%M'],  # 21.12 23:59:59,  21.12 23:59
    full = ['%d.%m.%y %H:%M:%S', '%d.%m.%y %H:%M'  # 21.12.21 23:59:59,  21.12.21 23:59
                                 '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M']  # 21.12.2021 23:59:59,  21.12.2021 23:59
    date = ['%H:%M:%S', '%H:%M']  # 23:59:59,  23:59
    month = ['%d %H:%M:%S', '%d %H:%M']  # 21 23:59:59,  21 23:59


class UserFriendlyDatetime:
    __separator = ' - '

    def __init__(self, datetime_: datetime, accuracy: int = 2):
        self.datetime = datetime_
        self.accuracy = accuracy

    def __str__(self):
        _datetime = _MSK_timezone.fromutc(self.datetime)
        _datetime = _datetime.strftime(f'%d.%m.%Y{self.__separator}' + self.__data[self.accuracy])
        return _datetime if self.accuracy > 0 else _datetime[:-3]

    @classmethod
    async def convert(cls, ctx, date: str, *, seconds: int = None, past: bool = False):
        now = datetime.utcnow().replace(microsecond=0)

        for key, formats in Formats._name_to_member_map_.items():
            for format_ in formats:
                try:
                    datetime_ = datetime.strptime(date, format_)
                except ValueError:
                    pass
                else:
                    if key == 'year':
                        datetime_ = datetime_.replace(year=now.year)
                    if key == 'date':
                        datetime_ = datetime_.replace(year=now.year, month=now.month, day=now.day)
                    if key == 'month':
                        datetime_ = datetime_.replace(year=now.year, month=now.month)

                    if not past and now > datetime_:
                        raise TimeInPast('Не живите в прошлом')

                    if seconds is not None:
                        if datetime_ > now + timedelta(seconds=seconds):
                            raise TimeInFuture('Не заглядывайте слишком далеко в будущее')

                    return cls(datetime_ - _MSK_timezone.utcoffset(datetime_))

        raise BadArgument('Неправильный формат даты')

    @property
    def dt(self):
        return self.datetime

    @classmethod
    def now(cls, accuracy: int = 1):
        return cls(datetime.utcnow().replace(microsecond=0), accuracy=accuracy)

    @classmethod
    def timestamp(cls, seconds: int):
        return cls(datetime.fromtimestamp(seconds))
