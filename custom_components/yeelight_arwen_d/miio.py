"""Minimal blocking miIO client (UDP port 54321, AES-128-CBC with the device token)."""

from __future__ import annotations

import hashlib
import itertools
import json
import socket
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PORT = 54321
HELLO = bytes.fromhex("21310020" + "ff" * 28)


class MiioError(Exception):
    """The device returned an error or an unreadable reply."""


class MiioTimeout(MiioError):
    """The device did not answer."""


def discover(timeout: float = 3.0) -> dict[int, str]:
    """Broadcast a hello and return {device id: IP address} of every miIO device that answers."""
    found: dict[int, str] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        # Without a broadcast route (some Docker or VLAN setups) sendto fails; the result is then empty.
        try:
            sock.sendto(HELLO, ("255.255.255.255", PORT))
            while True:
                reply, (ip, _) = sock.recvfrom(1024)
                if len(reply) >= 32 and reply[:2] == b"\x21\x31":
                    found[int.from_bytes(reply[8:12], "big")] = ip
        except OSError:
            pass
    return found


class MiioClient:
    """Send miIO commands to one device."""

    def __init__(self, host: str, token: str, timeout: float = 2.0) -> None:
        self.host = host
        self.did: int | None = None
        self._token = bytes.fromhex(token)
        self._key = hashlib.md5(self._token).digest()
        self._iv = hashlib.md5(self._key + self._token).digest()
        self._timeout = timeout
        self._ids = itertools.count(1)

    def send(self, method: str, params: Any) -> Any:
        """Send one command and return its "result" field; a lost packet is retried once."""
        for attempt in range(2):
            try:
                reply = self._exchange(method, params)
                break
            except OSError as err:
                if attempt == 1:
                    raise MiioTimeout(f"{method}: no reply from {self.host}") from err
        try:
            response = self._unpack(reply)
        except ValueError as err:
            # Bad padding or JSON: truncated packet or wrong token.
            raise MiioError(f"{method}: unreadable reply from {self.host}") from err
        if "error" in response:
            raise MiioError(f"{method}: {response['error']}")
        return response.get("result")

    def _exchange(self, method: str, params: Any) -> bytes:
        """Do the hello handshake, send the encrypted request and return the raw reply."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self._timeout)
            # The hello reply carries the device id and its clock, which every packet must echo.
            sock.sendto(HELLO, (self.host, PORT))
            hello, _ = sock.recvfrom(1024)
            self.did = int.from_bytes(hello[8:12], "big")
            request = {"id": next(self._ids) % 10000 + 1, "method": method, "params": params}
            sock.sendto(self._pack(request, hello[8:12], hello[12:16]), (self.host, PORT))
            reply, _ = sock.recvfrom(4096)
        return reply

    def _pack(self, request: dict, did: bytes, stamp: bytes) -> bytes:
        body = json.dumps(request).encode() + b"\x00"
        padder = padding.PKCS7(128).padder()
        encryptor = Cipher(algorithms.AES(self._key), modes.CBC(self._iv)).encryptor()
        payload = encryptor.update(padder.update(body) + padder.finalize()) + encryptor.finalize()
        stamp = (int.from_bytes(stamp, "big") + 1).to_bytes(4, "big")
        header = b"\x21\x31" + (32 + len(payload)).to_bytes(2, "big") + bytes(4) + did + stamp
        return header + hashlib.md5(header + self._token + payload).digest() + payload

    def _unpack(self, reply: bytes) -> dict:
        decryptor = Cipher(algorithms.AES(self._key), modes.CBC(self._iv)).decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        plain = decryptor.update(reply[32:]) + decryptor.finalize()
        plain = unpadder.update(plain) + unpadder.finalize()
        return json.loads(plain.rstrip(b"\x00"))
