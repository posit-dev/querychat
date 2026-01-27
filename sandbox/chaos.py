import os
from pathlib import Path

import chatlas
import ibis
import snowflake.connector

from shiny import session
from posit.connect.external.snowflake import PositAuthenticator

# A connection name within ~/.snowflake/connections.toml
# TODO: Set to workbench by default?
CONNECTION_NAME = "posit"

# Default Snowflake account
ACCOUNT = "duloftf-posit-software-pbc-dev"

# Database/table parameters
WAREHOUSE = "DEFAULT_WH"
DATABASE = "DEMO_CHAOS_DB"
SCHEMA = "ERP_DUMP"
TABLE_NAME = "T_DATA_LOG"

# A model name supported by Snowflake
MODEL = "claude-3-7-sonnet"


def chat_client():
    kwargs = {}

    if is_connect():
        auth = get_connect_auth()
        kwargs["authenticator"] = auth.authenticator
        kwargs["token"] = auth.token
    else:
        if not has_local_config():
            raise ValueError(
                "No Snowflake configuration found. Please set up "
                "~/.snowflake/connections.toml with the connection details."
            )
        kwargs["connection_name"] = CONNECTION_NAME

    return chatlas.ChatSnowflake(model=MODEL, account=ACCOUNT, kwargs=kwargs)


def get_connection():
    """Get a Snowflake connection based on the environment."""
    if is_connect():
        auth = get_connect_auth()
        return snowflake.connector.connect(
            account=ACCOUNT,
            warehouse=WAREHOUSE,
            database=DATABASE,
            schema=SCHEMA,
            authenticator=auth.authenticator,
            token=auth.token,
        )

    if not has_local_config():
        raise ValueError(
            "No Snowflake configuration found. Please set up "
            "~/.snowflake/connections.toml with the connection details."
        )

    return snowflake.connector.connect(
        connection_name=CONNECTION_NAME,
        warehouse=WAREHOUSE,
        database=DATABASE,
        schema=SCHEMA,
    )


def get_connect_auth():
    """Get Posit Connect Snowflake authenticator."""
    sess = session.get_current_session()
    if sess is None:
        raise RuntimeError("get_connect_auth() must be called within a Shiny session")

    # No-op for (1st run of) Express sessions
    if sess.is_stub_session():
        return None

    user_session_token = sess.http_conn.headers.get("Posit-Connect-User-Session-Token")
    return PositAuthenticator(
        local_authenticator="EXTERNALBROWSER",
        user_session_token=user_session_token,
    )


def is_connect():
    """Check if the app is running on Posit Connect."""
    return os.getenv("RSTUDIO_PRODUCT") == "CONNECT"


def has_local_config():
    home = Path(os.getenv("SNOWFLAKE_HOME", "~/.snowflake")).expanduser()
    config_path = home / "connections.toml"
    return config_path.exists()
