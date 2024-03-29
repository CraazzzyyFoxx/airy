def setup_routes(app, handler, project_root):
    router = app.router
    h = handler
    router
    router.add_get('/', h.index, name='index')
    router.add_get('/{short_id}', h.redirect, name='short')
    router.add_post('/shortify', h.shortify, name='shortify')
    router.add_static(
        '/static/', path=str(project_root / 'static'),
        name='static')