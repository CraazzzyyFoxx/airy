from tortoise import fields, Model


class UsedSlashCommandModel(Model):
    id: int = fields.IntField(pk=True)
    user_id: int = fields.BigIntField()
    guild_id: int = fields.BigIntField()
    channel_id: int = fields.BigIntField()
    payload: dict = fields.JSONField()
