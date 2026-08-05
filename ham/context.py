import contextlib
from functools import partial

from ham import cron, http, mqtt, proto


class CronApi(proto.CronApi):
    _cron: cron.Cron
    _teardown: contextlib.ExitStack

    def __init__(self, cron: cron.Cron) -> None:
        self._cron = cron
        self._teardown = contextlib.ExitStack()

    def at(
        self,
        M: proto.Minute,
        H: proto.Hour,
        d: proto.DayOfMonth,
        m: proto.Month,
        w: proto.DayOfWeek,
        callback: proto.CronCallback,
    ) -> None:
        expr = cron.Expr(M, H, d, m, w)
        self._cron.add(expr, callback)
        self._teardown.callback(partial(self._cron.remove, expr, callback))

    def teardown(self) -> None:
        self._teardown.close()


class HttpApi(proto.HttpApi):
    _router: http.Router
    _teardown: contextlib.ExitStack

    def __init__(self, router: http.Router) -> None:
        self._router = router
        self._teardown = contextlib.ExitStack()

    def route(self, method: str, path: str, handler: proto.HttpHandler) -> None:
        self._router.add(method, path, handler)
        self._teardown.callback(partial(self._router.remove, method, path, handler))

    def teardown(self) -> None:
        self._teardown.close()


class MqttApi(proto.MqttApi):
    _client: mqtt.Client
    _teardown: contextlib.ExitStack

    def __init__(self, client: mqtt.Client) -> None:
        self._client = client
        self._teardown = contextlib.ExitStack()

    def subscribe(self, topic: str, handler: proto.MqttHandler, qos: int = 0) -> None:
        self._client.subscribe(topic, handler, qos)
        self._teardown.callback(partial(self._client.unsubscribe, topic, handler))

    def publish(
        self,
        topic: str,
        payload: bytes,
        qos: int = 0,
        retain: bool = False,
    ) -> None:
        self._client.publish(topic, payload, qos=qos, retain=retain)

    def teardown(self) -> None:
        self._teardown.close()


class Context(proto.Context):
    cron: CronApi
    http: HttpApi
    mqtt: MqttApi

    def __init__(
        self,
        cron_scheduler: cron.Cron,
        http_router: http.Router,
        mqtt_client: mqtt.Client,
    ):
        self.cron = CronApi(cron_scheduler)
        self.http = HttpApi(http_router)
        self.mqtt = MqttApi(mqtt_client)

    def teardown(self) -> None:
        self.cron.teardown()
        self.mqtt.teardown()
        self.http.teardown()
