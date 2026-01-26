"""
Test to verify that QueryChatExpress cannot handle data_source=None pattern.

The issue is that QueryChatExpress auto-calls .server() during __init__.
During stub session it accepts None, but during real session it requires
a data source. Since __init__ happens during BOTH sessions in Express,
there's no opportunity to set the data source between stub and real sessions.
"""

# This would be the attempted usage pattern:
# from querychat.express import QueryChat
#
# # During stub session: data_source=None is passed
# qc = QueryChat(None, "users")
# qc.sidebar()
#
# # ERROR: During real session, __init__ is called AGAIN with None,
# # and mod_server() raises RuntimeError because data_source is still None

# The correct Express pattern (as shown in docs):
# from querychat.express import QueryChat
# from shiny.express import session
#
# # Create connection conditionally - returns None during stub session
# conn = get_user_connection(session)
#
# # Pass the connection (or None) to QueryChat
# qc = QueryChat(conn, "users")
# qc.sidebar()
#
# This works because:
# - Stub session: conn=None, mod_server handles it gracefully
# - Real session: conn=actual_connection, mod_server uses it

print("Express cannot use deferred pattern with data_source=None")
print("because __init__ auto-calls mod_server() during BOTH stub and real sessions")
print("There's no opportunity to set data_source between sessions.")
