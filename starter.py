import logging
import platform

from airy.core import Airy


if __name__ == "__main__":
    if int(platform.python_version_tuple()[1]) < 10:
        logging.fatal("Python version must be 3.10 or greater! Exiting...")
        raise RuntimeError("Python version is not 3.10 or greater.")

    bot = Airy()
    bot.run()
