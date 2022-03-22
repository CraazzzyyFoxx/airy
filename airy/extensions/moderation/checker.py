import hikari
import lightbulb


class CooldownByContent(lightbulb.cooldowns.CooldownManager):
    def _bucket_key(self, message):
        return (message.channel.id, message.content)


class SpamChecker:
    """This spam checker does a few things.

    1) It checks if a user has spammed more than 10 time in 12 seconds
    2) It checks if the content has been spammed 15 time in 17 seconds.
    3) It checks if new users have spammed 30 time in 35 seconds.
    4) It checks if "fast joiners" have spammed 10 time in 12 seconds.

    The second case is meant to catch alternating spam bots while the first one
    just catches regular singular spam bots.

    From experience these values aren't reached unless someone is actively spamming.
    """
    def __init__(self):
        self.by_content = CooldownByContent.from_cooldown(15, 17.0, commands.BucketType.member)
        self.by_user = commands.CooldownMapping.from_cooldown(10, 12.0, commands.BucketType.user)
        self.last_join = None
        self.new_user = commands.CooldownMapping.from_cooldown(30, 35.0, commands.BucketType.channel)

        # user_id flag mapping (for about 30 minutes)
        self.fast_joiners = cache.ExpiringCache(seconds=1800.0)
        self.hit_and_run = commands.CooldownMapping.from_cooldown(10, 12, commands.BucketType.channel)

    def is_new(self, member):
        now = discord.utils.utcnow()
        seven_days_ago = now - datetime.timedelta(days=7)
        ninety_days_ago = now - datetime.timedelta(days=90)
        return member.created_at > ninety_days_ago and member.joined_at > seven_days_ago

    def is_spamming(self, message):
        if message.guild is None:
            return False

        current = message.created_at.timestamp()

        if message.author.id in self.fast_joiners:
            bucket = self.hit_and_run.get_bucket(message)
            if bucket.update_rate_limit(current):
                return True

        if self.is_new(message.author):
            new_bucket = self.new_user.get_bucket(message)
            if new_bucket.update_rate_limit(current):
                return True

        user_bucket = self.by_user.get_bucket(message)
        if user_bucket.update_rate_limit(current):
            return True

        content_bucket = self.by_content.get_bucket(message)
        if content_bucket.update_rate_limit(current):
            return True

        return False

    def is_fast_join(self, member):
        joined = member.joined_at or discord.utils.utcnow()
        if self.last_join is None:
            self.last_join = joined
            return False
        is_fast = (joined - self.last_join).total_seconds() <= 2.0
        self.last_join = joined
        if is_fast:
            self.fast_joiners[member.id] = True
        return is_fast

## Checks

class NoMuteRole(commands.CommandError):
    def __init__(self):
        super().__init__('This server does not have a mute role set up.')

def can_mute():
    async def predicate(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        if ctx.guild is None:
            return False

        if not ctx.author.guild_permissions.manage_roles and not is_owner:
            return False

        # This will only be used within this cog.
        ctx.guild_config = config = await ctx.cog.get_guild_config(ctx.guild.id)
        role = config and config.mute_role
        if role is None:
            raise NoMuteRole()
        return ctx.author.top_role > role
    return commands.check(predicate)