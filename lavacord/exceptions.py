"""
The MIT License (MIT)

Copyright (c) 2022 CraazzzyyFoxx

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from .enums import ErrorSeverity


class LavacordError(Exception):
    """Base WaveLink Exception"""


class AuthorizationFailure(LavacordError):
    """Exception raised when an invalid password is provided toa node."""


class LavalinkException(LavacordError):
    """Exception raised when an error occurs talking to Lavalink."""


class LoadTrackError(LavalinkException):
    """Exception raised when an error occurred when loading a track."""

    def __init__(self, data):
        exception = data["exception"]
        self.severity: ErrorSeverity = ErrorSeverity[exception["severity"]]
        super().__init__(exception["message"])


class BuildTrackError(LavalinkException):
    """Exception raised when a track is failed to be decoded and re-built."""

    def __init__(self, data):
        super().__init__(data["error"])


class NodeOccupied(LavacordError):
    """Exception raised when node identifiers conflict."""


class InvalidIDProvided(LavacordError):
    """Exception raised when an invalid ID is passed somewhere in Wavelink."""


class ZeroConnectedNodes(LavacordError):
    """Exception raised when an operation is attempted with nodes, when there are None connected."""


class NoMatchingNode(LavacordError):
    """Exception raised when a Node is attempted to be retrieved with a incorrect identifier."""


class QueueException(LavacordError):
    """Base WaveLink Queue exception."""

    pass


class QueueFull(QueueException):
    """Exception raised when attempting to add to a full Queue."""

    pass


class QueueEmpty(QueueException):
    """Exception raised when attempting to retrieve from an empty Queue."""

    pass


class QueueHistoryEmpty(QueueEmpty):
    pass


class FiltersError(Exception):
    """
    A error for all filters.
    Parameters
    ----------
    message: :class:`str`
        the error message
    """

    def __init__(self, message: str) -> None:
        self._message = message

    @property
    def message(self):
        """
        A error message.
        """
        return self._message
