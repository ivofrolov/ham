from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ham.proto import Context, HttpRequest, MqttMessage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HttpResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


def cron_task() -> None:
    logger.debug("cron task run")


def on_http_request(request: "HttpRequest") -> HttpResponse:
    logger.debug("http request received on %s", request.path)
    return HttpResponse(200, {"Content-Type": "text/html"}, b"<h1>TODO</h1>")


def on_mqtt_message(message: "MqttMessage") -> None:
    logger.debug("mqtt message received on %s: %s", message.topic, message.payload)


def setup(ctx: "Context") -> None:
    ctx.cron.at(None, None, None, None, None, cron_task)
    ctx.http.route("GET", "/foobar", on_http_request)
    ctx.mqtt.subscribe("foo/bar", on_mqtt_message)
    logger.debug("script set up")


def teardown() -> None:
    logger.debug("script torn down")
