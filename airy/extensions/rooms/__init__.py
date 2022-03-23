import logging

import hikari
import lightbulb
from lightbulb import checks, decorators, plugins

from airy.core.models import VoiceChannelCreatorModel
from airy.utils.time import utcnow

from .room import VoiceRoom
from .cache import Cache

from airy.core import Airy

log = logging.getLogger(__name__)


class VoiceRoomsPlugin(plugins.Plugin):
    def __init__(self, name: str):
        super().__init__(name)


plugin = plugins.Plugin("VoiceRooms")
cache = Cache()


@plugin.listener(hikari.VoiceStateUpdateEvent)
async def on_voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
    voice_creators = await VoiceChannelCreatorModel.filter(guild_id=event.guild_id, channel_id=event.state.channel_id)
    if not voice_creators:
        return
    config = voice_creators[0]

    VoiceRoom(cache, config, event.state.member)


@plugin.command
@decorators.add_checks(checks.has_guild_permissions(hikari.Permissions.MANAGE_CHANNELS))
@lightbulb.add_checks(lightbulb.guild_only)
@decorators.command("voice", "Manages Voice Rooms")
@decorators.implements(lightbulb.SlashCommandGroup)
async def voice_room(_: lightbulb.Context):
    pass


@voice_room.child
@lightbulb.option("channel", "Voice Channel.",
                  required=True,
                  type=hikari.OptionType.CHANNEL,
                  channel_types=[hikari.ChannelType.GUILD_VOICE])
@lightbulb.option("channel_name", "The name of the created channels.",
                  required=True,
                  type=hikari.OptionType.STRING)
@lightbulb.option("user_limit", "Limits the number of users can connect to created voice channel. (Default: UNLIMITED)",
                  type=hikari.OptionType.INTEGER,
                  min_value=0,
                  max_value=99)
@lightbulb.option("editable", "Can channel owners edit them (Default: False).",
                  type=hikari.OptionType.BOOLEAN)
@lightbulb.option("additional_category_name", "The name of the created categories. (Default: VoiceRooms)",
                  type=hikari.OptionType.STRING)
@lightbulb.option("synchronization_perms", "Will created channels inherit permissions (Default: True).",
                  type=hikari.OptionType.BOOLEAN)
@lightbulb.option("auto_increment", "Whether to number created channels (Only if `editable` is False. Default: True).",
                  type=hikari.OptionType.BOOLEAN)
@decorators.command("create", "Initializes Voice Channels Creator", pass_options=True)
@decorators.implements(lightbulb.SlashSubCommand)
async def voice_room_create(ctx: lightbulb.SlashContext,
                            channel: hikari.GuildVoiceChannel,
                            channel_name: str,
                            user_limit: int = None,
                            editable: bool = False,
                            additional_category_name: str = "VoiceRooms",
                            synchronization_perms: bool = True,
                            auto_increment: bool = True):

    channel = ctx.bot.cache.get_guild_channel(channel)

    await VoiceChannelCreatorModel.create(guild_id=ctx.guild_id,
                                          channel_id=channel,
                                          channel_name=channel_name,
                                          user_limit=user_limit,
                                          editable=editable,
                                          auto_inc=auto_increment,
                                          additional_category_name=additional_category_name,
                                          sync_permissions=synchronization_perms)

    embed = hikari.Embed(title="Channel Creator successfully initialized.",
                         timestamp=utcnow()
                         )
    description = [f'Name of created channels: `{channel_name}`',
                   f'User Limit: `{user_limit}`',
                   f'Editable: `{editable}`',
                   f'Room numbering: `{auto_increment}`',
                   f'Synchronization Perms: `{synchronization_perms}`',
                   f"""Category:
                            >>> Name: `{additional_category_name}`"""]

    embed.description = '\n'.join(description)

    return await ctx.respond(embed=embed)


# def load(bot: Airy) -> None:
#     bot.add_plugin(plugin)
#     cache.init(bot)
#
#
# def unload(bot: Airy) -> None:
#     bot.remove_plugin(plugin)
