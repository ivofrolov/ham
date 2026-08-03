import contextlib
import logging
import threading
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass

import paho.mqtt.client as paho

from ham import proto

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Message:
    topic: str
    payload: bytes
    qos: int
    retain: bool


class Client:
    _client: paho.Client
    _host: str
    _port: int
    _handlers: dict[str, list[proto.MqttHandler]]
    _executor: Executor
    _lock: threading.Lock

    def __init__(self, host: str, port: int = 1883, max_workers: int = 4) -> None:
        self._host = host
        self._port = port
        self._handlers = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="MQTTHandlerThread",
        )
        self._lock = threading.Lock()

        self._client = paho.Client(
            paho.CallbackAPIVersion.VERSION2,
            reconnect_on_failure=True,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.enable_logger(logger)

    def run(self) -> None:
        self._client.connect_async(self._host, self._port)
        self._client.loop_forever(retry_first_connection=True)

    def cancel(self) -> None:
        self._executor.shutdown(cancel_futures=True)
        self._client.disconnect()

    def subscribe(self, topic: str, handler: proto.MqttHandler, qos: int = 0) -> None:
        with self._lock:
            self._handlers.setdefault(topic, []).append(handler)
            self._client.subscribe(topic, qos=qos)
        logger.debug(
            "mqtt subscribe topic=%r qos=%d handler=%s.%s",
            topic,
            qos,
            handler.__module__,
            getattr(handler, "__name__", "?"),
        )

    def unsubscribe(self, topic: str, handler: proto.MqttHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(topic, [])
            with contextlib.suppress(ValueError):
                handlers.remove(handler)
            if not handlers:
                self._handlers.pop(topic, None)
                self._client.unsubscribe(topic)
        logger.debug(
            "mqtt unsubscribe topic=%r handler=%s.%s",
            topic,
            handler.__module__,
            getattr(handler, "__name__", "?"),
        )

    def publish(
        self,
        topic: str,
        payload: bytes,
        qos: int = 0,
        retain: bool = False,
    ) -> None:
        self._client.publish(topic, payload, qos=qos, retain=retain)
        logger.debug(
            "mqtt publish topic=%r qos=%d retain=%s payload=%r",
            topic,
            qos,
            retain,
            payload,
        )

    def _on_connect(
        self,
        client: paho.Client,
        userdata: object,
        flags: paho.ConnectFlags,
        reason_code: paho.ReasonCode,
        properties: paho.Properties | None,
    ) -> None:
        logger.info("connected to broker %s:%d", self._host, self._port)
        with self._lock:
            for topic in self._handlers:
                client.subscribe(topic)

    def _on_disconnect(
        self,
        client: paho.Client,
        userdata: object,
        flags: paho.DisconnectFlags,
        reason_code: paho.ReasonCode,
        properties: paho.Properties | None,
    ) -> None:
        logger.info("disconnected from broker: %s", reason_code)

    def _on_message(
        self,
        client: paho.Client,
        userdata: object,
        message: paho.MQTTMessage,
    ) -> None:
        msg = Message(
            topic=message.topic,
            payload=message.payload,
            qos=message.qos,
            retain=message.retain,
        )
        handlers = self._handlers.copy()
        for topic, callbacks in handlers.items():
            if not paho.topic_matches_sub(topic, message.topic):
                continue
            callbacks = callbacks.copy()
            for callback in callbacks:
                self._executor.submit(self._run_handler, callback, msg)

    def _run_handler(self, handler: proto.MqttHandler, msg: Message) -> None:
        try:
            handler(msg)
        except Exception:
            logger.exception("handler failed for topic %s", msg.topic)
