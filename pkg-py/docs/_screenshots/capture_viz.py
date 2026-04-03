"""
Standalone Playwright script that captures screenshots of querychat visualizations
from the 10-viz-app.py example for use in documentation.

Screenshots are saved to pkg-py/docs/images/.

Usage:
    cd pkg-py && uv run python docs/_screenshots/capture_viz.py
"""

from __future__ import annotations

import importlib.util
import logging
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
EXAMPLES_DIR = REPO_ROOT / "pkg-py" / "examples"
IMAGES_DIR = REPO_ROOT / "pkg-py" / "docs" / "images"
APP_PATH = str(EXAMPLES_DIR / "10-viz-app.py")

TOOL_RESULT_TIMEOUT = 90_000  # ms — generous for LLM responses

# Chat component selectors — mirrors shinychat.playwright.ChatController
# Chat ID format: querychat_{table_name}-{chat_id}
CHAT_ID = "querychat_titanic-chat"
CHAT_INPUT_SELECTOR = f"#{CHAT_ID} > .shiny-chat-input > textarea"

# Viz tool result selectors — the tool result renders as div.shiny-tool-result
# (not a custom element). The viz container inside it has .querychat-viz-container
VIZ_CONTAINER_SELECTOR = ".querychat-viz-container"
TOOL_CARD_SELECTOR = ".shiny-tool-card"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_app_ready(url: str, timeout: float = 45.0, poll_interval: float = 0.25) -> None:
    start = time.time()
    last_error: Exception | None = None
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=poll_interval + 1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_error = e
            time.sleep(poll_interval)
    raise TimeoutError(f"App at {url} did not become ready within {timeout}s. Last error: {last_error}")


def load_shiny_app(app_path: str):
    from shiny.express._is_express import is_express_app
    from shiny.express._run import wrap_express_app

    path = Path(app_path).resolve()
    app_dir = str(path.parent)
    app_file = path.name

    if is_express_app(app_file, app_dir):
        return wrap_express_app(path)
    else:
        module_name = f"shiny_app_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module.app


def start_shiny_app(app_path: str, port: int):
    import uvicorn

    app = load_shiny_app(app_path)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread, server


def send_chat_message(page, message: str) -> None:
    """Type a message into the chat input and submit it via the send button."""
    # Use .type() to simulate keystroke-by-keystroke typing (triggers input events)
    page.locator(CHAT_INPUT_SELECTOR).type(message)
    # Click the send button — Enter on a textarea inserts a newline, not a submit
    send_btn_selector = f"#{CHAT_ID} > .shiny-chat-input .shiny-chat-btn-send"
    page.locator(send_btn_selector).click()


def wait_for_viz(page) -> None:
    """Wait for a visualization tool result card to appear and be fully rendered."""
    # The tool result renders as div.shiny-tool-result containing .querychat-viz-container
    viz_container = page.locator(VIZ_CONTAINER_SELECTOR)
    viz_container.wait_for(state="visible", timeout=TOOL_RESULT_TIMEOUT)

    # Also wait for footer buttons (confirms full card has rendered)
    page.locator(".querychat-footer-buttons").wait_for(state="visible", timeout=10_000)

    # Small pause to allow any animations/transitions to settle
    page.wait_for_timeout(800)


def capture_screenshots(url: str) -> None:
    from playwright.sync_api import sync_playwright

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # ------------------------------------------------------------------ #
        # Screenshot 1: Bar chart — survival rate by class
        # ------------------------------------------------------------------ #
        logger.info("Navigating to app...")
        page.goto(url)
        page.wait_for_selector("shiny-chat-container", timeout=30_000)
        # Wait for the greeting message to appear before sending our message
        page.wait_for_selector(".shiny-chat-message", timeout=60_000)

        logger.info("Sending bar chart request...")
        send_chat_message(
            page,
            "Create a bar chart showing survival rate by passenger class",
        )
        wait_for_viz(page)

        out_path = IMAGES_DIR / "viz-bar-chart.png"
        page.locator(TOOL_CARD_SELECTOR).screenshot(path=str(out_path))
        logger.info("Saved %s", out_path)

        # ------------------------------------------------------------------ #
        # Screenshot 2: Scatter plot — age vs fare colored by survival
        # ------------------------------------------------------------------ #
        logger.info("Reloading for scatter plot...")
        page.goto(url)
        page.wait_for_selector("shiny-chat-container", timeout=30_000)
        # Wait for the greeting message to appear before sending our message
        page.wait_for_selector(".shiny-chat-message", timeout=60_000)

        logger.info("Sending scatter plot request...")
        send_chat_message(
            page,
            "Create a scatter plot of age vs fare colored by whether the passenger survived",
        )
        wait_for_viz(page)

        out_path = IMAGES_DIR / "viz-scatter.png"
        page.locator(TOOL_CARD_SELECTOR).screenshot(path=str(out_path))
        logger.info("Saved %s", out_path)

        # ------------------------------------------------------------------ #
        # Screenshot 3: Same scatter with "Show Query" footer expanded
        # ------------------------------------------------------------------ #
        logger.info("Clicking 'Show Query' button...")
        show_query_btn = page.locator(".querychat-show-query-btn")
        show_query_btn.wait_for(state="visible", timeout=10_000)
        show_query_btn.click()

        # Wait for the query section to become visible (CSS transition)
        page.locator(".querychat-query-section--visible").wait_for(
            state="visible", timeout=5_000
        )
        page.wait_for_timeout(400)  # let CSS transition finish

        out_path = IMAGES_DIR / "viz-show-query.png"
        page.locator(TOOL_CARD_SELECTOR).screenshot(path=str(out_path))
        logger.info("Saved %s", out_path)

        # ------------------------------------------------------------------ #
        # Screenshot 4: Chart in fullscreen mode
        # ------------------------------------------------------------------ #
        logger.info("Entering fullscreen mode...")
        # Close the Show Query section first to keep screenshot clean
        show_query_btn.click()
        page.wait_for_timeout(300)

        fs_button = page.locator(".tool-fullscreen-toggle")
        fs_button.wait_for(state="visible", timeout=5_000)
        fs_button.click()

        # Wait for fullscreen mode — the card gets a `fullscreen` attribute
        page.wait_for_function(
            "document.querySelector('.shiny-tool-card[fullscreen]') !== null",
            timeout=5_000,
        )
        page.wait_for_timeout(400)  # let any transition finish

        out_path = IMAGES_DIR / "viz-fullscreen.png"
        page.screenshot(path=str(out_path))
        logger.info("Saved %s", out_path)

        # Exit fullscreen cleanly
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        browser.close()

    logger.info("All screenshots saved to %s", IMAGES_DIR)


def main() -> None:
    port = find_free_port()
    url = f"http://localhost:{port}"

    logger.info("Starting Shiny app on %s ...", url)
    _thread, server = start_shiny_app(APP_PATH, port)

    try:
        wait_for_app_ready(url, timeout=45.0)
        logger.info("App is ready.")
        capture_screenshots(url)
    finally:
        logger.info("Shutting down server...")
        server.should_exit = True


if __name__ == "__main__":
    main()
