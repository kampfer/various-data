"""管理服务线程封装的单元测试：启动、停止与端口占用。"""

from __future__ import annotations

import logging
import socket

import pytest
from fastapi import FastAPI

from admin.server import AdminServer, AdminServerError
from scheduler.config import AdminSettings

LOGGER = logging.getLogger("scheduler-test")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_start_and_stop_leaves_no_thread() -> None:
    port = _free_port()
    server = AdminServer(
        FastAPI(), AdminSettings(host="127.0.0.1", port=port), LOGGER
    )

    server.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
    finally:
        server.stop()

    assert server._thread is None
    with pytest.raises(OSError):
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass


def test_port_in_use_raises_port_error() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        port = int(occupied.getsockname()[1])
        server = AdminServer(
            FastAPI(), AdminSettings(host="127.0.0.1", port=port), LOGGER
        )

        with pytest.raises(AdminServerError) as excinfo:
            server.start()

    assert excinfo.value.kind == "port"


def test_disabled_server_does_not_start() -> None:
    server = AdminServer(
        FastAPI(), AdminSettings(enabled=False, port=_free_port()), LOGGER
    )
    server.start()
    server.stop()
    assert server._thread is None
