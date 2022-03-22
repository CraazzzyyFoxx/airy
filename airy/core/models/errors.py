import lightbulb


__all__ = ("TagAlreadyExists",
           "TagNotFound",
           "RoleHierarchyError",
           "PlayerException",
           "MissingPermissionsToEditPlayer",
           "TimeConversionError",
           "MemberExpectedError",
           "DMFailedError",
           "UserBlacklistedError",
           'BotRoleHierarchyError',
           "NoVoiceChannel",
           "TimeInPast",
           "TimeInFuture",
           "PlayerNotFound",
           "AlreadyConnected",
            )


class TagAlreadyExists(Exception):
    """
    Raised when a tag is trying to get created but already exists.
    """


class TagNotFound(Exception):
    """
    Raised when a tag is not found, although most functions just return None.
    """


class RoleHierarchyError(lightbulb.CheckFailure):
    """
    Raised when an action fails due to role hierarchy.
    """


class BotRoleHierarchyError(lightbulb.CheckFailure):
    """
    Raised when an action fails due to the bot's role hierarchy.
    """


class MemberExpectedError(Exception):
    """
    Raised when a command expected a member and received a user instead.
    """


class UserBlacklistedError(Exception):
    """
    Raised when a user who is blacklisted from using the application tries to use it.
    """
 
    
class DMFailedError(Exception):
    """
    Raised when DMing a user fails while executing a moderation command.
    """


class TimeConversionError(Exception):
    """
    Raised when a tag is not found, although most functions just return None.
    """


class TimeInPast(TimeConversionError):
    pass


class TimeInFuture(TimeConversionError):
    pass


class PlayerException(Exception):
    """Base Player Exception"""


class PlayerNotFound(PlayerException):
    """
    Raised when a player is not found, although most functions just return None.
    """


class AlreadyConnected(PlayerException):
    """
    Raised when a bot already connected to some channel, although most functions just return None.
    """


class MissingPermissionsToEditPlayer(lightbulb.errors.CheckFailure):
    """
    Raised when a member don't have permission to edit player, although most functions just return None.
    """


class NoVoiceChannel(lightbulb.errors.CheckFailure):
    """
    Raised when a member not in the same channel and trying edit player.
    """