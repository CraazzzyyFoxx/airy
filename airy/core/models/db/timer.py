from tortoise import fields
from tortoise.models import Model

from airy.utils.time import utcnow


class TimerModel(Model):
    id = fields.IntField(pk=True)
    expires = fields.DatetimeField(index=True)
    created = fields.DatetimeField(default=utcnow())
    event = fields.TextField()
    extra = fields.JSONField(default={})

    class Meta:
        """Metaclass to set table name and description"""

        table = "timer"
        table_description = "Stores information about the timer"
