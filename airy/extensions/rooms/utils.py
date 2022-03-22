import typing as t

import hikari

from airy.core.models import VoiceChannelCreatorModel

if t.TYPE_CHECKING:
    from .room import VoiceRoom


class Permissions:
    def __init__(self,
                 config: VoiceChannelCreatorModel):
        self.config = config

    @property
    def base(self):
        return hikari.Permissions.MANAGE_CHANNELS if self.config.editable else hikari.Permissions.NONE


class PermissionsCategory(Permissions):
    def get(self):
        if self.config.sync_permissions:
            return self.voice.invoked_channel.permission_overwrites.values()
        return hikari.UNDEFINED