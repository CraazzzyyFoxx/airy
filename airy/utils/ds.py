from __future__ import annotations

import lightbulb


def pass_options(name: str):
    """
    First order decorator that causes the decorated command callback function
    to have all options provided by the context passed as **keyword** arguments
    on invocation. This allows you to access the options directly instead of through the
    context object.
    This decorator **must** be below all other command decorators.
    Example:
        .. code-block:: python
            @lightbulb.option("text", "Text to repeat")
            @filament.utils.prefix_command("echo", "Repeats the given text")
            @filament.utils.pass_options
            async def echo(ctx, text):
                await ctx.respond(text)
    """
    def decorator(func):
        async def decorated(ctx: lightbulb.context.Context) -> None:
            raw_options = ctx.raw_options.copy()
            raw_options.pop(name)
            await func(ctx, **raw_options)

        return decorated

    return decorator
