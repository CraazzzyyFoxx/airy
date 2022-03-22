import functools
import operator

import hikari
from lightbulb import Check, checks


__all__ = ("is_mod", "is_admin", "mod_or_permissions", "admin_or_permissions")


def is_mod():
    return Check(functools.partial(checks._has_guild_permissions, perms=hikari.Permissions.MANAGE_GUILD))


def is_admin():
    return Check(functools.partial(checks._has_guild_permissions, perms=hikari.Permissions.ADMINISTRATOR))


def mod_or_permissions(*perms: hikari.Permissions):
    reduced = functools.reduce(operator.or_, [hikari.Permissions.MANAGE_GUILD, *perms])
    return Check(functools.partial(checks._has_guild_permissions, perms=reduced))


def admin_or_permissions(*perms: hikari.Permissions):
    reduced = functools.reduce(operator.or_, [hikari.Permissions.ADMINISTRATOR, *perms])
    return Check(functools.partial(checks._has_guild_permissions, perms=reduced))