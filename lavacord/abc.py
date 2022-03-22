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

import abc
from datetime import timedelta, datetime, timezone
from typing import (
    List,
    Literal,
    Optional,
    TYPE_CHECKING,
    Type,
    TypeVar,
    Union,
    overload, ClassVar,
)

import hikari
import attr

from .enums import Icons

if TYPE_CHECKING:
    from .pool import Node

__all__ = (
    "Searchable",
    "Playlist",
    "Track",
    "SpotifyInfo"
)

ST = TypeVar("ST", bound="Searchable")


@attr.define(kw_only=True)
class Track:
    """A Lavalink track object.
    Attributes
    ------------
    id: str
        The Base64 Track ID, can be used to rebuild track objects.
    title: str
        The track title.
    identifier: Optional[str]
        The tracks' identifier. could be None depending on track type.
    length:
        The duration of the track in seconds.
    uri: Optional[str]
        The tracks URI. Could be None.
    author: Optional[str]
        The author of the track. Could be None
    requester: Optional[hikari.Snowflake]
        The requester of the track. . Could be None
    """

    track: str = attr.field(default=None)
    title: str = attr.field()
    identifier: Optional[str] = attr.field(default=None)
    uri: Optional[str] = attr.field()
    isSeekable: bool = attr.field()
    author: Optional[str] = attr.field()
    isStream: bool = attr.field()
    length: float = attr.field()
    sourceName: str = attr.field()
    position: str = attr.field()
    requester: Optional[hikari.Snowflake] = attr.field(default=None)

    def __repr__(self):
        return f"[{self.title} - {self.author}]({self.uri}) \n > " \
               f"({timedelta(milliseconds=self.length) if not self.isStream else 'Infinity'}) " \
               f"Requester: <@{self.requester}>"

    @property
    def thumbnail(self):
        return None


class Searchable(metaclass=abc.ABCMeta):
    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node,
            *,
            return_first: Literal[True] = ...
    ) -> Optional[ST]:
        ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node,
            *,
            return_first: Literal[False] = ...
    ) -> List[ST]:
        ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node,
            *,
            return_first: Literal[True] = ...
    ) -> Optional[ST]:
        ...

    @overload
    @classmethod
    @abc.abstractmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node,
            *,
            return_first: Literal[False] = ...
    ) -> List[ST]:
        ...

    @classmethod
    @abc.abstractmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node,
            *,
            return_first: bool = False
    ) -> Union[Optional[ST], List[ST]]:
        raise NotImplementedError


@attr.define(kw_only=True)
class Playlist(metaclass=abc.ABCMeta):
    """An ABC that defines the basic structure of a lavalink playlist resource"""

    _icon: ClassVar[Icons]
    _color: ClassVar[hikari.Color]

    name: str = attr.field()
    selectedTrack: int = attr.field()
    tracks: List[Track] = attr.field()
    requester: Optional[hikari.Snowflake] = attr.field()

    @overload
    @classmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = ...,
    ) -> Playlist:
        ...

    @classmethod
    async def search(
            cls: Type[ST],
            query: str,
            requester: hikari.Snowflake,
            node: Node = None,
    ) -> Playlist:
        raise NotImplementedError

    @property
    def thumbnail(self):
        return None

    @property
    def embed(self) -> hikari.Embed:
        emb = hikari.Embed(color=self._color, timestamp=datetime.now(timezone.utc))
        emb.description = self.name
        if self.thumbnail:
            emb.set_thumbnail(self.thumbnail)
        emb.add_field(name='Duration',
                      value=str(timedelta(milliseconds=sum([track.length for track in self.tracks]))))
        emb.set_author(icon=self._icon, name='Playlist Added to Queue')
        return emb


@attr.define(kw_only=True)
class SpotifyInfo:
    id: str = attr.field()
    thumbnail: str = attr.field()

