import hikari
import lightbulb


async def _basic_cleanup_strategy(ctx, search):
    count = 0
    async for msg in ctx.history(limit=search, before=ctx.message):
        if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
            await msg.delete()
            count += 1
    return {'Bot': count}

