"""Loopback-only HTTP server that never performs reverse DNS during bind.

`http.server.HTTPServer.server_bind` calls `socket.getfqdn`, which can hang for
tens of seconds on offline hosts.  A fixed loopback hostname is sufficient for
these local, ephemeral-port experiments and makes their timing reproducible.
"""

from __future__ import annotations

from http.server import ThreadingHTTPServer
from socketserver import TCPServer


class LoopbackHTTPServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        if host != "127.0.0.1":
            raise ValueError("loopback server must bind 127.0.0.1")
        self.server_name = "localhost"
        self.server_port = port
