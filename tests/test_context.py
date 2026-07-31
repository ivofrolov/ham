import unittest
from unittest import mock

from ham import cron, http, mqtt
from ham.context import Context


class TestContext(unittest.TestCase):
    def test_teardown(self):
        context = Context(
            cron_scheduler=mock.Mock(),
            http_router=mock.Mock(),
            mqtt_client=mock.Mock(),
        )
        context.cron = mock.create_autospec(cron.Api, instance=True)
        context.http = mock.create_autospec(http.Api, instance=True)
        context.mqtt = mock.create_autospec(mqtt.Api, instance=True)

        context.teardown()

        context.cron.teardown.assert_called()
        context.http.teardown.assert_called()
        context.mqtt.teardown.assert_called()
