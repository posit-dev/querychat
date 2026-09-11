"""Tests for QueryChat's .page() method (shinychat.page_chat() wrapper)."""

from __future__ import annotations

import os
import re

import pytest


@pytest.fixture(autouse=True)
def set_dummy_api_key():
    old = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    yield
    if old is not None:
        os.environ["OPENAI_API_KEY"] = old
    else:
        del os.environ["OPENAI_API_KEY"]


def chat_container(html: str) -> str:
    m = re.search(r"<shiny-chat-container\b[^>]*>", html)
    assert m, "no <shiny-chat-container> found in rendered page"
    return m.group(0)


class TestCorePage:
    def test_page_renders_namespaced_chat(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        html = str(qc.page("Test App"))

        # The chat root ID must match what .server() (i.e., mod_server) expects
        tag = chat_container(html)
        assert 'id="querychat_users-chat"' in tag
        # querychat's CSS/JS relies on the `querychat` class on the chat root
        assert "querychat" in tag
        # The page shell derives its IDs from the chat ID
        assert 'id="querychat_users-chat_page"' in html

    def test_page_custom_id(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        html = str(qc.page("Test App", id="custom"))
        assert 'id="custom-chat"' in chat_container(html)

    def test_page_merges_user_class(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        tag = chat_container(str(qc.page("Test App", class_="extra")))
        assert "querychat" in tag
        assert "extra" in tag

    def test_page_defers_cancel_and_attachment_defaults_to_shinychat(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        tag = chat_container(str(qc.page("Test App")))
        # The attributes are omitted so shinychat's `client=`-based
        # auto-enable (update_cancel/update_upload at session start) applies.
        # mod_server() always constructs its Chat with a client.
        assert "enable-cancel" not in tag
        assert "allow-attachments" not in tag

    def test_page_rejects_page_owned_args(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        with pytest.raises(TypeError, match="owns"):
            qc.page("Test App", height="100px")

    def test_page_renders_as_app_ui(self):
        from querychat import QueryChat

        from shiny import App

        qc = QueryChat(None, "users")

        def server(input, output, session):
            pass

        app = App(qc.page("Test App"), server)
        rendered = app.ui
        html = rendered["html"] if isinstance(rendered, dict) else str(rendered)
        assert "<html" in html
        # querychat's dependencies make it into the final document
        assert "querychat.js" in html
        assert "styles.css" in html

    def test_page_includes_handoff_panel(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        # mod_server() always wires handoff_server(), so the panel must exist
        assert 'id="querychat_users-handoff_download"' in str(qc.page("Test App"))

    def test_page_injects_extras_via_footer(self):
        from querychat import QueryChat

        qc = QueryChat(None, "users")
        html = str(qc.page("Test App"))
        assert "shiny-chat-footer" in html
        assert "querychat-extras" in html

    def test_page_merges_user_footer(self):
        from querychat import QueryChat

        from shiny import ui

        qc = QueryChat(None, "users")
        html = str(qc.page("Test App", footer=ui.div(id="my-footer")))
        assert 'id="my-footer"' in html
        assert "querychat-extras" in html


class TestExpressPage:
    def run_app(self, tmp_path, app_source: str) -> str:
        from shiny.express._run import run_express
        from shiny.express._stub_session import ExpressStubSession
        from shiny.session import session_context

        app_file = tmp_path / "app.py"
        app_file.write_text(app_source)
        with session_context(ExpressStubSession()):
            return str(run_express(app_file))

    def test_express_page_renders_namespaced_chat(self, tmp_path):
        html = self.run_app(
            tmp_path,
            (
                "from querychat.express import QueryChat\n"
                "qc = QueryChat(None, 'users')\n"
                'qc.page("Test App")\n'
            ),
        )

        tag = chat_container(html)
        assert 'id="querychat_users-chat"' in tag
        assert "querychat" in tag
        assert 'id="querychat_users-chat_page"' in html

    def test_express_page_merges_user_footer(self, tmp_path):
        html = self.run_app(
            tmp_path,
            (
                "from querychat.express import QueryChat\n"
                "from shiny import ui\n"
                "qc = QueryChat(None, 'users')\n"
                'qc.page("Test App", footer=ui.div(id="my-footer"))\n'
            ),
        )
        assert 'id="my-footer"' in html
        # querychat's dependencies are still injected alongside the user footer
        assert "querychat" in html

    def test_express_page_includes_handoff_panel(self, tmp_path):
        html = self.run_app(
            tmp_path,
            (
                "from querychat.express import QueryChat\n"
                "qc = QueryChat(None, 'users')\n"
                'qc.page("Test App")\n'
            ),
        )
        # The panel is injected via page_chat(footer=) with the other extras
        assert 'id="querychat_users-handoff_download"' in html
