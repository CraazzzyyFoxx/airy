import logging

import hikari
import lightbulb
import miru

from airy.core.models import AirySlashContext
from airy.core.bot import Airy

from airy.utils.embeds import EmbedConstructor, EmbedSettings

logger = logging.getLogger(__name__)

test = lightbulb.Plugin("Test")


@test.listener(hikari.StartedEvent)
async def start_views(event: hikari.StartedEvent) -> None:
    PersistentThing().start_listener()


class PersistentThing(miru.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @miru.button(label="Foo!", style=hikari.ButtonStyle.SUCCESS, custom_id="foo")
    async def foo_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        await ctx.respond("You clicked foo!")

    @miru.button(label="Bar!", style=hikari.ButtonStyle.SUCCESS, custom_id="bar")
    async def bar_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        await ctx.respond("You clicked bar!")


class BasicView(miru.View):

    # Define a new Select menu with two options
    @miru.select(
        placeholder="Select me!",
        options=[
            miru.SelectOption(label="Option 1"),
            miru.SelectOption(label="Option 2"),
        ],
    )
    async def basic_select(self, select: miru.Select, ctx: miru.ViewContext) -> None:
        await ctx.respond(f"You've chosen {select.values[0]}!")

    # Define a new Button with the Style of success (Green)
    @miru.button(label="Click me!", style=hikari.ButtonStyle.SUCCESS)
    async def basic_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        await ctx.respond("You clicked me!")

    # Define a new Button that when pressed will stop the view & invalidate all the buttons in this view
    @miru.button(label="Modal!", style=hikari.ButtonStyle.PRIMARY)
    async def stop_button(self, button: miru.Button, ctx: miru.ViewContext) -> None:
        modal = BasicModal()
        await ctx.respond_with_modal(modal)


class BasicModal(miru.Modal):
    def __init__(self) -> None:
        super().__init__("Miru is cool!")
        self.add_item(miru.TextInput(label="Enter something!", placeholder="Miru is cool!"))
        self.add_item(
            miru.TextInput(
                label="Enter something long!",
                style=hikari.TextInputStyle.PARAGRAPH,
                min_length=200,
                max_length=1000,
            )
        )

    async def callback(self, ctx: miru.ModalContext) -> None:
        await ctx.respond(self.values)


@test.command
@lightbulb.command("mirupersistent", "Test miru persistent unbound")
@lightbulb.implements(lightbulb.SlashCommand)
async def miru_persistent(ctx: AirySlashContext) -> None:
    await ctx.respond("Beep Boop!", components=PersistentThing().build())


@test.command
@lightbulb.option("nonce", "The nonce to send.")
@lightbulb.command("nonce", "foo")
@lightbulb.implements(lightbulb.SlashCommand)
async def nonce_thing(ctx: AirySlashContext) -> None:
    await ctx.respond(f"Sending nonce: {ctx.options.nonce}", flags=hikari.MessageFlag.EPHEMERAL)
    await ctx.app.rest.create_message(ctx.channel_id, "Foo", nonce=ctx.options.nonce)


# @test.listener(hikari.GuildMessageCreateEvent)
# async def nonce_printer(event: hikari.GuildMessageCreateEvent) -> None:
#     print(f"Nonce is: {event.message.nonce}")


@test.command
@lightbulb.command("mirutest", "Test miru views")
@lightbulb.implements(lightbulb.SlashCommand)
async def viewtest(ctx: AirySlashContext) -> None:
    view = BasicView()
    view.add_item(miru.Button(label="Settings!", url="discord://-/settings/advanced"))
    resp = await ctx.respond("foo", components=view.build())
    view.start(await resp.message())


@test.command
@lightbulb.command("modaltest", "Test miru modals")
@lightbulb.implements(lightbulb.SlashCommand)
async def modaltest(ctx: AirySlashContext) -> None:
    modal = BasicModal()
    await modal.send(ctx.interaction)


@test.command
@lightbulb.command("embedcreator", "Test miru nav")
@lightbulb.implements(lightbulb.SlashCommand)
async def navtest(ctx: AirySlashContext) -> None:
    constr = EmbedConstructor(ctx=ctx)
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    await constr.start_embed()


# def load(bot: Airy) -> None:
#     bot.add_plugin(test)
#     pass
#
#
# def unload(bot: Airy) -> None:
#     bot.remove_plugin(test)
#     pass
