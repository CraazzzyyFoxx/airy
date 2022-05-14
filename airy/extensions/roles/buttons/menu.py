from __future__ import annotations

import typing as t

import hikari
import miru

from airy.core import AirySlashContext, MenuViewAuthorOnly, ActionMenusModel, ActionMenusButtonModel, ActionType, Airy
from airy.static import ColorEnum, MenuEmojiEnum
from airy.utils import utcnow, helpers, RespondEmbed
from .enums import button_styles


class AddModal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter action menus button")
        self.role: t.Optional[hikari.Role] = None
        self.label: t.Optional[str] = None
        self.style: t.Optional[hikari.ButtonStyle] = None
        self.emoji: t.Optional[hikari.Emoji] = None
        self.role_input = miru.TextInput(label="Role (name or id)",
                                         placeholder="For example: Airy or 947964654230052876",
                                         min_length=1)
        self.label_input = miru.TextInput(label="The label of the button. ",
                                          placeholder="The label that should appear on the button.",
                                          min_length=1,
                                          max_length=80)
        self.style_input = miru.TextInput(label="Button style",
                                          placeholder="The style of the button. "
                                                      "It's can be Blurple, Grey, Red, Green",
                                          style=hikari.TextInputStyle.PARAGRAPH,
                                          min_length=1,
                                          max_length=7)
        self.emoji_input = miru.TextInput(label="Emoji",
                                          placeholder="The emoji of the button. "
                                                      "It's can be :star: or <:spotify:908292227657240578>",
                                          style=hikari.TextInputStyle.PARAGRAPH)

        self.add_item(self.role_input)
        self.add_item(self.label_input)
        self.add_item(self.style_input)
        self.add_item(self.emoji_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.role = await helpers.parse_role(ctx, ctx.values.get(self.role_input))
        self.label = ctx.values.get(self.label_input)
        self.style = button_styles.get(ctx.values.get(self.style_input).capitalize()) or hikari.ButtonStyle.SECONDARY
        emoji = ctx.values.get(self.emoji_input)
        if emoji:
            try:
                self.emoji = hikari.Emoji.parse(emoji)
            except ValueError:
                self.emoji = None


class RemoveModal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.role: t.Optional[hikari.Role] = None
        self.role_input = miru.TextInput(label="Role (name or id)",
                                         placeholder="For example: Airy or 947964654230052876")
        self.add_item(self.role_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.role = await helpers.parse_role(ctx, ctx.values.get(self.role_input))


class MenuView(MenuViewAuthorOnly):
    def __init__(self, ctx: AirySlashContext, channel_id: hikari.Snowflake, message_id: hikari.Snowflake):
        self.ctx = ctx
        self.model: t.Optional[ActionMenusModel] = None

        self.channel_id = channel_id
        self.message_id = message_id

        self.acm_message: t.Optional[hikari.Message] = None
        self.acm_embed: t.Optional[hikari.Embed] = None
        self.acm_view: t.Optional[miru.View] = None

        super().__init__(ctx)
        for item in self.default_buttons:
            self.add_item(item)

    @property
    def bot(self) -> Airy:
        return self.ctx.bot

    @property
    def default_buttons(self):
        return [AddButtonButton(), RemoveButtonButton(), DestroyButton(), PreviewButton(), QuitButton(), SelectEmbed()]

    def get_kwargs(self):
        embed = hikari.Embed(title="Button Roles",
                             color=ColorEnum.teal,
                             timestamp=utcnow())
        entries_description = []

        for index, button in enumerate(self.model.buttons, 1):
            entries_description.append(f"**{index}.** {button.display()}")

        embed.description = '\n'.join(entries_description)
        return dict(embed=embed, components=self.build(), flags=self.flags)

    async def send(self, ctx: t.Union[miru.ViewContext, miru.ModalContext]):
        kwargs = self.get_kwargs()
        await ctx.edit_response(**kwargs)

    async def initial_send(self) -> None:
        try:
            self.acm_message = await self.ctx.bot.rest.fetch_message(self.channel_id, self.message_id)
            self.acm_embed = self.acm_message.embeds[0]
            self.acm_view = miru.View.from_message(self.acm_message, timeout=None)
        except hikari.NotFoundError:
            await self.ctx.respond(embed=RespondEmbed.error("Provided action menus missing"))
            return

        self.model = (await ActionMenusModel
                      .filter(guild_id=self.ctx.guild_id, message_id=self.message_id, channel_id=self.channel_id)
                      .first()
                      .prefetch_related("buttons"))

        if not self.model:
            await self.ctx.respond(embed=RespondEmbed.error("Provided action menus missing"))
            return
        kwargs = self.get_kwargs()
        await self.ctx.interaction.create_initial_response(hikari.ResponseType.MESSAGE_CREATE, **kwargs)
        message = await self.ctx.interaction.fetch_initial_response()
        super(MenuView, self).start(message)

    async def save(self):
        try:
            if len(self.model.buttons.related_objects) == 0:
                await self.ctx.bot.rest.delete_message(self.channel_id, self.message_id)
                await self.model.delete()
                await self.last_ctx.edit_response(embed=RespondEmbed.success("Button role was deleted"))
                self.stop()
            else:
                await self.ctx.bot.rest.edit_message(self.channel_id,
                                                     self.message_id,
                                                     embed=self.acm_embed,
                                                     components=self.acm_view.build())
                for item in self.children:
                    item.disabled = True
                kwargs = self.get_kwargs()
                await self.last_ctx.edit_response(**kwargs)
                self.stop()
        except hikari.NotFoundError:
            pass
        except hikari.ForbiddenError:
            embed = RespondEmbed.error(
                title="Insufficient permissions",
                description=f"The bot cannot edit message due to insufficient permissions.")
            await self.last_ctx.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)


ViewT = t.TypeVar("ViewT", bound=MenuView)


class AddButtonButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, emoji=MenuEmojiEnum.ADD)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = AddModal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = modal.role

        if len(self.view.acm_view.children) == 25:
            embed = RespondEmbed.error(
                title="Too many buttons",
                description="This message has too many buttons attached to it already, please choose a different message!"
            )
            await context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        if role and str(role.id) not in [entry.payload for entry in self.view.model.buttons]:
            channel_id = self.view.channel_id

            entry_model = ActionMenusButtonModel(menus_id=self.view.model.id,
                                                 payload=str(role.id),
                                                 label=modal.label,
                                                 style=modal.style,
                                                 action_type=ActionType.ROLE,
                                                 emoji=modal.emoji
                                                 )
            button = miru.Button(
                custom_id=f"ACM:{channel_id}:{role.id}",
                emoji=modal.emoji,
                label=modal.label,
                style=modal.style,
            )
            self.view.acm_view.add_item(button)
            await entry_model.save()
            self.view.model.buttons.related_objects.append(entry_model)

        await self.view.send(modal.get_response_context())


class RemoveButtonButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, emoji=MenuEmojiEnum.REMOVE)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = RemoveModal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = modal.role
        channel_id = self.view.channel_id

        if role and str(role.id) in [entry.payload for entry in self.view.model.buttons]:
            await ActionMenusButtonModel.filter(menus_id=self.view.model.id, payload=str(role.id)).delete()

            for entry in self.view.model.buttons.related_objects:
                if entry.payload == str(role.id):
                    for item in self.view.acm_view.children:
                        if item.custom_id == f"ACM:{channel_id}:{entry.payload}":
                            self.view.acm_view.remove_item(item)
                    self.view.model.buttons.related_objects.remove(entry)

        await self.view.send(modal.get_response_context())


class DestroyButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Destroy", style=hikari.ButtonStyle.DANGER, emoji=MenuEmojiEnum.TRASHCAN)

    async def callback(self, context: miru.ViewContext) -> None:
        try:
            await self.view.ctx.bot.rest.delete_message(self.view.channel_id, self.view.message_id)
        except hikari.NotFoundError:
            pass

        await self.view.model.delete()
        await context.edit_response(embed=RespondEmbed.success("Button roles were deleted"),
                                    components=[],
                                    flags=self.view.flags)
        self.view.stop()


class PreviewButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(label="Preview", style=hikari.ButtonStyle.SECONDARY)

    async def callback(self, context: miru.ViewContext) -> None:
        await context.respond(embed=self.view.acm_embed, flags=hikari.MessageFlag.EPHEMERAL)


class QuitButton(miru.Button[ViewT]):
    def __init__(self) -> None:
        super().__init__(style=hikari.ButtonStyle.PRIMARY, label="Save", emoji=MenuEmojiEnum.SAVE)

    async def callback(self, context: miru.ViewContext) -> None:
        try:
            await self.view.acm_message.edit(embed=self.view.acm_embed, components=self.view.acm_view.build())
        except hikari.NotFoundError:
            pass
        except hikari.ForbiddenError:
            embed = RespondEmbed.error(
                title="Insufficient permissions",
                description=f"The bot cannot edit message due to insufficient permissions.")
            await context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            return

        for item in self.view.children:
            item.disabled = True
        kwargs = self.view.get_kwargs()
        await context.edit_response(**kwargs)
        self.view.stop()


class TitleModal(miru.Modal):
    def __init__(self) -> None:
        self.title_input = miru.TextInput(label="Title",
                                          placeholder="The title of the embed.", max_length=100,
                                          style=hikari.TextInputStyle.PARAGRAPH)
        super().__init__("Title")
        self.title_: t.Optional[str] = None
        self.add_item(self.title_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        title = ctx.values.get(self.title_input)
        self.title_ = title if title else None


class DescriptionModal(miru.Modal):
    def __init__(self, ctx: miru.ViewContext, model: ActionMenusModel) -> None:
        emojis = []
        roles = []
        for button in model.buttons:
            if button.emoji:
                emojis.append(f"{button.emoji}")
            role: hikari.Role = ctx.bot.cache.get_role(button.payload)
            roles.append(f"@{role.name} <@&{button.payload}>")

        self.description_input = miru.TextInput(label="Description",
                                                placeholder="The description of the embed.", max_length=4000,
                                                style=hikari.TextInputStyle.PARAGRAPH
                                                )
        self.description_roles = miru.TextInput(label="Roles",
                                                value="\n".join(roles), max_length=4000,
                                                style=hikari.TextInputStyle.PARAGRAPH
                                                )
        self.description_emojis = miru.TextInput(label="Emojis",
                                                 value="\n".join(emojis), max_length=4000,
                                                 style=hikari.TextInputStyle.PARAGRAPH
                                                 )
        super().__init__("Description")
        self.description: t.Optional[str] = None
        self.add_item(self.description_input)
        self.add_item(self.description_emojis)
        self.add_item(self.description_roles)

    async def callback(self, ctx: miru.ModalContext) -> None:
        description = ctx.values.get(self.description_input)
        self.description = description if description else None


class ColorModal(miru.Modal):
    def __init__(self, ) -> None:
        self.color_input = miru.TextInput(label="Color",
                                          placeholder="The color of the embed.", min_length=1)

        super().__init__("Color")
        self.color: t.Optional[hikari.Color] = None
        self.add_item(self.color_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.color = helpers.parse_color(ctx.values.get(self.color_input))


class AuthorModal(miru.Modal):
    def __init__(self, ) -> None:
        self.author_input = miru.TextInput(label="Author",
                                           placeholder="The author of the embed. Appears above the title.",
                                           style=hikari.TextInputStyle.PARAGRAPH,
                                           max_length=100)

        self.author_url_input = miru.TextInput(label="Author URL",
                                               placeholder="An URL pointing to an image to use for the author's avatar.",
                                               max_length=100)

        super().__init__("Author")
        self.author_url: t.Optional[str] = None
        self.author: t.Optional[str] = None
        self.add_item(self.author_input)
        self.add_item(self.author_url_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.author_url_input)):
            self.author_url = ctx.values.get(self.author_url_input)
        author = ctx.values.get(self.author_input)
        self.author = author if author else None


class FooterModal(miru.Modal):
    def __init__(self, ) -> None:
        self.footer_input = miru.TextInput(label="Footer",
                                           placeholder="The footer of the embed.",
                                           max_length=200,
                                           style=hikari.TextInputStyle.PARAGRAPH)
        self.footer_url_input = miru.TextInput(label="Footer URL",
                                               placeholder="An url pointing to an image to use for the embed footer.",
                                               max_length=200)

        super().__init__("Footer")
        self.footer: t.Optional[str] = None
        self.footer_url: t.Optional[str] = None
        self.add_item(self.footer_input)
        self.add_item(self.footer_url_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.footer_url_input)):
            self.footer_url = ctx.values.get(self.footer_url_input)
        author = ctx.values.get(self.footer_input)
        self.footer = author if author else None


class ThumbnailModal(miru.Modal):
    def __init__(self, ) -> None:
        self.thumbnail_input = miru.TextInput(label="Thumbnail URL",
                                              placeholder="An url pointing to an image to use for the thumbnail.",
                                              max_length=200)

        super().__init__("Thumbnail")
        self.thumbnail: t.Optional[str] = None
        self.add_item(self.thumbnail_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.thumbnail_input)):
            self.thumbnail = ctx.values.get(self.thumbnail_input)
        else:
            self.thumbnail = None


class SelectEmbed(miru.Select[ViewT]):
    def __init__(self):
        self.options = [
            miru.SelectOption(label="Title", value="__title", description="The title of the embed."),
            miru.SelectOption(label="Description", value="__description", description="The title of the embed."),
            miru.SelectOption(label="Color", value="__color", description="The color of the embed."),
            miru.SelectOption(label="Author", value="__author",
                              description="The author of the embed. Appears above the title."),
            miru.SelectOption(label="Footer", value="__footer", description="The footer of the embed."),
            # miru.SelectOption(label="Thumbnail", value="__thumbnail",
            #                   description="An url pointing to an image to use for the thumbnail.")
        ]
        super().__init__(options=self.options,
                         placeholder="Embed Settings",
                         row=2)

    async def callback(self, context: miru.ViewContext) -> None:
        value = self.values[0]
        if value == "__title":
            modal = TitleModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.title = modal.title_
        elif value == "__description":
            modal = DescriptionModal(context, self.view.model)
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.description = modal.description
        elif value == "__color":
            modal = ColorModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.color = modal.color
        elif value == "__author":
            modal = AuthorModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.set_author(name=modal.author, icon=modal.author_url)
        elif value == "__footer":
            modal = FooterModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.set_footer(modal.footer, icon=modal.footer_url)
        # elif value == "__thumbnail":
        #     modal = ThumbnailModal()
        #     await context.respond_with_modal(modal)
        #     await modal.wait()
        #     self.view.acm_embed.set_thumbnail(modal.thumbnail)

        await self.view.send(modal.get_response_context())
