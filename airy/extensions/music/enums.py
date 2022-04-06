from __future__ import annotations

from hikari.internal.enums import Enum

__all__ = (
    "ButtonEmojis",
)


class ButtonEmojis(str, Enum):
    play = "<:play:910871207841251328>"
    pause = "<:pause:910871198433415208>"
    next = "<:next:910871169811492865>"
    previous = "<:previous:910871233422295080>"
    repeat = "<:repeat:910871225583149066>"
    audio = "<:audio:910871158814048316>"
    skipto = "<:skipto:911150565969518592>"
