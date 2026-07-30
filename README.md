# Home Automation Machine

A small kernel for home automation, meant to run as a single long-lived process (e.g. in
a container on a router) that just glues together inputs and outputs like MQTT, HTTP,
cron, etc.

The main goal is to be able to add, edit, and remove automation scripts by simply
dropping files into a folder or changing them via SSH. These scripts are hot-reloaded
upon change without the need for a service restart.

Scripts do not import or otherwise depend on the kernel at runtime. A broken script
never takes down a previously working one.

## Setup

Install the Python package using pip or other tool. Run it with `ham` command passing HTTP binding options, MQTT broker address and scripts folder location, e.g.

``` shell
pip install git+https://github.com/ivofrolov/ham.git

ham -vv --scripts ./scripts \
    --http-host 127.0.0.1 --http-port 8080 \
    --mqtt-host 127.0.0.1 --mqtt-port 1883
```

Here is a minimal container example.

``` dockerfile
FROM debian:stable-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    pipx \
    && rm -rf /var/lib/apt/lists/*

RUN pipx install --global --system-site-packages git+https://github.com/ivofrolov/ham.git

RUN mkdir -p /opt/ham
WORKDIR /opt/ham

RUN mkdir -p /opt/ham/scripts
VOLUME /opt/ham/scripts

EXPOSE 80

ENTRYPOINT ham -vv --scripts /opt/ham/scripts \
           --http-host 0.0.0.0 --http-port 80 \
           --mqtt-host broker --mqtt-port 1883
```

## Scripting

Put your scripts in a folder and pass it in `--scripts` parameter to `ham`. Implement `setup(ctx: "Context")` method using context object to utilize APIs (see [proto.py](ham/proto.py)):
  * schedule regular tasks,
  * subscribe and publish to MQTT topics,
  * register HTTP handlers.

Here is a script example.

``` python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ham.proto import Context, HttpRequest, MqttMessage

logger = logging.getLogger(__name__)


def cron_task() -> None:
    logger.debug("run cron task")


@dataclass(slots=True)
class HttpResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


def on_http_request(request: "HttpRequest") -> HttpResponse:
    logger.debug("received request on %s", request.path)
    return HttpResponse(200, {"Content-Type": "text/html"}, b"<h1>TODO</h1>")


def on_mqtt_message(message: "MqttMessage") -> None:
    logger.debug("received message on %s: %s", message.topic, message.payload)


def setup(ctx: "Context") -> None:
    ctx.cron.at(None, None, None, None, None, cron_task)
    ctx.http.route("GET", "/foobar", on_http_request)
    ctx.mqtt.subscribe("foo/bar", on_mqtt_message)
```
