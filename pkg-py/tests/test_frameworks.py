"""Smoke tests for framework-specific QueryChat implementations."""

import os

import pytest
from querychat.data import tips


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    """Set a dummy API key for tests that don't actually call the API."""
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def sample_df():
    """Provide a sample DataFrame for testing."""
    return tips()


class TestGradioQueryChat:
    """Tests for Gradio QueryChat."""

    def test_import(self):
        """Test that the module can be imported."""
        from querychat.gradio import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        """Test that QueryChat can be instantiated."""
        from querychat.gradio import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_app_returns_blocks(self, sample_df):
        """Test that .app() returns a Gradio Blocks (or wrapper)."""
        from querychat.gradio import QueryChat

        qc = QueryChat(sample_df, "tips")
        app = qc.app()
        # The app is wrapped in GradioBlocksWrapper for CSS/JS injection
        # Check that it has the expected interface (launch method)
        assert hasattr(app, "launch")

    def test_ui_returns_state(self, sample_df):
        """Test that .ui() returns a gr.State."""
        from querychat.gradio import QueryChat

        import gradio as gr

        qc = QueryChat(sample_df, "tips")
        with gr.Blocks():
            result = qc.ui()
        assert isinstance(result, gr.State)

    def test_state_to_ui_returns_native_dataframe(self, sample_df):
        """Test that state_to_ui returns a native DataFrame, not narwhals."""
        import narwhals.stable.v1 as nw
        from querychat._gradio import state_to_ui
        from querychat._querychat_core import create_app_state
        from querychat.gradio import QueryChat

        qc = QueryChat(sample_df, "tips")

        def client_factory(update_cb, reset_cb):
            return qc.client(update_dashboard=update_cb, reset_dashboard=reset_cb)

        state = create_app_state(qc._data_source, client_factory, qc.greeting)
        result = state_to_ui(state)

        # DataFrame is the 4th element in the tuple (index 3)
        df = result[3]

        # Verify it's a native DataFrame (pandas or polars), not a narwhals DataFrame
        assert not isinstance(df, nw.DataFrame), (
            "Expected native DataFrame (pandas/polars), got narwhals DataFrame"
        )


class TestDashQueryChat:
    """Tests for Dash QueryChat."""

    def test_import(self):
        """Test that the module can be imported."""
        from querychat.dash import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        """Test that QueryChat can be instantiated."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_app_returns_dash_app(self, sample_df):
        """Test that .app() returns a Dash app."""
        from querychat.dash import QueryChat

        import dash

        qc = QueryChat(sample_df, "tips")
        app = qc.app()
        assert isinstance(app, dash.Dash)

    def test_ui_returns_div(self, sample_df):
        """Dash QueryChat.ui() returns html.Div component."""
        from querychat.dash import QueryChat

        from dash import html

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        assert isinstance(component, html.Div)

    def test_store_id_property(self, sample_df):
        """Test that store_id property is available."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc.store_id is not None
        assert isinstance(qc.store_id, str)

    def test_dash_has_init_app_method(self, sample_df):
        """Dash QueryChat has init_app method."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert hasattr(qc, "init_app")
        assert callable(qc.init_app)

    def test_dash_has_ui_method(self, sample_df):
        """Dash QueryChat has ui method that returns component."""
        from querychat.dash import QueryChat

        from dash import html

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        assert isinstance(component, html.Div)

    def test_ui_contains_expected_children(self, sample_df):
        """Test that .ui() returns component with expected structure."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        # The UI should contain child components (chat input, display areas, etc.)
        assert hasattr(component, "children")
        assert component.children is not None

    def test_custom_greeting(self, sample_df):
        """Test that custom greeting is stored correctly."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips", greeting="Welcome to tips data!")
        assert qc.greeting == "Welcome to tips data!"

    def test_custom_tools(self, sample_df):
        """Test that custom tools configuration works."""
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips", tools="query")
        assert qc.tools == ("query",)

        qc_none = QueryChat(sample_df, "tips", tools=None)
        assert qc_none.tools is None


class TestStreamlitQueryChat:
    """Tests for Streamlit QueryChat."""

    def test_import(self):
        """Test that the module can be imported."""
        from querychat.streamlit import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        """Test that QueryChat can be instantiated."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_system_prompt_generated(self, sample_df):
        """Test that system prompt is generated with table info."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        prompt = qc.system_prompt
        assert isinstance(prompt, str)
        assert "tips" in prompt
        # Should mention some column names from tips dataset
        assert "total_bill" in prompt or "tip" in prompt

    def test_custom_greeting(self, sample_df):
        """Test that custom greeting is stored correctly."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips", greeting="Hello tips explorer!")
        assert qc.greeting == "Hello tips explorer!"

    def test_custom_tools(self, sample_df):
        """Test that custom tools configuration works."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips", tools="query")
        assert qc.tools == ("query",)

        qc_none = QueryChat(sample_df, "tips", tools=None)
        assert qc_none.tools is None

    def test_client_method_exists(self, sample_df):
        """Test that client() method exists and is callable."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert hasattr(qc, "client")
        assert callable(qc.client)

    def test_data_source_accessible(self, sample_df):
        """Test that data_source property provides access to underlying data."""
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        ds = qc.data_source
        assert ds is not None
        assert ds.table_name == "tips"

    # Note: Streamlit's .app(), .sidebar(), .ui() methods require
    # a running Streamlit context and cannot be easily unit tested
    # without mocking st.session_state and other Streamlit internals.
