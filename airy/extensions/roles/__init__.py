from airy.core import Airy

from .group import group_role_plugin
from .buttons import role_buttons


def load(bot: Airy):
    bot.add_plugin(group_role_plugin)
    bot.add_plugin(role_buttons)
    group_role_plugin.init()


def unload(bot: Airy):
    bot.remove_plugin(group_role_plugin)
    bot.remove_plugin(role_buttons)
