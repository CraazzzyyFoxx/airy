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

import asyncio
import typing as t

from datetime import timedelta

import attr
import hikari
import tekore

from tekore._model import FullAlbum, FullPlaylist, SimpleTrack, PlaylistTrack

from airy.utils import utcnow

from .abc import Playlist, Track, SpotifyInfo
from .enums import Icons

if t.TYPE_CHECKING:
    from .pool import Node

__all__ = (
    "SearchableTrack",
    "YouTubeTrack",
    "YouTubeMusicTrack",
    "SoundCloudTrack",
    "YouTubePlaylist",
    "SpotifyTrack",
    "YouTubeMusicPlaylist",
    "SpotifyPlaylist",
    "TwitchTrack",
    "SpotifyAlbum",
)

ST = t.TypeVar("ST", bound="SearchableTrack")


@attr.define(kw_only=True, repr=False)
class SearchableTrack(Track):
    _search_type: t.ClassVar[str]
    _icon: t.ClassVar[Icons]
    _color: t.ClassVar[hikari.Color]
    _spotify = False

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = None,
            *,
            return_first: bool = True
    ) -> t.List[Track]:
        tracks = await node.get_tracks(cls, query=query, requester=requester, return_first=return_first)

        if tracks is not None:
            return tracks

    @property
    def embed(self) -> hikari.Embed:
        emb = hikari.Embed(color=self._color, timestamp=utcnow())
        emb.set_thumbnail(self.thumbnail)
        emb.description = self.title
        emb.add_field(name='Duration', value=str(timedelta(milliseconds=self.length)
                                                 if not self.isStream else 'Infinity'))
        emb.set_author(icon=self._icon, name='Track Added to Queue')
        return emb


class YouTubeTrack(SearchableTrack):
    """A track created using a search to YouTube."""

    _search_type = "ytsearch"
    _color = hikari.Color.from_hex_code("#ff0101")
    _icon = Icons.youtube
    _spotify = False

    @property
    def thumbnail(self) -> str:
        """The URL to the thumbnail of this video."""
        return f"https://img.youtube.com/vi/{self.identifier}/maxresdefault.jpg"


class YouTubeMusicTrack(SearchableTrack):
    """A track created using a search to YouTube Music."""

    _search_type = "ytmsearch"
    _color = hikari.Color.from_hex_code("#ff0101")
    _icon = Icons.youtubemusic
    _spotify = False

    @property
    def thumbnail(self) -> str:
        """The URL to the thumbnail of this video."""
        return f"https://i.ytimg.com/vi/{self.identifier}/maxresdefault.jpg"


class TwitchTrack(SearchableTrack):
    """A track created using a search to Twitch."""
    _search_type = ""
    _color = hikari.Color.from_hex_code("#9448ff")
    _icon = Icons.twitch
    _spotify = False


class SoundCloudTrack(SearchableTrack):
    """A track created using a search to SoundCloud."""

    _search_type = "scsearch"
    _color = hikari.Color.from_hex_code("#f08f16")
    _icon = Icons.soundcloud
    _spotify = False


@attr.define(kw_only=True, repr=False)
class SpotifyTrack(YouTubeMusicTrack):
    """A track retrieved via YouTubeMusic with a Spotify URL/ID."""
    _color = hikari.Color.from_hex_code("#1ed760")
    _icon = Icons.spotify
    _spotify = True

    spotify_info: SpotifyInfo = attr.field()

    @property
    def uri(self):
        return f'https://open.spotify.com/track/{self.spotify_info.id}'

    @property
    def thumbnail(self) -> str:
        return self.spotify_info.thumbnail

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = None,
            *,
            return_first: bool = True
    ) -> t.List[Track]:
        track_: tekore.model.FullTrack = await node.spotify.track(query)
        artists = [artist.name for artist in track_.artists]
        query = f'{track_.name} {", ".join(artists)}'
        return await node.get_tracks(cls,
                                     query,
                                     requester,
                                     payload=dict(spotify_info=SpotifyInfo(id=track_.id,
                                                                           thumbnail=track_.album.images[0].url)),
                                     return_first=return_first)


@attr.define(kw_only=True, repr=False)
class YouTubePlaylist(Playlist):
    _icon = Icons.youtube
    _color = hikari.Color.from_hex_code("#ff0101")
    _spotify = False

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = ...,
    ) -> YouTubePlaylist:
        return await node.get_playlist(cls, YouTubeTrack, query, requester)


@attr.define(kw_only=True, repr=False)
class YouTubeMusicPlaylist(Playlist):
    _icon = Icons.youtubemusic
    _color = hikari.Color.from_hex_code("#ff0101")
    _spotify = False

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = ...,
    ) -> YouTubeMusicPlaylist:
        return await node.get_playlist(cls, YouTubeMusicTrack, query, requester)


class SpotifyAlbum(Playlist):
    _icon = Icons.spotify
    _color = hikari.Color.from_hex_code("#1ed760")
    _spotify = True

    name: str = attr.field()
    uri: str = attr.field()
    thumbnail: str = attr.field()

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = None,
    ) -> SpotifyAlbum:
        playlist: FullAlbum = await node.spotify.album(query)
        tracks = []

        async def func(track: SimpleTrack):
            artists = [artist.name for artist in track.artists]
            query = f'{track.name} {", ".join(artists)}'
            print(track.preview_url)
            print(track.href)
            track_ = await node.get_tracks(SpotifyTrack,
                                           query=query,
                                           requester=requester,
                                           return_first=True,
                                           payload=dict(spotify_info=SpotifyInfo(id=query,
                                                                                 thumbnail=track.preview_url)))
            if track_ is None:
                return

            tracks.append(track_)

        tasks = []

        for track in playlist.tracks.items:
            tasks.append(asyncio.create_task(func(track)))
        await asyncio.wait(tasks)

        return cls(tracks=tracks,
                   name=playlist.name,
                   selectedTrack=len(tracks),
                   uri=playlist.uri,
                   thumbnail=playlist.images[0].url,
                   requester=requester)


@attr.define(kw_only=True, repr=False)
class SpotifyPlaylist(Playlist):
    _icon = Icons.spotify
    _color = hikari.Color.from_hex_code("#1ed760")
    _spotify = False

    name: str = attr.field()
    uri: str = attr.field()
    thumbnail: str = attr.field()

    @classmethod
    async def search(
            cls: t.Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = None,
    ) -> SpotifyAlbum:
        playlist: FullPlaylist = await node.spotify.playlist(query)
        tracks = []

        async def func(track: PlaylistTrack):
            artists = [artist.name for artist in track.track.artists]
            query = f'{track.track.name} {", ".join(artists)}'
            track_ = await node.get_tracks(SpotifyTrack,
                                           query=query,
                                           requester=requester,
                                           return_first=True,
                                           payload=dict(spotify_info=SpotifyInfo(id=track.track.id,
                                                                                 thumbnail=track.track.album.images[
                                                                                     0].url)))
            if track_ is None:
                return

            tracks.append(track_)

        tasks = []

        for track in playlist.tracks.items:
            tasks.append(asyncio.create_task(func(track)))
        await asyncio.wait(tasks)

        return cls(tracks=tracks,
                   name=playlist.name,
                   selectedTrack=len(tracks),
                   uri=playlist.uri,
                   thumbnail=playlist.images[0].url,
                   requester=requester)
