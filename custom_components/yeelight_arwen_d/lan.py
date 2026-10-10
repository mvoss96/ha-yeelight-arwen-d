"""Receive the state changes a lamp pushes over the Yeelight LAN protocol (TCP 55443)."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from collections.abc import Callable
from typing import Any

from .const import LAN_PORT

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 5
RETRY_DELAY = 5


async def listen(
    get_host: Callable[[], str],
    on_props: Callable[[dict[str, Any]], None],
    on_connected: Callable[[bool], None],
) -> None:
    """Keep a connection open, pass each pushed "props" message on and reconnect after errors.

    Nothing is ever sent: the lamp counts every command it receives on this port against a
    quota of 60 per minute. Commands go over miIO, which has no such limit.
    """
    while True:
        host = get_host()
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, LAN_PORT), CONNECT_TIMEOUT)
        except (OSError, TimeoutError) as err:
            _LOGGER.debug("No LAN connection to %s: %s", host, err)
            await asyncio.sleep(RETRY_DELAY)
            continue
        _enable_keepalive(writer.get_extra_info("socket"))
        _LOGGER.debug("LAN connection to %s open", host)
        on_connected(True)
        try:
            while line := await reader.readline():
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if isinstance(message, dict) and message.get("method") == "props":
                    on_props(message.get("params", {}))
        # ValueError: a line longer than the stream buffer.
        except (OSError, ValueError) as err:
            _LOGGER.debug("LAN connection to %s lost: %s", host, err)
        finally:
            writer.close()
        # Not reached when the task is cancelled on unload.
        on_connected(False)
        await asyncio.sleep(RETRY_DELAY)


def _enable_keepalive(sock: Any) -> None:
    """Notice a lamp that lost power; without traffic the connection would otherwise never close."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    for option, value in (("TCP_KEEPIDLE", 10), ("TCP_KEEPINTVL", 5), ("TCP_KEEPCNT", 3)):
        if hasattr(socket, option):
            sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, option), value)
