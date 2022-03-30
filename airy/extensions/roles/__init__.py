from airy.core import Airy

from .group import group_role_plugin


def load(bot: Airy):
    bot.add_plugin(group_role_plugin)
    group_role_plugin.init()


def unload(bot: Airy):
    bot.remove_plugin(group_role_plugin)