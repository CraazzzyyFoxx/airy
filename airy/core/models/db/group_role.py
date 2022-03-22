import typing as t
from enum import IntEnum

import hikari
from tortoise import fields
from tortoise.models import Model


__all__ = ("GroupRoleModel", "EntryRoleGroupModel", "HierarchyRoles")


class HierarchyRoles(IntEnum):
    NONE = 0
    TopDown = 1
    BottomTop = 2

    @classmethod
    def try_value(cls, value):
        for name, value_ in cls._member_map_.items():
            if value_.value == int(value):
                return cls._member_map_[name]
        return value

    @classmethod
    def to_choices(cls) -> t.List[hikari.CommandChoice]:
        return [hikari.CommandChoice(name=name, value=str(value.value)) for name, value in cls._member_map_.items()]


class GroupRoleModel(Model):
    id = fields.IntField(pk=True)
    guild_id: hikari.Snowflake = fields.BigIntField()
    role_id: hikari.Snowflake = fields.BigIntField()
    hierarchy = fields.IntEnumField(HierarchyRoles, default=HierarchyRoles.NONE)

    entries: fields.ReverseRelation['EntryRoleGroupModel']

    class Meta:
        """Metaclass to set table name and description"""

        table = "role_group"
        table_description = "Stores information about the role groups"


class EntryRoleGroupModel(Model):
    id: fields.ForeignKeyRelation[GroupRoleModel] = fields.ForeignKeyField(model_name='main.GroupRoleModel',
                                                                           related_name='entries',
                                                                           to_field='id',
                                                                           source_field='id',
                                                                           pk=True)
    role_id = fields.BigIntField()

    class Meta:
        """Metaclass to set table name and description"""

        table = "role_group_entry"
        table_description = "Stores information about the role groups"
