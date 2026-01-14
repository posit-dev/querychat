"""
Pytest configuration and fixtures for querychat example tests.

Uses:
- pytest-playwright for browser automation
- shinychat.playwright.ChatController for chat interactions

Most apps run in-process using threads, except Streamlit which uses subprocess.
All tests require OPENAI_API_KEY to be set.

Test Isolation Strategy:
------------------------
Server fixtures use module scope for efficiency (avoid restarting servers for each test).
Test isolation is achieved through:
1. Playwright's default function-scoped `page` fixture (fresh browser page per test)
2. Each test's setup navigates to the app URL, triggering a fresh session
3. Apps use session-based state, so each browser session has independent state

This means the same server instance handles multiple tests, but each test gets
a clean slate from the browser/session perspective.
"""

from __future__ import annotations

import importlib.util
import logging
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

# Configure logging for test debugging
logger = logging.getLogger(__name__)

# Path constants for example apps
# Tests run from pkg-py/ but paths need to resolve correctly
REPO_ROOT = Path(__file__).parent.parent.parent.parent
EXAMPLES_DIR = REPO_ROOT / "pkg-py" / "examples"




if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import Page
    from shinychat.playwright import ChatController as ChatControllerType


# ==================== App lifecycle helpers ====================


def _find_free_port() -> int:
    """
    Find an available port by binding to port 0 and letting the OS assign one.

    Note: There is an inherent TOCTOU (time-of-check to time-of-use) race condition
    here - the port is released before the server binds to it. Another process could
    grab the port in between. This is mitigated by:
    1. Using SO_REUSEADDR to allow quick reuse of the port
    2. The _start_server_with_retry() wrapper which retries with a new port on failure
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _wait_for_app_ready(
    url: str,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
) -> None:
    """
    Poll an HTTP endpoint until it responds successfully.

    Args:
        url: The URL to poll (e.g., "http://localhost:8765")
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Raises:
        TimeoutError: If the app doesn't respond within the timeout

    """
    start_time = time.time()
    last_error: Exception | None = None

    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=poll_interval + 1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_error = e
            time.sleep(poll_interval)

    raise TimeoutError(
        f"App at {url} did not become ready within {timeout}s. "
        f"Last error: {last_error}"
    )


def _start_server_with_retry(
    start_fn_factory,
    timeout: float = 45.0,
    max_attempts: int = 3,
):
    """
    Start a server with retry logic for reliability.

    Args:
        start_fn_factory: Function that returns (url, start_fn) tuple.
            Called fresh on each attempt to get a new port.
            start_fn should return (cleanup_resource, server) tuple.
        timeout: Timeout for waiting for server to be ready
        max_attempts: Maximum number of startup attempts

    Returns:
        Tuple of (url, cleanup_resource, server)

    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            url, start_fn = start_fn_factory()
            result = start_fn()
            _wait_for_app_ready(url, timeout=timeout)
            return url, *result
        except Exception as e:
            last_error = e
            logger.warning(
                "Server startup attempt %d/%d failed: %s",
                attempt + 1,
                max_attempts,
                e,
            )
            # Small delay before retry
            time.sleep(0.5)

    raise RuntimeError(
        f"Failed to start server after {max_attempts} attempts. "
        f"Last error: {last_error}"
    )


def _create_chat_controller(page: Page, table_name: str) -> ChatControllerType:
    """Create a ChatController for a querychat chat component."""
    from shinychat.playwright import ChatController

    # Chat ID format: {module_id}-{chat_id}
    # module_id = "querychat_{table_name}" (from QueryChat)
    # chat_id = "chat" (from CHAT_ID constant in _shiny_module.py)
    return ChatController(page, f"querychat_{table_name}-chat")


# ==================== Shiny threaded helpers ====================


def _load_shiny_app(app_path: str) -> Any:
    """
    Load a Shiny app from a Python file.

    Handles both Shiny Core apps (with explicit `app = App(...)`) and Shiny Express
    apps (which use decorators and don't have an explicit app object).

    Args:
        app_path: Absolute or relative path to the Shiny app Python file.

    Returns:
        The loaded Shiny App object ready to be served.

    Note:
        Uses unique module names based on the file path to avoid Python's module
        caching, which could cause issues when loading multiple apps in the same
        test session.

    """
    from shiny.express._is_express import is_express_app
    from shiny.express._run import wrap_express_app

    path = Path(app_path).resolve()
    app_dir = str(path.parent)
    app_file = path.name

    if is_express_app(app_file, app_dir):
        # Express apps don't have an explicit `app` object
        return wrap_express_app(path)
    else:
        # Regular apps have `app = App(...)` at module level
        # Use unique module name based on path to avoid caching issues
        module_name = f"shiny_app_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module.app


def _start_shiny_app_threaded(app_path: str, port: int) -> tuple[threading.Thread, Any]:
    """Start a Shiny app in a background thread."""
    import uvicorn

    app = _load_shiny_app(app_path)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread, server


def _stop_shiny_server(server: Any) -> None:
    """Stop a uvicorn server."""
    server.should_exit = True


# ==================== App Fixtures ====================
#
# Note on fixture organization: Each app has its own fixture rather than using
# parameterization because:
# 1. Different frameworks (Shiny, Streamlit, Gradio, Dash) require different
#    server startup/shutdown logic
# 2. Test files are organized by framework, so explicit fixtures make dependencies clear
# 3. The factory pattern ensures proper port allocation on retries
#
# The fixtures follow a consistent structure:
# - Define a start_factory that gets a fresh port on each attempt
# - Use _start_server_with_retry for reliability
# - Yield the URL and clean up the server on teardown

# ==================== 01-hello-app fixtures ====================


@pytest.fixture(scope="module")
def app_01_hello() -> Generator[str, None, None]:
    """Start the 01-hello-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "01-hello-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=30.0)
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_01_hello(page: Page) -> ChatControllerType:
    """Create a ChatController for the 01-hello-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 02-prompt-app fixtures ====================


@pytest.fixture(scope="module")
def app_02_prompt() -> Generator[str, None, None]:
    """Start the 02-prompt-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "02-prompt-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=30.0)
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_02_prompt(page: Page) -> ChatControllerType:
    """Create a ChatController for the 02-prompt-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 03-sidebar-express-app fixtures ====================


@pytest.fixture(scope="module")
def app_03_express() -> Generator[str, None, None]:
    """Start the 03-sidebar-express-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-express-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=30.0)
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_03_express(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-express-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 03-sidebar-core-app fixtures ====================


@pytest.fixture(scope="module")
def app_03_core() -> Generator[str, None, None]:
    """Start the 03-sidebar-core-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-core-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=30.0)
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_03_core(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-core-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== Streamlit subprocess helpers ====================


def _start_streamlit_app_subprocess(
    app_path: str, port: int
) -> tuple[subprocess.Popen, None]:
    """
    Start a Streamlit app in a subprocess.

    Uses subprocess to run Streamlit which works reliably in CI.
    """
    import sys

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            app_path,
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process, None


def _stop_streamlit_server(process: subprocess.Popen) -> None:
    """Stop a Streamlit subprocess."""
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


# ==================== 04-streamlit-app fixtures ====================


@pytest.fixture(scope="module")
def app_04_streamlit() -> Generator[str, None, None]:
    """Start the 04-streamlit-app.py Streamlit server for testing."""
    app_path = str(EXAMPLES_DIR / "04-streamlit-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_streamlit_app_subprocess(app_path, port)

    url, process, _ = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


# ==================== 09-streamlit-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_09_streamlit_custom() -> Generator[str, None, None]:
    """Start the 09-streamlit-custom-app.py Streamlit server for testing."""
    app_path = str(EXAMPLES_DIR / "09-streamlit-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_streamlit_app_subprocess(app_path, port)

    url, process, _ = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


# ==================== Gradio threaded helpers ====================


def _load_gradio_app(app_path: str) -> Any:
    """
    Load a Gradio app from a Python file.

    Handles two common patterns for Gradio apps:
    1. Simple apps: `app = qc.app()` at module level
    2. Custom apps: `app` is a `gr.Blocks` instance directly

    Args:
        app_path: Absolute or relative path to the Gradio app Python file.

    Returns:
        The loaded Gradio Blocks object ready to be launched.

    Raises:
        ValueError: If neither `app` nor `qc` attributes are found in the module.

    Note:
        Uses unique module names to avoid Python's module caching issues.

    """
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"gradio_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    # Handle both patterns:
    # - 05-gradio-app.py: app = qc.app() at module level
    # - 07-gradio-custom-app.py: app is gr.Blocks directly
    if hasattr(module, "app"):
        return module.app
    elif hasattr(module, "qc"):
        return module.qc.app()
    else:
        raise ValueError(f"Cannot find Gradio app in {app_path}")


def _start_gradio_app_threaded(app_path: str, port: int) -> tuple[None, Any]:
    """Start a Gradio app in a thread (same process for testing)."""
    app = _load_gradio_app(app_path)
    # Gradio's launch() with prevent_thread_lock=True returns immediately
    # It returns (FastAPI App, local_url, share_url)
    # To close, we need to call close() on the Blocks object (app), not the returned value
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        prevent_thread_lock=True,
        quiet=True,
    )
    return None, app  # Return the Blocks object for cleanup


def _stop_gradio_server(app: Any) -> None:
    """Stop a Gradio server."""
    if app is not None:
        app.close()


# ==================== 05-gradio-app fixtures ====================


@pytest.fixture(scope="module")
def app_05_gradio() -> Generator[str, None, None]:
    """Start the 05-gradio-app.py Gradio server for testing."""
    app_path = str(EXAMPLES_DIR / "05-gradio-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_gradio_app_threaded(app_path, port)

    url, _, server = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_gradio_server(server)


# ==================== 07-gradio-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_07_gradio_custom() -> Generator[str, None, None]:
    """Start the 07-gradio-custom-app.py Gradio server for testing."""
    app_path = str(EXAMPLES_DIR / "07-gradio-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_gradio_app_threaded(app_path, port)

    url, _, server = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_gradio_server(server)


# ==================== Dash threaded helpers ====================


def _load_dash_app(app_path: str) -> Any:
    """
    Load a Dash app from a Python file.

    Handles two common patterns for Dash apps:
    1. Simple apps: `app = qc.app()` at module level
    2. Custom apps: `app` is a `dash.Dash` instance directly

    Args:
        app_path: Absolute or relative path to the Dash app Python file.

    Returns:
        The loaded Dash application object ready to be served.

    Raises:
        ValueError: If neither `app` nor `qc` attributes are found in the module.

    Note:
        Uses unique module names to avoid Python's module caching issues.

    """
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"dash_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    # Handle both patterns:
    # - 06-dash-app.py: app = qc.app() at module level
    # - 08-dash-custom-app.py: app is dash.Dash directly
    if hasattr(module, "app"):
        return module.app
    elif hasattr(module, "qc"):
        return module.qc.app()
    else:
        raise ValueError(f"Cannot find Dash app in {app_path}")


def _start_dash_app_threaded(app_path: str, port: int) -> tuple[threading.Thread, Any]:
    """Start a Dash app in a thread (same process for testing)."""
    from werkzeug.serving import make_server

    dash_app = _load_dash_app(app_path)
    server = make_server("127.0.0.1", port, dash_app.server, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread, server


def _stop_dash_server(server: Any) -> None:
    """Stop a werkzeug server."""
    server.shutdown()


# ==================== 06-dash-app fixtures ====================


@pytest.fixture(scope="module")
def app_06_dash() -> Generator[str, None, None]:
    """Start the 06-dash-app.py Dash server for testing."""
    app_path = str(EXAMPLES_DIR / "06-dash-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_dash_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_dash_server(server)


# ==================== 08-dash-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_08_dash_custom() -> Generator[str, None, None]:
    """Start the 08-dash-custom-app.py Dash server for testing."""
    app_path = str(EXAMPLES_DIR / "08-dash-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_dash_app_threaded(app_path, port)

    url, _thread, server = _start_server_with_retry(start_factory, timeout=45.0)
    try:
        yield url
    finally:
        _stop_dash_server(server)
