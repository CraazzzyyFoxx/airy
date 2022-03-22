from enum import IntEnum

from tortoise import fields
from tortoise.models import Model

from airy.utils.time import utcnow


__all__ = ("VoiceType",
           "UserGuildModel",
           "UserGuildMovesModel",
           "UserModel"
           )


class VoiceType(IntEnum):
    JOIN = 1
    LEAVE = 2
    MOVE = 3


class UserGuildModel(Model):
    guild_id = fields.BigIntField(pk=True, generated=False)
    user_id = fields.BigIntField()

    messages_send = fields.IntField(default=0)
    messages_edit = fields.IntField(default=0)
    messages_deleted = fields.IntField(default=0)

    class Meta:
        """Metaclass to set table name and description"""

        table = "guild_users"
        table_description = "Stores information about the users"


class UserModel(Model):
    id = fields.BigIntField(pk=True, generated=False)

    color = fields.IntField(default=0)
    tz = fields.TextField(default="utc")

    class Meta:
        """Metaclass to set table name and description"""

        table = "users"
        table_description = "Stores information about the users"


class UserGuildMovesModel(Model):
    guild_id = fields.BigIntField(pk=True, generated=False)
    user_id = fields.BigIntField()

    type = fields.IntEnumField(VoiceType)

    time = fields.DatetimeField(default=utcnow())

    class Meta:
        """Metaclass to set table name and description"""

        table = "user_moves"
        table_description = "Stores information about the user's moves"
