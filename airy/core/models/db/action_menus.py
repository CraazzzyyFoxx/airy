from enum import IntEnum

import hikari
from tortoise import fields
from tortoise.models import Model

__all__ = ("ActionType", "ActionMenusModel", "ButtonModel", "DropdownModel", "DropdownEntriesModel")


class ActionType(IntEnum):
    MEMBER_ROLE = 1
    MEMBER_PREFIX = 2


class ActionMenusModel(Model):
    """Defining a Action Menus model to store data"""

    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    message_id = fields.BigIntField()

    buttons = fields.ReverseRelation['ActionMenusButtonModel']
    dropdowns = fields.ReverseRelation['ActionMenusDropdownModel']

    class Meta:
        """Metaclass to set table name and description"""

        table = "action_menus"
        table_description = "Stores information about the action menus"


class ButtonModel(Model):
    id = fields.IntField(pk=True)
    interaction_id = fields.TextField()

    action_type = fields.IntEnumField(ActionType, default=ActionType.MEMBER_ROLE)
    payload = fields.CharField(max_length=18)

    style = fields.IntEnumField(hikari.ButtonStyle, default=hikari.ButtonStyle.SECONDARY)
    label = fields.TextField(null=True)
    emoji = fields.TextField(null=True)
    url = fields.TextField(null=True)

    menus = fields.ForeignKeyField(model_name='main.ActionMenusModel',
                                   related_name='buttons')

    class Meta:
        """Metaclass to set table name and description"""

        table = "action_menus_button"
        table_description = "Stores information about the action menus"


class DropdownModel(Model):
    id = fields.IntField(pk=True)
    interaction_id = fields.CharField(max_length=100)

    description = fields.TextField()
    row = fields.SmallIntField()

    menus = fields.ForeignKeyField(model_name='main.ActionMenusModel',
                                   related_name='dropdowns')
    entries = fields.ReverseRelation['DropdownEntriesModel']

    class Meta:
        """Metaclass to set table name and description"""

        table = "action_menus_dropdown"
        table_description = "Stores information about the action menus"


class DropdownEntriesModel(Model):
    dropdown = fields.ForeignKeyField(model_name='main.DropdownModel',
                                      related_name='entries'
                                      )
    label = fields.TextField()
    value = fields.TextField()
    emoji = fields.TextField()

    class Meta:
        """Metaclass to set table name and description"""

        table = "action_menus_dropdown_entries"
        table_description = "Stores information about the action menus"
