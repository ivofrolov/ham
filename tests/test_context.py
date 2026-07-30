import unittest
from unittest import mock

from ham import cron, http, mqtt
from ham.context import Context


class TestContext(unittest.TestCase):
    def test_teardown(self):
        cron_mock = mock.create_autospec(cron.Api, instance=True)
        http_mock = mock.create_autospec(http.Api, instance=True)
        mqtt_mock = mock.create_autospec(mqtt.Api, instance=True)
        context = Context(cron=cron_mock, http=http_mock, mqtt=mqtt_mock)

        context.teardown()

        cron_mock.teardown.assert_called()
        http_mock.teardown.assert_called()
        mqtt_mock.teardown.assert_called()
