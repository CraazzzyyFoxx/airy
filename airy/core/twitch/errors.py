from typing import Any, Optional


__all__ = (
    "TwitchIOException",
    "AuthenticationError",
    "InvalidContent",
    "IRCCooldownError",
    "EchoMessageWarning",
    "NoClientID",
    "NoToken",
    "HTTPException",
    "Unauthorized",
)


class TwitchIOException(Exception):
    pass


class AuthenticationError(TwitchIOException):
    pass


class InvalidContent(TwitchIOException):
    pass


class IRCCooldownError(TwitchIOException):
    pass


class EchoMessageWarning(TwitchIOException):
    pass


class NoClientID(TwitchIOException):
    pass


class NoToken(TwitchIOException):
    pass


class HTTPException(TwitchIOException):
    def __init__(
        self, message: str, *, reason: Optional[str] = None, status: Optional[int] = None, extra: Optional[Any] = None
    ):

        self.message = message
        self.reason = reason
        self.status = status
        self.extra = extra


class Unauthorized(HTTPException):
    pass
