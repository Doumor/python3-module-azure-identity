# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
from typing import Any, Mapping

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs


class AuthCodeRedirectHandler(BaseHTTPRequestHandler):
    """HTTP request handler to capture the authentication server's response.
    Mostly from the Azure CLI: https://github.com/Azure/azure-cli/blob/dev/src/azure-cli-core/azure/cli/core/_profile.py
    """

    def do_GET(self):
        if self.path.endswith("/favicon.ico"):  # deal with legacy IE
            self.send_response(204)
            return

        query = self.path.split("?", 1)[-1]
        parsed = parse_qs(query, keep_blank_values=True)
        self.server.query_params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in parsed.items()}

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(b"Authentication complete. You can close this window.")

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin,unused-argument
        pass  # this prevents server dumping messages to stdout


class AuthCodeRedirectServer(HTTPServer):
    """HTTP server that listens for the redirect request following an authorization code authentication"""

    query_params = {}  # type: Mapping[str, Any]

    def __init__(self, hostname, port, timeout):
        # type: (str, int, int) -> None
        HTTPServer.__init__(self, (hostname, port), AuthCodeRedirectHandler)
        self.timeout = timeout

    def wait_for_redirect(self):
        # type: () -> Mapping[str, Any]
        while not self.query_params:
            try:
                self.handle_request()
            except (IOError, ValueError):
                # socket has been closed, probably by handle_timeout
                break

        # ensure the underlying socket is closed (a no-op when the socket is already closed)
        self.server_close()

        # if we timed out, this returns an empty dict
        return self.query_params

    def handle_timeout(self):
        """Break the request-handling loop by tearing down the server"""
        self.server_close()
