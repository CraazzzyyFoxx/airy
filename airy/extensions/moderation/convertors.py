import hikari
import lightbulb

from airy.core.bot.utils import BadArgument


def can_execute_action(ctx: lightbulb.Context, user: hikari.Member, target: hikari.Member):
    return user == ctx.get_guild().owner_id or \
           user.get_top_role() > target.get_top_role()


class BannedMember(lightbulb.BaseConverter):
    async def convert(self, argument):
        ban_list = await self.context.bot.rest.fetch_bans(self.context.guild_id)
        entity = lightbulb.utils.find(ban_list, lambda u: u.user == argument)

        if entity is None:
            raise BadArgument('This member has not been banned before.')
        return entity


class ActionReason(lightbulb.BaseConverter):
    async def convert(self, argument):
        ret = f'{self.context.author} (ID: {self.context.author.id}): {argument}'

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret


def safe_reason_append(base, to_append):
    appended = base + f'({to_append})'
    if len(appended) > 512:
        return base
    return appended
