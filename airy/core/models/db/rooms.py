from tortoise import fields
from tortoise.models import Model


class VoiceChannelCreatorModel(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    channel_name = fields.TextField()
    user_limit = fields.SmallIntField(null=True)
    editable = fields.BooleanField()
    auto_inc = fields.BooleanField()
    sync_permissions = fields.BooleanField()
    additional_category_name = fields.TextField()

    class Meta:
        """Metaclass to set table name and description"""

        table = "voice_rooms_creators"
        table_description = "Stores information about the Voice Rooms Creators"