import unittest
from unittest import mock

from ham import cron, http, proto
from ham.context import Context, CronApi, HttpApi, MqttApi


class TestCronApi(unittest.TestCase):
    def test_at(self):
        callback1 = mock.Mock(spec=proto.CronCallback)
        callback2 = mock.Mock(spec=proto.CronCallback)
        cron_mock = mock.create_autospec(cron.Cron, instance=True)
        api = CronApi(cron_mock)

        api.at(None, None, None, None, None, callback1)
        api.at(None, None, None, None, None, callback2)

        cron_mock.add.assert_has_calls(
            [
                mock.call(cron.Expr(), callback1),
                mock.call(cron.Expr(), callback2),
            ]
        )

    def test_at__expr(self):
        cron_mock = mock.create_autospec(cron.Cron, instance=True)
        api = CronApi(cron_mock)

        api.at(1, 2, 3, 4, 5, mock.Mock(spec=proto.CronCallback))

        cron_mock.add.assert_called_with(cron.Expr(M=1, H=2, d=3, m=4, w=5), mock.ANY)

    def test_teardown(self):
        callback1 = mock.Mock(spec=proto.CronCallback)
        callback2 = mock.Mock(spec=proto.CronCallback)
        cron_mock = mock.create_autospec(cron.Cron, instance=True)
        api = CronApi(cron_mock)
        api.at(None, None, None, None, None, callback1)
        api.at(None, None, None, None, None, callback2)

        api.teardown()

        cron_mock.remove.assert_has_calls(
            [
                mock.call(cron.Expr(), callback2),
                mock.call(cron.Expr(), callback1),
            ]
        )


class TestApi(unittest.TestCase):
    def test_route(self):
        handler1 = mock.Mock(spec=proto.HttpHandler)
        handler2 = mock.Mock(spec=proto.HttpHandler)
        router_mock = mock.create_autospec(http.Router, instance=True)
        api = HttpApi(router_mock)

        api.route("GET", "/test", handler1)
        api.route("POST", "/test", handler2)

        router_mock.add.assert_has_calls(
            [
                mock.call("GET", "/test", handler1),
                mock.call("POST", "/test", handler2),
            ]
        )

    def test_teardown(self):
        handler1 = mock.Mock(spec=proto.HttpHandler)
        handler2 = mock.Mock(spec=proto.HttpHandler)
        router_mock = mock.create_autospec(http.Router, instance=True)
        api = HttpApi(router_mock)
        api.route("GET", "/test", handler1)
        api.route("POST", "/test", handler2)

        api.teardown()

        router_mock.remove.assert_has_calls(
            [
                mock.call("POST", "/test", handler2),
                mock.call("GET", "/test", handler1),
            ]
        )


class TestContext(unittest.TestCase):
    def test_teardown(self):
        context = Context(
            cron_scheduler=mock.Mock(),
            http_router=mock.Mock(),
            mqtt_client=mock.Mock(),
        )
        context.cron = mock.create_autospec(CronApi, instance=True)
        context.http = mock.create_autospec(HttpApi, instance=True)
        context.mqtt = mock.create_autospec(MqttApi, instance=True)

        context.teardown()

        context.cron.teardown.assert_called()
        context.http.teardown.assert_called()
        context.mqtt.teardown.assert_called()
