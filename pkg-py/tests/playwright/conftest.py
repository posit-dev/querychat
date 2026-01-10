"""
Pytest configuration and fixtures for querychat example tests.

Uses:
- pytest-playwright for browser automation
- pytest-recording (VCR.py) for recording/replaying LLM API responses
- shinychat.playwright.ChatController for chat interactions
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

import pytest

# Configure logging for test debugging
logger = logging.getLogger(__name__)

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
    poll_interval: float = 0.5,
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
            with urllib.request.urlopen(url, timeout=poll_interval) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_error = e
            time.sleep(poll_interval)

    raise TimeoutError(
        f"App at {url} did not become ready within {timeout}s. "
        f"Last error: {last_error}"
    )


def _terminate_process(proc: subprocess.Popen, app_name: str = "app") -> None:
    """Safely terminate a subprocess and log any captured output."""
    # Capture any remaining output before terminating
    stdout_data = b""
    stderr_data = b""

    if proc.poll() is None:  # Process is still running
        proc.terminate()
        try:
            stdout_data, stderr_data = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_data, stderr_data = proc.communicate()
    else:
        # Process already exited - capture any buffered output
        if proc.stdout:
            stdout_data = proc.stdout.read()
        if proc.stderr:
            stderr_data = proc.stderr.read()

    # Log output for debugging if there's anything interesting
    if stderr_data:
        logger.debug(
            "[%s] stderr:\n%s", app_name, stderr_data.decode("utf-8", errors="replace")
        )
    if stdout_data and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "[%s] stdout:\n%s", app_name, stdout_data.decode("utf-8", errors="replace")
        )


def _start_shiny_app(app_path: str, port: int) -> subprocess.Popen:
    """Start a Shiny app server."""
    return subprocess.Popen(
        ["uv", "run", "shiny", "run", app_path, "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _create_chat_controller(page: Page, table_name: str) -> ChatControllerType:
    """Create a ChatController for a querychat chat component."""
    from shinychat.playwright import ChatController

    # Chat ID format: {module_id}-{chat_id}
    # module_id = "querychat_{table_name}" (from QueryChat)
    # chat_id = "chat" (from CHAT_ID constant in _shiny_module.py)
    return ChatController(page, f"querychat_{table_name}-chat")


# ==================== 01-hello-app fixtures ====================


@pytest.fixture(scope="module")
def app_01_hello() -> Generator[str, None, None]:
    """Start the 01-hello-app.py Shiny server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_shiny_app("pkg-py/examples/01-hello-app.py", port)
    try:
        _wait_for_app_ready(url)
        yield url
    finally:
        _terminate_process(proc, "01-hello-app")


@pytest.fixture
def chat_01_hello(page: Page) -> ChatControllerType:
    """Create a ChatController for the 01-hello-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 02-prompt-app fixtures ====================


@pytest.fixture(scope="module")
def app_02_prompt() -> Generator[str, None, None]:
    """Start the 02-prompt-app.py Shiny server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_shiny_app("pkg-py/examples/02-prompt-app.py", port)
    try:
        _wait_for_app_ready(url)
        yield url
    finally:
        _terminate_process(proc, "02-prompt-app")


@pytest.fixture
def chat_02_prompt(page: Page) -> ChatControllerType:
    """Create a ChatController for the 02-prompt-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 03-sidebar-express-app fixtures ====================


@pytest.fixture(scope="module")
def app_03_express() -> Generator[str, None, None]:
    """Start the 03-sidebar-express-app.py Shiny server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_shiny_app("pkg-py/examples/03-sidebar-express-app.py", port)
    try:
        _wait_for_app_ready(url)
        yield url
    finally:
        _terminate_process(proc, "03-sidebar-express-app")


@pytest.fixture
def chat_03_express(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-express-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== 03-sidebar-core-app fixtures ====================


@pytest.fixture(scope="module")
def app_03_core() -> Generator[str, None, None]:
    """Start the 03-sidebar-core-app.py Shiny server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_shiny_app("pkg-py/examples/03-sidebar-core-app.py", port)
    try:
        _wait_for_app_ready(url)
        yield url
    finally:
        _terminate_process(proc, "03-sidebar-core-app")


@pytest.fixture
def chat_03_core(page: Page) -> ChatControllerType:
    """Create a ChatController for the 03-sidebar-core-app chat component."""
    return _create_chat_controller(page, "titanic")


# ==================== Streamlit helpers ====================


def _start_streamlit_app(app_path: str, port: int) -> subprocess.Popen:
    """Start a Streamlit app server."""
    return subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            app_path,
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# ==================== 04-streamlit-app fixtures ====================


@pytest.fixture(scope="module")
def app_04_streamlit() -> Generator[str, None, None]:
    """Start the 04-streamlit-app.py Streamlit server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_streamlit_app("pkg-py/examples/04-streamlit-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Streamlit takes longer to start
        yield url
    finally:
        _terminate_process(proc, "04-streamlit-app")


# ==================== 09-streamlit-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_09_streamlit_custom() -> Generator[str, None, None]:
    """Start the 09-streamlit-custom-app.py Streamlit server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_streamlit_app("pkg-py/examples/09-streamlit-custom-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Streamlit takes longer to start
        yield url
    finally:
        _terminate_process(proc, "09-streamlit-custom-app")


# ==================== Gradio helpers ====================


def _start_gradio_app(app_path: str, port: int) -> subprocess.Popen:
    """Start a Gradio app server."""
    env = os.environ.copy()
    env["GRADIO_SERVER_PORT"] = str(port)
    return subprocess.Popen(
        ["uv", "run", "python", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


# ==================== 05-gradio-app fixtures ====================


@pytest.fixture(scope="module")
def app_05_gradio() -> Generator[str, None, None]:
    """Start the 05-gradio-app.py Gradio server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_gradio_app("pkg-py/examples/05-gradio-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Gradio takes time to start
        yield url
    finally:
        _terminate_process(proc, "05-gradio-app")


# ==================== 07-gradio-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_07_gradio_custom() -> Generator[str, None, None]:
    """Start the 07-gradio-custom-app.py Gradio server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_gradio_app("pkg-py/examples/07-gradio-custom-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Gradio takes time to start
        yield url
    finally:
        _terminate_process(proc, "07-gradio-custom-app")


# ==================== Dash helpers ====================


def _start_dash_app(app_path: str, port: int) -> subprocess.Popen:
    """
    Start a Dash app server.

    The Dash example apps read DASH_PORT and DASH_DEBUG from environment variables.
    """
    env = os.environ.copy()
    env["DASH_PORT"] = str(port)
    env["DASH_DEBUG"] = "false"  # Disable debug mode for tests
    return subprocess.Popen(
        ["uv", "run", "python", app_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


# ==================== 06-dash-app fixtures ====================


@pytest.fixture(scope="module")
def app_06_dash() -> Generator[str, None, None]:
    """Start the 06-dash-app.py Dash server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_dash_app("pkg-py/examples/06-dash-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Dash takes time to start
        yield url
    finally:
        _terminate_process(proc, "06-dash-app")


# ==================== 08-dash-custom-app fixtures ====================


@pytest.fixture(scope="module")
def app_08_dash_custom() -> Generator[str, None, None]:
    """Start the 08-dash-custom-app.py Dash server for testing."""
    port = _find_free_port()
    url = f"http://localhost:{port}"
    proc = _start_dash_app("pkg-py/examples/08-dash-custom-app.py", port)
    try:
        _wait_for_app_ready(url, timeout=45.0)  # Dash takes time to start
        yield url
    finally:
        _terminate_process(proc, "08-dash-custom-app")
