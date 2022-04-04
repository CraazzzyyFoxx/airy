## Airy

Multipurpose bot that runs on Discord.

## Running

Nevertheless, the installation steps are as follows:

1. **Make sure to get Python 3.10 or higher**

This is required to actually run the bot.

2. **Set up venv**

Just do `python3.10 -m venv venv`

3. **Install dependencies**

This is `pip install -U -r requirements.txt`

4. **Create the database in PostgreSQL**

You will need PostgreSQL 9.5 or higher and type the following
in the `psql` tool:

```postgresql
CREATE ROLE airy WITH LOGIN PASSWORD 'your_password';
CREATE DATABASE airy OWNER airy;
```

5. **Setup configuration**

The next step is just to create a `.env` file in the root directory where
the bot is with the following template:

```env
BOT_TOKEN = <bot_token_here>
BOT_DEV_GUILDS = []
BOT_ERRORS_TRACE_CHANNEL = <channel_id>
BOT_INFO_CHANNEL = <channel_id>
BOT_STATS_CHANNEL = <channel_id>

POSTGRES_DB = <bot_database>
POSTGRES_HOST = <database_host>
POSTGRES_PASSWORD = <database_password>
POSTGRES_PORT = <database_port>
POSTGRES_USER = <database_user>
INITIALIZE_DB = <true | false>
MIGRATE_DB = <true | false>

LAVALINK_URL=<url_here>
LAVALINK_PASSWORD = <lavalink_password>

SPOTIFY_CLIENT_ID = <spotify_client_id>
SPOTIFY_CLIENT_SECRET = <spotify_client_secret>
```
