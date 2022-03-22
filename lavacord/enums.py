"""
The MIT License (MIT)

Copyright (c) 2022 CraazzzyyFoxx

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

from hikari.internal.enums import Enum

__all__ = (
    "RepeatMode",
    "ShuffleMode",
    "Icons",
    "LoadType",
    "ErrorSeverity"
)


class RepeatMode(str, Enum):
    OFF = "OFF"
    ONE = "ONE"
    ALL = "ALL"


class ShuffleMode(int, Enum):
    OFF = 0
    ON = 1


class ErrorSeverity(str, Enum):
    common = "COMMON"
    suspicious = "SUSPICIOUS"
    fault = "FAULT"


class LoadType(str, Enum):
    track_loaded = "TRACK_LOADED"
    playlist_loaded = "PLAYLIST_LOADED"
    search_result = "SEARCH_RESULT"
    no_matches = "NO_MATCHES"
    load_failed = "LOAD_FAILED"


class Icons(str, Enum):
    spotify = "https://cdn.discordapp.com/emojis/908292227657240578.png"
    twitch = "https://cdn.discordapp.com/emojis/908292214067691573.png"
    youtube = "https://cdn.discordapp.com/emojis/908292349170446336.png"
    youtubemusic = "https://cdn.discordapp.com/emojis/908292237786497034.png"
    soundcloud = "https://cdn.discordapp.com/emojis/954864037596917850.png"
