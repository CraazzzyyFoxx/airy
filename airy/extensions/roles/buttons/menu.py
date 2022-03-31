from __future__ import annotations

import typing as t

import hikari
import miru

from airy.core import AirySlashContext, MenuViewAuthorOnly, ActionMenusModel, ActionMenusButtonModel, ActionType, Airy
from airy.utils import ColorEnum, utcnow, helpers, RespondEmbed, MenuEmojiEnum

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
                                          style=hikari.TextInputStyle.PARAGRAPH)
        self.emoji_input = miru.TextInput(label="Emoji",
                                          placeholder="The emoji of the button. "
                                                      "It's can be :star: or <:spotify:908292227657240578>",
                                          style=hikari.TextInputStyle.PARAGRAPH)

        self.add_item(self.role_input)
        self.add_item(self.label_input)
        self.add_item(self.style_input)
        self.add_item(self.emoji_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.role = await helpers.is_role(ctx, ctx.values.get(self.role_input))
        self.label = ctx.values.get(self.label_input) or '\u200b'
        self.style = button_styles.get(ctx.values.get(self.style_input).capitalize()) or hikari.ButtonStyle.SECONDARY
        emoji = ctx.values.get(self.emoji_input)
        self.emoji = hikari.Emoji.parse(emoji) if emoji else hikari.UNDEFINED


class RemoveModal(miru.Modal):
    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.role: t.Optional[hikari.Role] = None
        self.role_input = miru.TextInput(label="Role (name or id)",
                                         placeholder="For example: Airy or 947964654230052876")
        self.add_item(self.role_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.role = await helpers.is_role(ctx, ctx.values.get(self.role_input))


class MenuView(MenuViewAuthorOnly):
    def __init__(self, ctx: AirySlashContext, channel_id: hikari.Snowflake, message_id: hikari.Snowflake):
        self.channel_id = channel_id
        self.message_id = message_id
        self.acm_message: t.Optional[hikari.Message] = None
        self.acm_embed: t.Optional[hikari.Embed] = None

        self.ctx = ctx
        super().__init__(ctx)
        self.model: t.Optional[ActionMenusModel] = None
        for item in self.default_buttons:
            self.add_item(item)

    @property
    def bot(self) -> Airy:
        return self.ctx.bot

    @property
    def default_buttons(self):
        return [AddButtonButton(), RemoveButtonButton(), DestroyButton(), PreviewButton(), QuitButton()]

    def get_kwargs(self):
        embed = hikari.Embed(title="Action Menus",
                             color=ColorEnum.teal,
                             timestamp=utcnow())
        entries_description = []

        for index, entry in enumerate(self.model.buttons, 1):
            entry_role = self.ctx.bot.cache.get_role(hikari.Snowflake(entry.payload))
            entries_description.append(f"**{index}.** {entry.label} - {entry_role.mention} "
                                       f"(Button ID: {entry.id}, Role ID: {entry_role.id})")

        embed.description = '\n'.join(entries_description)
        return dict(embed=embed, components=self.build(), flags=self.flags)

    async def send(self, ctx: t.Union[miru.ViewContext, miru.ModalContext]):
        kwargs = self.get_kwargs()
        await ctx.edit_response(**kwargs)

    async def initial_send(self) -> None:
        try:
            self.acm_message = await self.ctx.bot.rest.fetch_message(self.channel_id, self.message_id)
            self.acm_embed = self.acm_message.embeds[0]
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


ViewT = t.TypeVar("ViewT", bound=MenuView)


class AddButtonButton(miru.Button[ViewT]):
    def __init__(self):
        super().__init__(style=hikari.ButtonStyle.SECONDARY, emoji=MenuEmojiEnum.ADD)

    async def callback(self, context: miru.ViewContext) -> None:
        modal = AddModal()
        await context.respond_with_modal(modal)
        await modal.wait()
        role = modal.role

        if role and str(role.id) not in [entry.payload for entry in self.view.model.buttons]:
            channel_id = self.view.channel_id
            message_id = self.view.message_id

            entry_model = ActionMenusButtonModel(id_id=self.view.model.id,
                                                 payload=str(role.id),
                                                 style=modal.style,
                                                 action_type=ActionType.ROLE,
                                                 emoji=modal.emoji.__str__()
                                                 )
            button = miru.Button(
                custom_id=f"ACM:{channel_id}:{role.id}",
                emoji=modal.emoji,
                label=modal.label,
                style=modal.style,
            )

            message = await self.view.bot.rest.fetch_message(channel_id, message_id)
            view = miru.View.from_message(message, timeout=None)
            view.add_item(button)
            try:
                await message.edit(components=view.build())
            except hikari.NotFoundError:
                pass
            except hikari.ForbiddenError:
                embed = RespondEmbed.error(
                    title="Insufficient permissions",
                    description=f"The bot cannot edit message due to insufficient permissions.")
                await context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
            else:
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
        message_id = self.view.message_id

        if role and str(role.id) in [entry.payload for entry in self.view.model.buttons]:
            if len(self.view.model.buttons.related_objects) == 1:
                try:
                    await self.view.ctx.bot.rest.delete_message(channel_id, message_id)
                except hikari.NotFoundError:
                    pass
                except hikari.ForbiddenError:
                    embed = RespondEmbed.error(
                        title="Insufficient permissions",
                        description=f"The bot cannot edit message due to insufficient permissions.")
                    await context.respond(embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
                else:
                    await self.view.model.delete()
                    await context.edit_response(embed=RespondEmbed.success("Action Menus was deleted"))
            else:
                await ActionMenusButtonModel.filter(id_id=self.view.model.id, role_id=role.id).delete()
                for entry in self.view.model.buttons.related_objects:
                    if entry.payload == str(role.id):
                        try:
                            message = await self.view.bot.rest.fetch_message(channel_id, message_id)
                        except hikari.NotFoundError:
                            pass
                        else:  # Remove button if message still exists
                            view = miru.View.from_message(message, timeout=None)

                            for item in view.children:
                                if item.custom_id == f"ACM:{channel_id}:{entry.payload}":
                                    view.remove_item(item)
                            await message.edit(components=view.build())
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
        await context.respond(embed=RespondEmbed.success("Action Menus was deleted"),
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
        super().__init__(style=hikari.ButtonStyle.PRIMARY, label="Quit", emoji=MenuEmojiEnum.SAVE)

    async def callback(self, context: miru.ViewContext) -> None:
        for item in self.view.children:
            item.disabled = True
        kwargs = self.view.get_kwargs()
        await context.edit_response(**kwargs)
        self.view.stop()


class TitleModal(miru.Modal):
    title_input = miru.TextInput(label="Title",
                                 placeholder="The title of the embed.", max_length=128)

    def __init__(self, ) -> None:
        super().__init__("Title")
        self.title: t.Optional[str] = None
        self.add_item(self.title_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        title = ctx.values.get(self.title_input)
        self.title = title if title else hikari.UNDEFINED


class DescriptionModal(miru.Modal):
    description_input = miru.TextInput(label="Description",
                                       placeholder="The description of the embed.", max_length=4096)

    def __init__(self, ) -> None:
        super().__init__("Description")
        self.description: t.Optional[str] = None
        self.add_item(self.description_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        description = ctx.values.get(self.description_input)
        self.description = description if description else hikari.UNDEFINED


class ColorModal(miru.Modal):
    color_input = miru.TextInput(label="Color",
                                 placeholder="The color of the embed.", min_length=1)

    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.color: t.Optional[hikari.Color] = None
        self.add_item(self.color_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        self.color = helpers.is_color(ctx.values.get(self.color_input))


class AuthorModal(miru.Modal):
    author_input = miru.TextInput(label="Author",
                                  placeholder="The author of the embed. Appears above the title.", max_length=128)

    author_url_input = miru.TextInput(label="Author URL",
                                      placeholder="An URL pointing to an image to use for the author's avatar.")

    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.author_url: t.Optional[str] = None
        self.author: t.Optional[str] = None
        self.add_item(self.author_input)
        self.add_item(self.author_url_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.author_url_input)):
            self.author_url = ctx.values.get(self.author_url_input)
        author = ctx.values.get(self.author_input)
        self.author = author if author else hikari.UNDEFINED


class FooterModal(miru.Modal):
    footer_input = miru.TextInput(label="Footer",
                                  placeholder="The footer of the embed.",
                                  max_length=256)
    footer_url_input = miru.TextInput(label="Footer URL",
                                      placeholder="An url pointing to an image to use for the embed footer.",
                                      max_length=256)

    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.footer: t.Optional[str] = None
        self.footer_url: t.Optional[str] = None
        self.add_item(self.footer_input)
        self.add_item(self.footer_url_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.footer_url_input)):
            self.footer_url = ctx.values.get(self.footer_url_input)
        author = ctx.values.get(self.footer_input)
        self.footer = author if author else hikari.UNDEFINED


class ThumbnailModal(miru.Modal):
    thumbnail_input = miru.TextInput(label="Thumbnail URL",
                                     placeholder="An url pointing to an image to use for the thumbnail.",
                                     max_length=256)

    def __init__(self, ) -> None:
        super().__init__("Enter Role")
        self.thumbnail: t.Optional[str] = None
        self.add_item(self.thumbnail_input)

    async def callback(self, ctx: miru.ModalContext) -> None:
        if helpers.is_url(ctx.values.get(self.thumbnail_input)):
            self.thumbnail = ctx.values.get(self.thumbnail_input)
        else:
            self.thumbnail = hikari.UNDEFINED


class SelectEmbed(miru.Select[ViewT]):
    options = [
        miru.SelectOption(label="Title", value="__title", description="The title of the embed."),
        miru.SelectOption(label="Description", value="__description", description="The title of the embed."),
        miru.SelectOption(label="Color", value="__color", description="The color of the embed."),
        miru.SelectOption(label="Author", value="__author",
                          description="The author of the embed. Appears above the title."),
        miru.SelectOption(label="Footer", value="__footer", description="The footer of the embed."),
        miru.SelectOption(label="Thumbnail", value="__thumbnail",
                          description="An url pointing to an image to use for the thumbnail.")
    ]

    def __init__(self):
        super().__init__(options=self.options)

    async def callback(self, context: miru.ViewContext) -> None:
        value = self.values[0]
        if value == "__title":
            modal = TitleModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.title = modal.title
        elif value == "__description":
            modal = DescriptionModal()
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
        elif value == "__thumbnail":
            modal = ThumbnailModal()
            await context.respond_with_modal(modal)
            await modal.wait()
            self.view.acm_embed.set_thumbnail(modal.thumbnail)

        await self.view.send(modal.get_response_context())
