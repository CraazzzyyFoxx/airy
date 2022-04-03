import typing as t

import hikari

from airy.core import Airy

if t.TYPE_CHECKING:
    from .room import VoiceCategory


class Cache:
    def __init__(self):
        self.bot: t.Optional[Airy] = None
        self._cache: t.Dict[hikari.Snowflake, t.Dict[hikari.Snowflake, VoiceCategory]] = dict()

    def init(self, bot: Airy):
        self.bot = bot

    def get_free_category(self, channel_id: hikari.Snowflake):
        categories = self._cache.get(channel_id)

        category = None

        if categories:
            for pair in categories.items():
                if len(pair[1].rooms) < 3:
                    category = pair[1]
                    break

        return category

    def get_category_position(self, channel_id: hikari.Snowflake):
        data = self._cache.get(channel_id)
        if data:
            return len(data)
        return 0

    def add_creator(self, channel_id: hikari.Snowflake):
        self._cache[channel_id] = dict()

    def add_category(self, channel_id: hikari.Snowflake, category):
        if not self._cache.get(channel_id):
            self.add_creator(channel_id)
        self._cache[channel_id][category.id] = category

    def remove_creator(self, channel_id: hikari.Snowflake):
        self._cache.pop(channel_id)

    def remove_category(self, channel_id: hikari.Snowflake, category):
        self._cache[channel_id].pop(category.id)
        if len(self._cache[channel_id]) == 0:
            self.remove_creator(channel_id)

    async def load_from_redis(self):
        pass

    async def upload_to_redis(self):
        pass
