log_config = {
    "disable_existing_loggers": True,
    "version": 1,
    "formatters": {
        "verbose": {
            "format": "%(levelname)-8s %(asctime)s [%(filename)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "brief": {
            "format": "%(levelname)-8s %(asctime)s %(name)-16s %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": """
                    asctime: %(asctime)s
                    created: %(created)f
                    filename: %(filename)s
                    funcName: %(funcName)s
                    levelname: %(levelname)s
                    levelno: %(levelno)s
                    lineno: %(lineno)d
                    message: %(message)s
                    module: %(module)s
                    msec: %(msecs)d
                    name: %(name)s
                    pathname: %(pathname)s
                    process: %(process)d
                    processName: %(processName)s
                    relativeCreated: %(relativeCreated)d
                    thread: %(thread)d
                    threadName: %(threadName)s
                    exc_info: %(exc_info)s
                """,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },

    },
    "handlers": {
        "stream": {
            "formatter": "brief",
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        "logfile": {
            "formatter": "verbose",
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/airy.log",
            "backupCount": 5,
            "maxBytes": 1 * 1024 * 1024  # 1 MiB
        },
        "json": {
            "formatter": "json",
            "level": "ERROR",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "airy": {"level": "INFO",
                 "handlers": ["stream", "json"], },
        "lavacord": {"level": "INFO",
                     "handlers": ["stream", "json"], },
        "lightbulb": {"level": "INFO",
                      "handlers": ["stream", "json"], },
        "hikari.gateway": {"level": "INFO",
                           "handlers": ["stream", "json"], },
        "hikari.ratelimits": {"level": "INFO",
                              "handlers": ["stream", "json"], },
    },
}

LOGGING_CONFIG = {
    "formatters": {
        "default": {...},
        "simple": {...},
        "json": {...},
    },
    "handlers": {
        "logfile": {...},
        "verbose_output": {...},
        "json": {...},
    },
    "loggers": {
        "tryceratops": {  # The name of the logger, this SHOULD match your module!
            "level": "INFO",  # FILTER: only INFO logs onwards from "tryceratops" logger
            "handlers": [
                "verbose_output",  # Refer the handler defined above
            ],
        },
    },
    "root": {  # All loggers (including tryceratops)
        "level": "INFO",  # FILTER: only INFO logs onwards
        "handlers": [
            "logfile",  # Refer the handler defined above
            "json"  # Refer the handler defined above
        ]
    }
}
