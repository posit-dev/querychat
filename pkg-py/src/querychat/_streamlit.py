"""Streamlit-specific implementation for querychat."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

import streamlit as st
import streamlit.components.v1 as components
from chatlas import ContentToolRequest, ContentToolResult

from ._querychat_module import GREETING_PROMPT
from .tools import UpdateDashboardData

if TYPE_CHECKING:
    import chatlas
    from chatlas import Chat

    from ._datasource import DataSource

# Type alias for the client factory function
ClientFactory = Callable[
    [Callable[[UpdateDashboardData], None], Callable[[], None]],
    "chatlas.Chat",
]


class AppState:
    """Typed session state for Streamlit apps using QueryChat."""

    def __init__(self, client_factory: ClientFactory):
        self.chat_history: list[dict[str, str]] = []
        self.sql: str = ""
        self.title: Optional[str] = None
        self.pending_prompt: Optional[str] = None

        # Create the client with callbacks that update this state
        def update_callback(data: UpdateDashboardData) -> None:
            self.sql = data["query"]
            self.title = data["title"]

        def reset_callback() -> None:
            self.sql = ""
            self.title = None

        self.client: chatlas.Chat = client_factory(update_callback, reset_callback)

    @staticmethod
    def get(client_factory: ClientFactory, table_name: str) -> AppState:
        """Get or initialize AppState from Streamlit session state."""
        if "_querychat_state" not in st.session_state:
            st.session_state._querychat_state = AppState(client_factory)
            st.set_page_config(
                page_title=f"querychat with {table_name}",
                layout="wide",
                initial_sidebar_state="expanded",
            )
        return st.session_state._querychat_state


def run_streamlit_app(
    data_source: DataSource,
    client_factory: ClientFactory,
    greeting: Optional[str] = None,
) -> None:
    """
    Run a Streamlit app to chat with a dataset.

    Parameters
    ----------
    data_source
        The data source to query against.
    client_factory
        A factory function that creates a chatlas Chat client with callbacks.
        Takes (update_dashboard_callback, reset_dashboard_callback) and returns a Chat.
    greeting
        Optional greeting message to display at the start.

    """
    # Get (or initialize) typed session state
    state = AppState.get(client_factory, data_source.table_name)

    # CSS and JS for suggestion handling
    st.html(SUGGGESTION_CSS)
    components.html(SUGGESTION_JS)

    with st.sidebar:
        chat_container = st.container(height="stretch")

        with chat_container:
            for message in state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"], unsafe_allow_html=True)

            if not state.chat_history:
                the_greeting = greeting
                if not the_greeting:
                    the_greeting = ""
                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        for chunk in streamlit_generator(GREETING_PROMPT, state.client):
                            the_greeting += chunk
                            placeholder.markdown(the_greeting, unsafe_allow_html=True)

                state.chat_history.append(
                    {"role": "assistant", "content": the_greeting}
                )

        # Chat input (stays at bottom of sidebar, outside the scrollable container)
        if prompt := st.chat_input(
            "Ask a question about your data...",
            key="chat_input",
        ):
            state.pending_prompt = prompt
            st.rerun()

        # Process pending prompt if any (from chat input or suggestion button)
        if state.pending_prompt:
            prompt = state.pending_prompt
            state.pending_prompt = None

            state.chat_history.append({"role": "user", "content": prompt})

            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                content = ""
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    for chunk in streamlit_generator(prompt, state.client):
                        content += chunk
                        placeholder.markdown(content, unsafe_allow_html=True)

            state.chat_history.append({"role": "assistant", "content": content})

            # Force rerun to update the data display
            st.rerun()

    # Main content area
    st.title(f"querychat with `{data_source.table_name}`")

    # SQL Query display
    st.subheader(state.title or "SQL Query")

    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.code(state.sql or f"SELECT * FROM {data_source.table_name}", language="sql")

    with col2:
        if state.sql and st.button("Reset Query", type="secondary"):
            state.sql = ""
            state.title = None
            st.rerun()

    # Data display
    st.subheader("Data view")
    df = data_source.execute_query(state.sql) if state.sql else data_source.get_data()
    st.dataframe(df, width="stretch", height=400, hide_index=True)
    st.caption(f"Data has {df.shape[0]} rows and {df.shape[1]} columns.")


def streamlit_generator(prompt: str, client: Chat):
    """Yield markdown strings for Streamlit from chatlas client stream."""
    for chunk in client.stream(prompt, content="all", echo="none"):
        if isinstance(chunk, ContentToolRequest):
            # Show request doesn't seem all that useful since result follows and will show the SQL
            yield ""
        elif isinstance(chunk, ContentToolResult):
            # Get display metadata if available
            display_info = chunk.extra.get("display") if chunk.extra else None

            if display_info and hasattr(display_info, "markdown"):
                res = "\n\n" + display_info.markdown + "\n\n"
            else:
                res = "\n\n" + str(chunk) + "\n\n"

            yield res

        elif isinstance(chunk, str):
            yield chunk


SUGGGESTION_CSS = """
<style>
    .suggestion {
        color: #0066cc;
        cursor: pointer;
        text-decoration: underline;
        font-weight: 500;
        transition: all 0.2s ease;
        display: inline;
    }

    .suggestion:hover {
        color: #0052a3;
        text-decoration: none;
        background-color: rgba(0, 102, 204, 0.1);
        padding: 2px 4px;
        border-radius: 3px;
    }

    .suggestion:active {
        transform: scale(0.98);
    }

    .querychat-update-dashboard-btn {
        display: none;
    }
</style>
"""

SUGGESTION_JS = """
<script>
    // Access parent window to attach handler to main document
    const targetDoc = window.parent.document;

    targetDoc.addEventListener('click', function(e) {
        const suggestion = e.target.closest('.suggestion');

        if (suggestion) {
            e.preventDefault();

            const suggestionText = suggestion.textContent.trim();
            const chatInput = targetDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');

            if (chatInput) {
                // Use native setter to update the value (works with React)
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.parent.HTMLTextAreaElement.prototype,
                    'value'
                ).set;
                nativeInputValueSetter.call(chatInput, suggestionText);

                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                chatInput.focus();
            }
        }
    });
</script>
"""
