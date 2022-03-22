import typing as t

import hikari
import lavacord
import lightbulb
import orjson

from tekore import Spotify, request_client_token

from airy.config import lavalink_config, spotify_config
from airy.core import AiryPlugin, AirySlashContext
from airy.utils import RespondEmbed, SimplePages

from .checks import can_edit_player, is_connected
from .player import AiryPlayer


class MusicPlugin(AiryPlugin):
    def __init__(self):
        super().__init__(name="MusicPlugin")
        self.lavalink: t.Optional[lavacord.LavalinkClient] = None
        self.spotify = Spotify(request_client_token(spotify_config.client_id,
                                                    spotify_config.client_secret), asynchronous=True)

        self.add_checks(lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.CONNECT),
                        lightbulb.checks.bot_has_guild_permissions(hikari.Permissions.SPEAK),
                        is_connected(),
                        can_edit_player()
                        )

    def init(self):
        self.bot.subscribe(hikari.ShardReadyEvent, self.start_lavalink)

    async def start_lavalink(self, _: hikari.StartedEvent) -> None:
        self.lavalink = lavacord.LavalinkClient(self.bot)
        await lavacord.NodePool.create_node(bot=self.bot,
                                            host=lavalink_config.url,
                                            port=2333,
                                            password=lavalink_config.password,
                                            spotify_client_id=spotify_config.client_id,
                                            spotify_client_secret=spotify_config.client_secret,
                                            dumps=orjson.dumps)

    async def join(self, ctx: AirySlashContext) -> t.Optional[AiryPlayer]:
        states = self.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
        voice_state = [state async for state in states.iterator().filter(lambda i: i.user_id == ctx.author.id)]
        if not voice_state:
            return None

        player: AiryPlayer = await self.lavalink.create_player(voice_state[0], cls=AiryPlayer)  # type: ignore
        player.text_channel_id = ctx.channel_id
        await player.connect(self_deaf=True)
        return player


plugin = MusicPlugin()


@plugin.listener(lavacord.TrackExceptionEvent)
@plugin.listener(lavacord.TrackEndEvent)
async def track_end(event: lavacord.TrackEndEvent):
    player = event.player

    states = plugin.bot.cache.get_voice_states_view_for_guild(event.guild_id)
    voice_states = [state async for state in states.iterator()
        .filter(lambda i: i.channel_id == player.voice_state.channel_id)]

    if len(voice_states) == 0 or not player.queue:
        return await event.player.destroy()

    await player.play(player.queue.get_next_track())
    await player.send_menu()


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("join", "Lets Airy connect to a voice channel.")
@lightbulb.implements(lightbulb.SlashCommand)
async def connect_cmd(ctx: AirySlashContext):
    player = await plugin.join(ctx)
    if player:
        await ctx.respond(embed=RespondEmbed.success("Joined voice channel."))


@plugin.command()
@lightbulb.add_cooldown(10, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.option("song", "The name of the song (or url) that you want to play.", type=hikari.OptionType.STRING)
@lightbulb.command("play", "Queues Track/Playlist/Stream or resume playback.")
@lightbulb.implements(lightbulb.SlashCommand)
async def play_cmd(ctx: AirySlashContext):
    """Searches the query on youtube, or adds the URL to the queue."""
    await ctx.respond(hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    query = ctx.options.song

    if not query:
        await ctx.respond("Please specify a query.")
        return None

    player = await plugin.lavalink.get_player(ctx.guild_id)
    # Join the user's voice channel if the bot is not in one.
    if not player:
        player = await plugin.join(ctx)

    if not player:
        return

    data = await player.search_tracks(query, ctx.member.id)

    if not data:  # tracks is empty
        await ctx.respond("Could not find any video of the search query.")
        return
    if isinstance(data, lavacord.Playlist):
        player.queue.extend(data.tracks)
    else:
        player.queue.put(data)

    if not player.is_playing():
        await player.play(player.queue.get_next_track())
    await ctx.respond(embed=data.embed)
    await player.send_menu(ctx)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.add_cooldown(3, 3, lightbulb.cooldowns.buckets.UserBucket)
@lightbulb.command("leave", "Lets Airy clear the queue and disconnect.")
@lightbulb.implements(lightbulb.SlashCommand)
async def leave_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return

    await player.destroy()
    await ctx.respond(embed=RespondEmbed.success("Disconnected"))


@plugin.command()
@lightbulb.add_cooldown(30, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("queue", "Shows queue")
@lightbulb.implements(lightbulb.SlashCommand)
async def queue_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return
    pages = SimplePages(player.queue.__str__(), ctx=ctx)
    await pages.send(ctx.interaction)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("pause", "Pauses the playback.")
@lightbulb.implements(lightbulb.SlashCommand)
async def pause_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return

    await player.pause()
    await player.send_menu(ctx)
    await ctx.respond(embed=RespondEmbed.success("Playback was paused"), flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("resume", "Resumes the playback.")
@lightbulb.implements(lightbulb.SlashCommand)
async def resume_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return

    await player.resume()
    await player.send_menu(ctx)
    await ctx.respond(embed=RespondEmbed.success("Playback was resumed"), flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("skip", "Skips the current song.")
@lightbulb.implements(lightbulb.SlashCommand)
async def skip_cmd(_: AirySlashContext):
    pass


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("fskip", "Skips the current song without voting)")
@lightbulb.implements(lightbulb.SlashCommand)
async def fskip_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return
    await player.stop()
    await player.send_menu(ctx)
    await ctx.respond(embed=RespondEmbed.success("Track was skipped"), flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.command("fprevious", "Plays the previous song without voting")
@lightbulb.implements(lightbulb.SlashCommand)
async def previous_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return
    player.queue.get_previous_track()
    await player.stop()
    await player.send_menu(ctx)
    await ctx.respond(embed=RespondEmbed.success("Previous track was started"), flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.add_cooldown(8, 3, lightbulb.cooldowns.buckets.GuildBucket)
@lightbulb.add_checks(lightbulb.checks.has_guild_permissions(hikari.Permissions.CONNECT))
@lightbulb.option("mode", "Repeat mode", choices=["OFF", "ONE", "ALL"])
@lightbulb.command("repeat", "Enables or disables song / queue repeat.")
@lightbulb.implements(lightbulb.SlashCommand)
async def repeat_cmd(ctx: AirySlashContext):
    player: AiryPlayer = await plugin.lavalink.get_player(ctx.guild_id)  # type: ignore
    if not player:
        return
    player.queue.set_repeat_mode(lavacord.RepeatMode(ctx.options.mode))
    await player.send_menu(ctx)
    await ctx.respond(embed=RespondEmbed.success(f"Repeat mode was set to {ctx.options.mode}"),
                      flags=hikari.MessageFlag.EPHEMERAL)


def load(bot):
    bot.add_plugin(plugin)
    plugin.init()


def unload(bot):
    bot.remove_plugin(plugin)
