import functools
import operator

import hikari
import lightbulb
import miru
import lavacord


from airy.core import AirySlashContext, NoVoiceChannel, MissingPermissionsToEditPlayer
from airy.utils import helpers

reduced = functools.reduce(operator.or_, [hikari.Permissions.ADMINISTRATOR, hikari.Permissions.MANAGE_GUILD])


async def _is_connected(context: AirySlashContext) -> bool:
    states = context.bot.cache.get_voice_states_view_for_guild(context.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == context.author.id)]
    if not voice_state:
        raise NoVoiceChannel("You are not in a voice channel.")
    return True


async def _can_edit_player(context: AirySlashContext) -> bool:
    player = await lavacord.NodePool.get_player(context.guild_id)
    if not player or context.command.name in ["play", "queue"]:
        return True

    if player.queue.current_track.requester == context.author.id:
        return True

    perms = lightbulb.utils.permissions_for(context.member)
    if helpers.includes_permissions(perms, reduced):
        return True

    raise MissingPermissionsToEditPlayer("You don't have permissions to interact with this player")


async def _can_edit_player_buttons(context: miru.ViewContext) -> bool:
    player = await lavacord.NodePool.get_player(context.guild_id)

    if not player:
        return True

    if player.queue.current_track.requester == context.author.id:
        return True

    perms = lightbulb.utils.permissions_for(context.member)
    if helpers.includes_permissions(perms, reduced):
        return True

    raise MissingPermissionsToEditPlayer("You don't have permissions to interact with this player")


can_edit_player = lightbulb.Check(_can_edit_player)
is_connected = lightbulb.Check(_is_connected)
