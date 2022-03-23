from tortoise import fields
from tortoise.models import Model


class BlacklistModel(Model):
    """Defining a blacklist model to blacklist"""

    id: int = fields.IntField(pk=True)
    entry_id: int = fields.BigIntField()

    class Meta:
        """Metaclass to set table name and description"""

        table = "blacklist"
        table_description = "Stores information about the blacklist"
