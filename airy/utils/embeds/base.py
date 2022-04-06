import typing

import hikari

from airy.etc import RespondIconsEnum, ColorEnum
from airy.utils.time import utcnow


class BaseEmbed(hikari.Embed):
    def __init__(self,
                 *,
                 title: typing.Any = None,
                 description: typing.Any = None,
                 url: typing.Optional[str] = None,
                 color: typing.Optional[hikari.colors.Colorish] = None,
                 ):
        super().__init__(title=title, description=description, url=url, color=color)
        self.timestamp = utcnow()


class RespondEmbed(BaseEmbed):
    def __init__(self,
                 *,
                 description: typing.Any = None,
                 url: typing.Optional[str] = None,
                 color: typing.Optional[hikari.colors.Colorish] = None,
                 ):
        super().__init__(description=description, url=url, color=color)
        self.timestamp = utcnow()

    @classmethod
    def error(cls, title: typing.Any = None, description: typing.Any = None):
        emb = cls(description=description,
                  color=ColorEnum.ERROR)
        emb.set_author(icon=RespondIconsEnum.ERROR.value, name=title)
        return emb

    @classmethod
    def success(cls, title: typing.Any = None, description: typing.Any = None):
        emb = cls(description=description,
                  color=ColorEnum.EMBED_GREEN)
        emb.set_author(icon=RespondIconsEnum.SUCCESS.value, name=title)
        return emb

    @classmethod
    def cooldown(cls, title: typing.Any = None, description: typing.Any = None):
        emb = cls(description=description,
                  color=ColorEnum.EMBED_BLUE)
        emb.set_author(icon=RespondIconsEnum.COOLDOWN, name=title)
        return emb
