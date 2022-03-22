import typing as t

from tortoise import fields
from tortoise.models import Model


class ReportModel(Model):
    guild_id = fields.BigIntField()
    is_enabled = fields.BooleanField()
    channel_id = fields.BigIntField(null=True)
    extra: dict = fields.JSONField(default={'pinged_role_ids': []})

    @property
    def pinged_role_ids(self) -> t.List[int]:
        return self.extra.get('pinged_role_ids')

    @pinged_role_ids.setter
    def pinged_role_ids(self, value):
        self.pinged_role_ids = value

    @pinged_role_ids.deleter
    def pinged_role_ids(self):
        self.pinged_role_ids = self.extra['muted_members'] = []

    class Meta:
        """Metaclass to set table name and description"""

        table = "reports"
        table_description = "Stores information about the reports"
