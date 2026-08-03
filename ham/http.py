import logging
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlsplit

from ham import proto

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Request:
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: bytes


@dataclass(slots=True)
class Response:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


class Router:
    _routes: dict[tuple[str, str], proto.HttpHandler]
    _lock: threading.Lock

    def __init__(self) -> None:
        self._routes = {}
        self._lock = threading.Lock()

    def add(self, method: str, path: str, handler: proto.HttpHandler) -> None:
        with self._lock:
            self._routes[(method, path)] = handler
        logger.debug("http route method=%s path=%r", method, path)

    def remove(self, method: str, path: str, handler: proto.HttpHandler) -> None:
        unroute = False
        with self._lock:
            if self._routes.get((method, path)) is handler:
                del self._routes[(method, path)]
                unroute = True
        if unroute:
            logger.debug("http unroute method=%s path=%r", method, path)

    def dispatch(self, request: Request) -> proto.HttpResponse:
        handler = self._routes.get((request.method, request.path))
        if handler is None:
            return Response(status=HTTPStatus.NOT_FOUND)

        try:
            return handler(request)
        except Exception:
            logger.exception("handler failed for %s %s", request.method, request.path)
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)


class Handler(BaseHTTPRequestHandler):
    timeout = 30  # socket timeout, seconds

    _max_body_length = 1024 * 1024  # bytes
    _router: Router

    def __init__(self, *args, router: Router, **kwargs):
        self._router = router
        super().__init__(*args, **kwargs)

    def _handle(self) -> None:
        url = urlsplit(self.path)

        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return
        if length < 0:
            self.send_error(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return
        if length > self._max_body_length:
            self.send_error(
                HTTPStatus.CONTENT_TOO_LARGE,
                f"max is {self._max_body_length} bytes",
            )
            return
        body = self.rfile.read(length) if length else b""

        request = Request(
            method=self.command,
            path=url.path,
            query=url.query,
            headers=dict(self.headers.items()),
            body=body,
        )
        response = self._router.dispatch(request)
        self.send_response(response.status)
        for key, value in response.headers.items():
            self.send_header(key, value)
        if "Content-Length" not in response.headers:
            self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(format, *args)
