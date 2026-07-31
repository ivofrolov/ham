from ham import cron, http, mqtt, proto


class Context(proto.Context):
    cron: cron.Api
    http: http.Api
    mqtt: mqtt.Api

    def __init__(
        self,
        cron_scheduler: cron.Cron,
        http_router: http.Router,
        mqtt_client: mqtt.Client,
    ):
        self.cron = cron.Api(cron_scheduler)
        self.http = http.Api(http_router)
        self.mqtt = mqtt.Api(mqtt_client)

    def teardown(self) -> None:
        self.cron.teardown()
        self.mqtt.teardown()
        self.http.teardown()
