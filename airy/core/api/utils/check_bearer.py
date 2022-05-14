from aiohttp import web


def check_bearer(request: web.Request):
    bearer = request.headers.get("Authorization")
    if not bearer:
        return