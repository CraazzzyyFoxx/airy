import functools
import operator

import hikari
import lightbulb
import miru
import lavacord


from airy.core import AirySlashContext, NoVoiceChannel, MissingPermissionsToEditPlayer
from airy.utils import helpers

reduced = functools.reduce(operator.or_, [hikari.Permissions.ADMINISTRATOR, hikari.Permissions.MANAGE_GUILD])


async def _is_connected(ctx: AirySlashContext) -> bool:
    states = ctx.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
    if not voice_state:
        raise NoVoiceChannel("You are not in a voice channel.")
    return True


async def _can_edit_player(ctx: AirySlashContext) -> bool:
    player = await lavacord.NodePool.get_player(ctx.guild_id)
    if not player or ctx.command.name in ["play", "queue"]:
        return True

    if player.queue.current_track.requester == ctx.author.id:
        return True

    perms = lightbulb.utils.permissions_for(ctx.member)
    if helpers.includes_permissions(perms, reduced):
        return True

    raise MissingPermissionsToEditPlayer()


async def _can_edit_player_buttons(ctx: miru.ViewContext) -> bool:
    player = await lavacord.NodePool.get_player(ctx.guild_id)

    if not player:
        return True

    if player.queue.current_track.requester == ctx.author.id:
        return True

    perms = lightbulb.utils.permissions_for(ctx.member)
    if helpers.includes_permissions(perms, reduced):
        return True

    raise MissingPermissionsToEditPlayer()


def is_connected() -> lightbulb.Check:
    return lightbulb.Check(functools.partial(_is_connected))


def can_edit_player() -> lightbulb.Check:
    return lightbulb.Check(functools.partial(_can_edit_player))
