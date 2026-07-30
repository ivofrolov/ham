from ham import cron, http, mqtt, proto


class Context(proto.Context):
    cron: cron.Api
    http: http.Api
    mqtt: mqtt.Api

    def __init__(self, cron: cron.Api, http: http.Api, mqtt: mqtt.Api):
        self.cron = cron
        self.http = http
        self.mqtt = mqtt

    def teardown(self) -> None:
        self.cron.teardown()
        self.mqtt.teardown()
        self.http.teardown()
