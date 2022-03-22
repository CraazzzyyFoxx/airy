"""
MIT License

Copyright (c) 2022 CrazzzyyFoxx

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from __future__ import annotations

import asyncio.exceptions
import json
import logging
import os
from pprint import pprint
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

import aiohttp
import hikari
import tekore

from . import abc
from .enums import *
from .exceptions import *
from .stats import Stats
from .websocket import Websocket
from .player import BasePlayer
from .tracks import SearchableTrack

__all__ = (
    "Node",
    "NodePool",
)

PT = TypeVar("PT", bound=SearchableTrack)
PLT = TypeVar("PLT", bound=abc.Playlist)

logger: logging.Logger = logging.getLogger(__name__)


class Node:
    """Lavacord Node object.
    Attributes
    ----------
    bot: :class:`hikari.GatewayBot`
        The discord.py Bot object.
    .. warning::
        This class should not be created manually. Please use :meth:`NodePool.create_node()` instead.
    """

    def __init__(
            self,
            bot: hikari.GatewayBot,
            host: str,
            port: int,
            password: str,
            *,
            https: bool = False,
            heartbeat: float = 30,
            dumps: Callable[[Any], str],
            region: Optional[hikari.VoiceRegion] = None,
            spotify_client_id: Optional[str] = None,
            spotify_client_secret: Optional[str] = None,
            identifier: str = None,
            resume_key: Optional[str] = None,
    ):
        self.bot = bot
        self._host: str = host
        self._port: int = port
        self._password: str = password
        self._https: bool = https
        self._heartbeat: float = heartbeat
        self._region: Optional[hikari.VoiceRegion] = region
        self._identifier: str = identifier or str(os.urandom(8).hex())
        self.resume_key = resume_key or str(os.urandom(8).hex())
        self._dumps: Callable[[Any], str] = dumps

        self._players: Dict[hikari.Snowflake, BasePlayer] = {}
        self._websocket: Optional[Websocket] = None
        self.stats: Optional[Stats] = None
        self._spotify: Optional[tekore.Spotify] = None

        if spotify_client_id and spotify_client_secret:
            self._spotify = tekore.Spotify(tekore.request_client_token(spotify_client_id,
                                                                       spotify_client_secret), asynchronous=True)

    def __repr__(self) -> str:
        return f"<Lavacord Node: <{self.identifier}>, Region: <{self.region}>, Players: <{len(self._players)}>>"

    @property
    def host(self) -> str:
        """The host this node is connected to."""
        return self._host

    @property
    def port(self) -> int:
        """The port this node is connected to."""
        return self._port

    @property
    def region(self) -> Optional[hikari.VoiceRegion]:
        """The voice region of the Node."""
        return self._region

    @property
    def identifier(self) -> str:
        """The Nodes unique identifier."""
        return self._identifier

    @property
    def players(self) -> Dict[hikari.Snowflake, BasePlayer]:
        """A list of currently connected Players."""
        return self._players

    @property
    def penalty(self) -> float:
        """The load-balancing penalty for this node."""
        if self.stats is None:
            return 9e30

        return self.stats.penalty.total

    @property
    def spotify(self) -> tekore.Spotify:
        return self._spotify

    def is_connected(self) -> bool:
        """Bool indicating whether or not this Node is currently connected to Lavalink."""
        if self._websocket is None:
            return False

        return self._websocket.is_connected()

    async def connect(self) -> None:
        self._websocket = Websocket(node=self)
        await self._websocket.connect()

    async def create_player(self, voice_state: hikari.VoiceState, cls=BasePlayer):
        player = cls(voice_state.guild_id, voice_state.channel_id, node=self)
        self._players[voice_state.guild_id] = player
        return player

    def get_player(self, guild_id: hikari.Snowflake) -> Optional[Type[BasePlayer]]:
        return self._players.get(guild_id)

    async def _get_data(
            self, endpoint: str, params: dict
    ) -> Tuple[Dict[str, Any], aiohttp.ClientResponse]:
        headers = {"Authorization": self._password}
        async with self._websocket.session.get(
                f"{self._websocket.host}/{endpoint}", headers=headers, params=params
        ) as resp:
            data = await resp.json()

        return data, resp

    async def _loadtracks(self, query):
        data, resp = await self._get_data("loadtracks", {"identifier": query})
        if resp.status != 200:
            raise LavalinkException("Invalid response from Lavalink server.")

        load_type = LoadType(data.get("loadType"))

        if load_type is LoadType.load_failed:
            raise LoadTrackError(data)

        if load_type is LoadType.no_matches:
            raise LavalinkException("Track not found.")

        return data, load_type

    async def get_tracks(self, cls: Type[PT],
                         query: str,
                         requester: hikari.Snowflake,
                         *,
                         return_first: bool = True,
                         payload=None
                         ) -> List[PT]:
        if payload is None:
            payload = {}

        query = f"{cls._search_type}:{query}" if cls._search_type else query

        data, load_type = await self._loadtracks(query)
        if load_type is LoadType.track_loaded or return_first:
            track_data_ = data["tracks"][0]
            return cls(track=track_data_["track"], requester=requester, **(track_data_["info"] | payload))

        return [
            cls(track=track_data_["track"], requester=requester, **(track_data_["info"] | payload))
            for track_data_ in data["tracks"]
        ]

    async def get_playlist(self,
                           cls: Type[PLT],
                           cls_track: Type[PT],
                           query: str,
                           requester: hikari.Snowflake,
                           *,
                           payload=None
                           ) -> Optional[PLT]:
        if payload is None:
            payload = {}

        data, load_type = await self._loadtracks(query)
        if load_type is not LoadType.playlist_loaded:
            raise LavalinkException("Track failed to load.")

        return cls(tracks=[cls_track(track=track['track'], **track['info'], requester=requester)
                           for track in data.get("tracks")],
                   requester=requester,
                   **(data.get("playlistInfo") | payload))

    async def build_track(self, cls: Type[PT], identifier: str) -> PT:
        data, resp = await self._get_data("decodetrack", {"track": identifier})

        if resp.status != 200:
            raise BuildTrackError(data)

        return cls(track=identifier, **data)

    async def disconnect(self) -> None:
        for player in self.players.values():
            await player.disconnect()

        await self.cleanup()

    async def cleanup(self) -> None:
        try:
            self._websocket.listener.cancel()
        except asyncio.exceptions.CancelledError:
            pass

        try:
            await self._websocket.session.close()
        except (aiohttp.ClientConnectorError, aiohttp.WSServerHandshakeError, aiohttp.ServerDisconnectedError) as error:
            logger.error(f"During websocket close :: {error}")

        del NodePool._nodes[self._identifier]


class NodePool:
    _nodes: ClassVar[Dict[str, Node]] = {}

    @classmethod
    async def create_node(
            cls,
            bot: hikari.GatewayBot,
            host: str,
            port: int,
            password: str,
            *,
            https: bool = False,
            heartbeat: float = 30,
            region: Optional[hikari.VoiceRegion] = None,
            spotify_client_id: Optional[str] = None,
            spotify_client_secret: Optional[str] = None,
            identifier: str = None,
            dumps: Callable[[Any], str] = json.dumps,
            resume_key: Optional[str] = None,
    ) -> Node:

        if identifier in cls._nodes:
            raise NodeOccupied(f"A node with identifier <{identifier}> already exists in this pool.")

        node = Node(
            bot=bot,
            host=host,
            port=port,
            password=password,
            https=https,
            heartbeat=heartbeat,
            region=region,
            spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret,
            identifier=identifier,
            dumps=dumps,
            resume_key=resume_key
        )

        cls._nodes[node.identifier] = node
        await node.connect()

        return node

    @classmethod
    def get_node(
            cls, *, identifier: str = None, region: hikari.VoiceRegion = None
    ) -> Node:
        if not cls._nodes:
            raise ZeroConnectedNodes("There are no connected Nodes on this pool.")

        if identifier is not None:
            try:
                node = cls._nodes[identifier]
            except KeyError:
                raise NoMatchingNode(f"No Node with identifier <{identifier}> exists.")
            else:
                return node

        elif region is not None:
            nodes = [n for n in cls._nodes.values() if n.region is region]
            if not nodes:
                raise ZeroConnectedNodes(
                    f"No Nodes for region <{region}> exist on this pool."
                )
        else:
            nodes = cls._nodes.values()

        return sorted(nodes, key=lambda n: len(n.players))[0]

    @classmethod
    async def get_player(cls, guild_id: hikari.Snowflake) -> t.Optional[BasePlayer]:
        for node in NodePool._nodes.values():
            player = node.get_player(guild_id)
            if player is not None:
                return player

        return None
