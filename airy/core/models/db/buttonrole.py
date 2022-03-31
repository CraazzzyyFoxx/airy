from __future__ import annotations

import hikari
import miru

from tortoise import fields
from tortoise.models import Model


__all__ = ("ButtonRoleModel",)


class ButtonRoleModel(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    message_id = fields.BigIntField()

    role_id = fields.BigIntField()
    style = fields.IntEnumField(hikari.ButtonStyle, default=hikari.ButtonStyle.SECONDARY)
    label = fields.TextField(null=True)
    emoji = fields.TextField(null=True)

    class Meta:
        """Metaclass to set table name and description"""

        table = "button_role"
        table_description = "Stores information about the button role"

    async def update(self, rest: hikari.api.RESTClient) -> None:
        """Update the rolebutton with the current state of this object.

        Parameters
        ----------
        rest : hikari.api.RESTClient
            The rest client to use for API calls.

        Raises
        ------
        hikari.ForbiddenError
            Failed to edit or fetch the message the button belongs to.
        """
        button = miru.Button(
            custom_id=f"RB:{self.id}:{self.role_id}",
            emoji=self.emoji,
            label=self.label,
            style=self.style,
        )

        message = await rest.fetch_message(self.channel_id, self.message_id)

        view = miru.View.from_message(message, timeout=None)
        view.add_item(button)
        await message.edit(components=view.build())
        await self.save()

    async def delete(self, rest: hikari.api.RESTClient) -> None:
        """Delete this rolebutton, removing it from the message and the database.

        Parameters
        ----------
        rest : hikari.api.RESTClient
            The rest client to use for API calls.

        Raises
        ------
        hikari.ForbiddenError
            Failed to edit or fetch the message the button belongs to.
        """

        try:
            message = await rest.fetch_message(self.channel_id, self.message_id)
        except hikari.NotFoundError:
            pass
        else:  # Remove button if message still exists
            view = miru.View.from_message(message, timeout=None)

            for item in view.children:
                if item.custom_id == f"RB:{self.id}:{self.role_id}":
                    view.remove_item(item)
            await message.edit(components=view.build())

        await super().delete()
