"""Pytest fixtures for querychat Playwright E2E tests."""

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
        f"App at {url} did not become ready within {timeout}s. Last error: {last_error}"
    )


def _start_server_with_retry(
    start_fn_factory,
    cleanup_fn,
    timeout: float = 45.0,
    max_attempts: int = 3,
):
    """
    Start a server with retry logic for reliability.

    Args:
        start_fn_factory: Function that returns (url, start_fn) tuple.
            Called fresh on each attempt to get a new port.
            start_fn should return (cleanup_resource, server) tuple.
        cleanup_fn: Function that takes (cleanup_resource, server) and cleans up
            resources on failure. Called when server startup fails to prevent leaks.
        timeout: Timeout for waiting for server to be ready
        max_attempts: Maximum number of startup attempts

    Returns:
        Tuple of (url, cleanup_resource, server)

    """
    last_error = None
    for attempt in range(max_attempts):
        result = None
        try:
            url, start_fn = start_fn_factory()
            result = start_fn()
            _wait_for_app_ready(url, timeout=timeout)
            return url, *result
        except Exception as e:
            last_error = e
            # Clean up resources from failed attempt to prevent leaks
            if result is not None:
                try:
                    cleanup_fn(*result)
                except Exception as cleanup_error:
                    logger.warning(
                        "Cleanup after failed attempt %d raised: %s",
                        attempt + 1,
                        cleanup_error,
                    )
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


@pytest.fixture(scope="module")
def app_01_hello() -> Generator[str, None, None]:
    """Start the 01-hello-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "01-hello-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_01_hello(page: Page) -> ChatControllerType:
    """Create a ChatController for the 01-hello-app chat component."""
    return _create_chat_controller(page, "titanic")


@pytest.fixture(scope="module")
def app_02_prompt() -> Generator[str, None, None]:
    """Start the 02-prompt-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "02-prompt-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_02_prompt(page: Page) -> ChatControllerType:
    """Create a ChatController for the 02-prompt-app chat component."""
    return _create_chat_controller(page, "titanic")


@pytest.fixture(scope="module")
def app_03_express() -> Generator[str, None, None]:
    """Start the 03-sidebar-express-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-express-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_03_express(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-express-app chat component."""
    return _create_chat_controller(page, "titanic")


@pytest.fixture(scope="module")
def app_03_core() -> Generator[str, None, None]:
    """Start the 03-sidebar-core-app.py Shiny server for testing."""
    app_path = str(EXAMPLES_DIR / "03-sidebar-core-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_shiny_app_threaded(app_path, port)

    def shiny_cleanup(_thread, server):
        _stop_shiny_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, shiny_cleanup, timeout=30.0
    )
    try:
        yield url
    finally:
        _stop_shiny_server(server)


@pytest.fixture
def chat_03_core(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-core-app chat component."""
    return _create_chat_controller(page, "titanic")


def _start_streamlit_app_subprocess(
    app_path: str, port: int
) -> tuple[subprocess.Popen, None]:
    """
    Start a Streamlit app in a subprocess.

    Uses subprocess to run Streamlit which works reliably in CI.
    Output is redirected to DEVNULL to avoid pipe buffer deadlocks.
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


@pytest.fixture(scope="module")
def app_04_streamlit() -> Generator[str, None, None]:
    """Start the 04-streamlit-app.py Streamlit server for testing."""
    app_path = str(EXAMPLES_DIR / "04-streamlit-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_streamlit_app_subprocess(app_path, port)

    def streamlit_cleanup(process, _):
        _stop_streamlit_server(process)

    url, process, _ = _start_server_with_retry(
        start_factory, streamlit_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


@pytest.fixture(scope="module")
def app_09_streamlit_custom() -> Generator[str, None, None]:
    """Start the 09-streamlit-custom-app.py Streamlit server for testing."""
    app_path = str(EXAMPLES_DIR / "09-streamlit-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_streamlit_app_subprocess(app_path, port)

    def streamlit_cleanup(process, _):
        _stop_streamlit_server(process)

    url, process, _ = _start_server_with_retry(
        start_factory, streamlit_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_streamlit_server(process)


def _load_gradio_app(app_path: str) -> Any:
    """
    Load a Gradio app from a Python file.

    The module must define an `app` variable containing the Gradio Blocks object.
    This can be created via `app = qc.app()` or `with gr.Blocks() as app:`.

    Args:
        app_path: Absolute or relative path to the Gradio app Python file.

    Returns:
        The loaded Gradio Blocks object ready to be launched.

    Raises:
        ValueError: If no `app` attribute is found in the module.

    """
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"gradio_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    if hasattr(module, "app"):
        return module.app

    raise ValueError(
        f"Cannot find Gradio app in {app_path}. "
        "The module must define an `app` variable containing the Gradio Blocks object."
    )


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


@pytest.fixture(scope="module")
def app_05_gradio() -> Generator[str, None, None]:
    """Start the 05-gradio-app.py Gradio server for testing."""
    app_path = str(EXAMPLES_DIR / "05-gradio-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_gradio_app_threaded(app_path, port)

    def gradio_cleanup(_, server):
        _stop_gradio_server(server)

    url, _, server = _start_server_with_retry(
        start_factory, gradio_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_gradio_server(server)


@pytest.fixture(scope="module")
def app_07_gradio_custom() -> Generator[str, None, None]:
    """Start the 07-gradio-custom-app.py Gradio server for testing."""
    app_path = str(EXAMPLES_DIR / "07-gradio-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_gradio_app_threaded(app_path, port)

    def gradio_cleanup(_, server):
        _stop_gradio_server(server)

    url, _, server = _start_server_with_retry(
        start_factory, gradio_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_gradio_server(server)


def _load_dash_app(app_path: str) -> Any:
    """
    Load a Dash app from a Python file.

    The module must define an `app` variable containing the Dash application.
    This can be created via `app = qc.app()` or `app = dash.Dash(...)`.

    Args:
        app_path: Absolute or relative path to the Dash app Python file.

    Returns:
        The loaded Dash application object ready to be served.

    Raises:
        ValueError: If no `app` attribute is found in the module.

    """
    path = Path(app_path).resolve()
    # Use unique module name based on path to avoid caching issues
    module_name = f"dash_app_{path.stem}_{id(path)}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    if hasattr(module, "app"):
        return module.app

    raise ValueError(
        f"Cannot find Dash app in {app_path}. "
        "The module must define an `app` variable containing the Dash application."
    )


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


@pytest.fixture(scope="module")
def app_06_dash() -> Generator[str, None, None]:
    """Start the 06-dash-app.py Dash server for testing."""
    app_path = str(EXAMPLES_DIR / "06-dash-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_dash_app_threaded(app_path, port)

    def dash_cleanup(_thread, server):
        _stop_dash_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, dash_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_dash_server(server)


@pytest.fixture(scope="module")
def app_08_dash_custom() -> Generator[str, None, None]:
    """Start the 08-dash-custom-app.py Dash server for testing."""
    app_path = str(EXAMPLES_DIR / "08-dash-custom-app.py")

    def start_factory():
        port = _find_free_port()
        url = f"http://localhost:{port}"
        return url, lambda: _start_dash_app_threaded(app_path, port)

    def dash_cleanup(_thread, server):
        _stop_dash_server(server)

    url, _thread, server = _start_server_with_retry(
        start_factory, dash_cleanup, timeout=45.0
    )
    try:
        yield url
    finally:
        _stop_dash_server(server)
