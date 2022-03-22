import typing as t

import hikari
import miru


class ButtonMenus(miru.Button):
    def __init__(
            self,
            *,
            style: t.Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.PRIMARY,
            label: t.Optional[str] = None,
            disabled: bool = False,
            custom_id: t.Optional[str] = None,
            url: t.Optional[str] = None,
            emoji: t.Union[hikari.Emoji, str, None] = None,
            row: t.Optional[int] = None,
    ) -> None:
        super().__init__()


class Menus:
    def __init__(self):
        pass

