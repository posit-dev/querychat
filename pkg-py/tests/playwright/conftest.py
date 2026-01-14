"""
Pytest configuration and fixtures for querychat example tests.

Uses:
- pytest-playwright for browser automation
- shinychat.playwright.ChatController for chat interactions

Most apps run in-process using threads, except Streamlit which uses subprocess.
All tests require OPENAI_API_KEY to be set.
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
    """Find an available port by binding to port 0 and letting the OS assign one."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
    start_fn,
    wait_url: str,
    timeout: float = 45.0,
    max_attempts: int = 3,
):
    """
    Start a server with retry logic for reliability.

    Args:
        start_fn: Function that returns (cleanup_resource, server) tuple
        wait_url: URL to poll for readiness
        timeout: Timeout for waiting for server to be ready
        max_attempts: Maximum number of startup attempts

    Returns:
        Tuple of (cleanup_resource, server) from start_fn

    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            result = start_fn()
            _wait_for_app_ready(wait_url, timeout=timeout)
            return result
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
    """Load a Shiny app from file (handles both regular and Express apps)."""
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
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
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


# ==================== 01-hello-app fixtures ====================


@pytest.fixture(scope="module")
def app_01_hello() -> Generator[str, None, None]:
    """Start the 01-hello-app.py Shiny server for testing ."""
    app_path = str(EXAMPLES_DIR / "01-hello-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_shiny_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=30.0)
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
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_shiny_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=30.0)
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
    """Start the 03-sidebar-express-app.py Shiny server for testing ."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-express-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_shiny_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=30.0)
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
    """Start the 03-sidebar-core-app.py Shiny server for testing ."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-core-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_shiny_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=30.0)
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
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_streamlit_app_subprocess(app_path, port)

    process, _ = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


# ==================== 09-streamlit-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_09_streamlit_custom() -> Generator[str, None, None]:
    """Start the 09-streamlit-custom-app.py Streamlit server for testing."""
    app_path = str(EXAMPLES_DIR / "09-streamlit-custom-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_streamlit_app_subprocess(app_path, port)

    process, _ = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


# ==================== Gradio threaded helpers ====================


def _load_gradio_app(app_path: str) -> Any:
    """Load a Gradio app from file."""
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"gradio_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

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
    """Start the 05-gradio-app.py Gradio server for testing ."""
    app_path = str(EXAMPLES_DIR / "05-gradio-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_gradio_app_threaded(app_path, port)

    _, server = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_gradio_server(server)


# ==================== 07-gradio-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_07_gradio_custom() -> Generator[str, None, None]:
    """Start the 07-gradio-custom-app.py Gradio server for testing ."""
    app_path = str(EXAMPLES_DIR / "07-gradio-custom-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_gradio_app_threaded(app_path, port)

    _, server = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_gradio_server(server)


# ==================== Dash threaded helpers ====================


def _load_dash_app(app_path: str) -> Any:
    """Load a Dash app from file."""
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"dash_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

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
    """Start the 06-dash-app.py Dash server for testing ."""
    app_path = str(EXAMPLES_DIR / "06-dash-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_dash_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_dash_server(server)


# ==================== 08-dash-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_08_dash_custom() -> Generator[str, None, None]:
    """Start the 08-dash-custom-app.py Dash server for testing ."""
    app_path = str(EXAMPLES_DIR / "08-dash-custom-app.py")
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def start():
        return _start_dash_app_threaded(app_path, port)

    _thread, server = _start_server_with_retry(start, url, timeout=45.0)
    try:
        yield url
    finally:
        _stop_dash_server(server)
