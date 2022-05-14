import hikari
from attr import fields
from attrs import asdict, filters
from aiohttp import web

from ..services import (
    AuthService,
)

router = web.Application()

router.add_routes()

@router.post(
    "/",
    dependencies=[Depends(AuthService.requires_authorization)],
)
async def get_guilds(request: web.Request):
    return [asdict(guild, filter=filters.exclude(fields(hikari.OwnGuild).app))
            for guild in await UserService.fetch_guilds(token)]


@router.post(
    "/hasperms",
    dependencies=[Depends(AuthService.requires_authorization)],
)
async def get_guilds_hasperms(token=Depends(AuthService.requires_authorization)):
    return [asdict(guild, filter=filters.exclude(fields(hikari.OwnGuild).app))
            for guild in await UserService.fetch_guilds_with_manage_server_perm(token)]


@router.post(
    "/hasperms/mutual",
    dependencies=[Depends(AuthService.requires_authorization)],
)
async def get_guilds_hasperms_mutual(token=Depends(AuthService.requires_authorization)):
    guilds = await UserService.fetch_guilds_with_manage_server_perm(token)
    return [asdict(guild, filter=filters.exclude(fields(hikari.OwnGuild).app))
            for guild in await UserService.find_mutual_guilds(guilds)]