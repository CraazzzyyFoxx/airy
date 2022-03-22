import miru

from hikari.internal import enums


class EmbedSettings(enums.Flag):
    """Flags to control the cache components."""
    TITLE = 1 << 0
    DESCRIPTION = 1 << 1
    URL = 1 << 2
    TIMESTAMP = 1 << 3
    COLOR = 1 << 4
    AUTHOR = 1 << 5
    THUMBNAIL = 1 << 6
    IMAGE = 1 << 7
    FIELDS = 1 << 8

    ALL = (
            TITLE
            | DESCRIPTION
            | URL
            | TIMESTAMP
            | COLOR
            | AUTHOR
            | THUMBNAIL
            | IMAGE
            | FIELDS
    )


select_options = {EmbedSettings.TITLE: miru.SelectOption(label='Title', value='__title', description='Title of embed'),
                  EmbedSettings.DESCRIPTION: miru.SelectOption(label='Description', value='__description',
                                                               description='Title of embed'),
                  EmbedSettings.URL: miru.SelectOption(label='Url', value='__url', description='Title of embed'),
                  EmbedSettings.TIMESTAMP: miru.SelectOption(label='Timestamp', value='__timestamp',
                                                             description='Title of embed'),
                  EmbedSettings.COLOR: miru.SelectOption(label='Color', value='__color', description='Title of embed'),
                  EmbedSettings.AUTHOR: miru.SelectOption(label='Author', value='__author',
                                                          description='Title of embed')}
