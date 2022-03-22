from typing import TYPE_CHECKING
from typing import Optional
from typing import TypeVar
from typing import Union

import hikari
from miru import Select

from miru.button import Button
from miru.context import ViewContext
from miru.modal import Modal
from miru.text_input import TextInput

from .enums import select_options, EmbedSettings

if TYPE_CHECKING:
    from . import EmbedConstructorT


class ConstructorButton(Button[EmbedConstructorT]):
    """A baseclass for all navigation buttons. NavigatorView requires instances of this class as it's items.

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
        style: Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.PRIMARY,
        label: Optional[str] = None,
        disabled: bool = False,
        custom_id: Optional[str] = None,
        emoji: Union[hikari.Emoji, str, None] = None,
        row: Optional[int] = None,
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

    async def before_page_change(self) -> None:
        """
        Called when the navigator is about to transition to the next page. Also called before the first page is sent.
        """
        pass


class MainSelect(Select[EmbedConstructorT]):
    def __init__(self, view: EmbedConstructorT):
        options = [value for name, value in select_options.items()
                   if view.is_action_enabled_for(name)]
        super().__init__(options=options, row=2)
        self._view = view

    async def callback(self, context: ViewContext) -> None:
        value = self.values[0]

        if value == "__title":
            modal = Modal("Title", autodefer=False)
            modal.add_item(TextInput(label="Title",
                                     placeholder="Enter a title",
                                     required=True,
                                     min_length=1,
                                     max_length=256))

        if value == "__description":
            modal = Modal("Description", autodefer=False)
            modal.add_item(TextInput(label="Description",
                                     style=hikari.TextInputStyle.PARAGRAPH,
                                     placeholder="Enter a Description",
                                     required=True,
                                     min_length=1,
                                     max_length=256))

        if value == "__color":
            modal = Modal("Color", autodefer=False)
            modal.add_item(TextInput(label="Color",
                                     placeholder="Enter a Color",
                                     required=True,
                                     min_length=1,
                                     max_length=256))

        if value == "__timestamp":
            modal = Modal("Title", autodefer=False)
            modal.add_item(TextInput(label="Title",
                                     placeholder="Enter a title",
                                     required=True,
                                     min_length=1,
                                     max_length=256))


        await modal.wait()

        if not modal.values:
            return


class AddFieldButton(ConstructorButton[EmbedConstructorT]):
    def __init__(self):
        super().__init__()


class IndicatorButton(ConstructorButton[EmbedConstructorT]):
    """
    A built-in NavButton to show the current page's number.
    """

    def __init__(
        self,
        *,
        style: Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.SECONDARY,
        custom_id: Optional[str] = None,
        emoji: Union[hikari.Emoji, str, None] = None,
        disabled: bool = False,
        row: Optional[int] = None,
    ):
        # Either label or emoji is required, so we pass a placeholder
        super().__init__(style=style, label="0/0", custom_id=custom_id, emoji=emoji, disabled=disabled, row=row)

    async def before_page_change(self) -> None:
        self.label = f"{self.view.current_page+1}/{self.view.source.get_max_pages()}"

    async def callback(self, context: ViewContext) -> None:
        modal = Modal("Jump to page", autodefer=False)
        modal.add_item(TextInput(label="Page Number", placeholder="Enter a page number to jump to it..."))
        await context.respond_with_modal(modal)
        await modal.wait()

        if not modal.values:
            return

        try:
            page_number = int(list(modal.values.values())[0]) - 1
        except (ValueError, TypeError):
            self.view._inter = modal.get_response_context().interaction
            return await modal.get_response_context().defer()

        self.view.current_page = page_number
        await self.view.send_page(modal.get_response_context())


class StopButton(ConstructorButton[EmbedConstructorT]):
    """
    A built-in NavButton to stop the navigator and disable all buttons.
    """

    def __init__(
        self,
        *,
        style: Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.DANGER,
        label: Optional[str] = 'Quit',
        custom_id: Optional[str] = None,
        emoji: Union[hikari.Emoji, str, None] = None,
        row: Optional[int] = None,
    ):
        super().__init__(style=style, label=label, custom_id=custom_id, emoji=emoji, row=row)

    async def callback(self, context: ViewContext) -> None:
        if not self.view.message and not self.view._inter:
            return

        for button in self.view.children:
            assert isinstance(button, ConstructorButton)
            button.disabled = True

        if self.view._inter and self.view.ephemeral:
            await self.view._inter.edit_initial_response(components=self.view.build())
        elif self.view.message:
            await self.view.message.edit(components=self.view.build())
        self.view.stop()
