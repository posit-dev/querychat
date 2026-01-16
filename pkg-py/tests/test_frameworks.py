"""Smoke tests for framework-specific QueryChat implementations."""

import os

import pytest
from querychat.data import tips


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old_api_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy-api-key-for-testing"
    yield
    if old_api_key is not None:
        os.environ["OPENAI_API_KEY"] = old_api_key
    else:
        del os.environ["OPENAI_API_KEY"]


@pytest.fixture
def sample_df():
    return tips()


class TestGradioQueryChat:
    @pytest.fixture(autouse=True)
    def _skip_if_no_gradio(self):
        pytest.importorskip("gradio")

    def test_import(self):
        from querychat.gradio import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        from querychat.gradio import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_app_returns_blocks(self, sample_df):
        from querychat.gradio import QueryChat

        qc = QueryChat(sample_df, "tips")
        app = qc.app()
        assert hasattr(app, "launch")

    def test_ui_returns_state(self, sample_df):
        from querychat.gradio import QueryChat

        import gradio as gr

        qc = QueryChat(sample_df, "tips")
        with gr.Blocks():
            result = qc.ui()
        assert isinstance(result, gr.State)


class TestDashQueryChat:
    @pytest.fixture(autouse=True)
    def _skip_if_no_dash(self):
        pytest.importorskip("dash")

    def test_import(self):
        from querychat.dash import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_app_returns_dash_app(self, sample_df):
        from querychat.dash import QueryChat

        import dash

        qc = QueryChat(sample_df, "tips")
        app = qc.app()
        assert isinstance(app, dash.Dash)

    def test_ui_returns_div(self, sample_df):
        from querychat.dash import QueryChat

        from dash import html

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        assert isinstance(component, html.Div)

    def test_store_id_property(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc.store_id is not None
        assert isinstance(qc.store_id, str)

    def test_dash_has_init_app_method(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert hasattr(qc, "init_app")
        assert callable(qc.init_app)

    def test_dash_has_ui_method(self, sample_df):
        from querychat.dash import QueryChat

        from dash import html

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        assert isinstance(component, html.Div)

    def test_ui_contains_expected_children(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips")
        component = qc.ui()
        assert hasattr(component, "children")
        assert component.children is not None

    def test_custom_greeting(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips", greeting="Welcome to tips data!")
        assert qc.greeting == "Welcome to tips data!"

    def test_custom_tools(self, sample_df):
        from querychat.dash import QueryChat

        qc = QueryChat(sample_df, "tips", tools="query")
        assert qc.tools == ("query",)

        qc_none = QueryChat(sample_df, "tips", tools=None)
        assert qc_none.tools is None


class TestStreamlitQueryChat:
    @pytest.fixture(autouse=True)
    def _skip_if_no_streamlit(self):
        pytest.importorskip("streamlit")

    def test_import(self):
        from querychat.streamlit import QueryChat

        assert QueryChat is not None

    def test_instantiation(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert qc is not None
        assert qc.data_source is not None

    def test_system_prompt_generated(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        prompt = qc.system_prompt
        assert isinstance(prompt, str)
        assert "tips" in prompt
        assert "total_bill" in prompt or "tip" in prompt

    def test_custom_greeting(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips", greeting="Hello tips explorer!")
        assert qc.greeting == "Hello tips explorer!"

    def test_custom_tools(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips", tools="query")
        assert qc.tools == ("query",)

        qc_none = QueryChat(sample_df, "tips", tools=None)
        assert qc_none.tools is None

    def test_client_method_exists(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        assert hasattr(qc, "client")
        assert callable(qc.client)

    def test_data_source_accessible(self, sample_df):
        from querychat.streamlit import QueryChat

        qc = QueryChat(sample_df, "tips")
        ds = qc.data_source
        assert ds is not None
        assert ds.table_name == "tips"
