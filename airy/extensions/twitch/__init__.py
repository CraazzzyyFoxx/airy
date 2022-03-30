import datetime
import typing as t
import logging
import asyncio

import hikari
import lightbulb
import miru

from airy.core.models import AirySlashContext
from airy.core.bot import Airy

from airy.utils import SimplePages, RespondEmbed, format_dt, ColorEnum

logger = logging.getLogger(__name__)

timezone = lightbulb.Plugin("Twitch")


@timezone.command()
@lightbulb.command("timezone", "Manages timezones")
@lightbulb.implements(lightbulb.SlashCommandGroup)
async def tz_cmd(_: AirySlashContext):
    pass


# def load(bot: Airy) -> None:
#     bot.add_plugin(timezone)
#     pass
#
#
# def unload(bot: Airy) -> None:
#     bot.remove_plugin(timezone)
#     pass
