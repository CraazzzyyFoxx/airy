import asyncio
import typing as t

import hikari
import lavacord
import miru

from .enums import ButtonEmojis


if t.TYPE_CHECKING:
    from .player import PlayerMenu


__all__ = ("PlayOrPauseButton",
           "RepeatButton",
           "PreviousButton",
           "NextButton",
           'SkipToButton',
           "PlayerMenuT",
           "PlayerButton")


PlayerMenuT = t.TypeVar("PlayerMenuT", bound="PlayerMenu")


class PlayerButton(miru.Button[PlayerMenuT]):
    """A baseclass for all player buttons. NavigatorView requires instances of this class as it's items.

    Parameters
    ----------
    style : Union[hikari.ButtonStyle, int], optional
        The style of the navigation button, by default hikari.ButtonStyle.PRIMARY
    label : Optional[str], optional
        The label of the navigation button, by default None
    disabled : bool, optional
        Boolean indicating if the navigation button is disabled, by default False
    custom_id : Optional[str], optional
        The custom identifier of the navigation button, by default None
    emoji : Union[hikari.Emoji, str, None], optional
        The emoji of the navigation button, by default None
    row : Optional[int], optional
        The row this navigation button should occupy. Leave None for auto-placement.
    """

    def __init__(
        self,
        *,
        style: t.Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.SECONDARY,
        label: t.Optional[str] = None,
        disabled: bool = False,
        custom_id: t.Optional[str] = None,
        emoji: t.Union[hikari.Emoji, str, None] = None,
        row: t.Optional[int] = None,
    ):
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            url=None,
            emoji=emoji,
            row=row,
        )

    async def before_update_menu(self) -> None:
        """
        Called when the player is about to transition to the next page. Also called before the first page is sent.
        """
        pass


class PlayOrPauseButton(PlayerButton):
    def __init__(self):
        super().__init__(label="Play",
                         emoji=ButtonEmojis.play,
                         )

    async def callback(self, context: miru.ViewContext) -> None:
        if self.label == "Pause":
            await self.view.player.pause()
        else:
            await self.view.player.resume()
        await asyncio.sleep(0.1)
        await self.view.send_menu_component(context)

    async def before_update_menu(self) -> None:
        if self.view.player.is_paused():
            self.label = "Play"
            self.emoji = ButtonEmojis.play
        else:
            self.label = "Pause"
            self.emoji = ButtonEmojis.pause


class PreviousButton(PlayerButton):
    def __init__(self):
        super().__init__(label="Previous",
                         emoji=ButtonEmojis.previous,
                         )

    async def callback(self, context: miru.ViewContext) -> None:
        player = self.view.player
        player.queue.get_previous_track()
        await player.stop()
        await asyncio.sleep(0.1)
        await self.view.send_menu_component(context)

    async def before_update_menu(self) -> None:
        if self.view.player.queue.current_index == 1:
            self.disabled = True
        else:
            self.disabled = False


class NextButton(PlayerButton):
    def __init__(self):
        super().__init__(label="Next",
                         emoji=ButtonEmojis.next,
                         )

    async def callback(self, context: miru.ViewContext) -> None:
        await self.view.player.stop()
        await asyncio.sleep(0.1)
        await self.view.send_menu_component(context)

    async def before_update_menu(self) -> None:
        if len(self.view.player.queue.upcoming) > 0:
            self.disabled = False
        else:
            self.disabled = True


class RepeatButton(PlayerButton):
    def __init__(self):
        super().__init__(label="OFF",
                         emoji=ButtonEmojis.repeat,
                         )

    async def callback(self, context: miru.ViewContext) -> None:
        repeat_mode = self.label
        if repeat_mode == "OFF":
            self.view.player.queue.set_repeat_mode(lavacord.RepeatMode.ONE)
        elif repeat_mode == "ONE":
            self.view.player.queue.set_repeat_mode(lavacord.RepeatMode.ALL)
        else:
            self.view.player.queue.set_repeat_mode(lavacord.RepeatMode.OFF)

        await self.view.send_menu_component(context)

    async def before_update_menu(self) -> None:
        repeat_mode = self.view.player.queue.repeat_mode
        if repeat_mode == lavacord.RepeatMode.OFF:
            self.label = "OFF"
            self.style = hikari.ButtonStyle.SECONDARY
        elif repeat_mode == lavacord.RepeatMode.ONE:
            self.label = "ONE"
            self.style = hikari.ButtonStyle.SECONDARY
        else:
            self.label = "ALL"
            self.style = hikari.ButtonStyle.PRIMARY


class SkipToButton(PlayerButton):
    def __init__(self):
        super().__init__(label="Skip to",
                         emoji=ButtonEmojis.skipto,
                         )

    async def before_update_menu(self) -> None:
        if not self.view.player.queue:
            self.disabled = True
        else:
            self.disabled = False

    async def callback(self, context: miru.ViewContext) -> None:
        modal = miru.Modal("Skip to index", autodefer=False)
        modal.add_item(miru.TextInput(label="Track number", placeholder="Enter a track button to skip to it..."))
        await context.respond_with_modal(modal)
        await modal.wait()

        if not modal.values:
            return

        try:
            index = int(list(modal.values.values())[0]) - 1
        except (ValueError, TypeError):
            self.view._inter = modal.get_response_context().interaction
            return await modal.get_response_context().defer()

        self.view.player.queue.skip_to_index(index)
        await self.view.player.stop()
        await asyncio.sleep(0.1)
        await self.view.send_menu_component(modal.get_response_context())
