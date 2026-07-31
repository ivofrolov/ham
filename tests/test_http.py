import unittest
from unittest import mock

from ham.http import Api, Request, Router
from ham.proto import HttpHandler


class TestRouter(unittest.TestCase):
    def test_add(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router = Router()

        router.add("GET", "/test1", handler1)
        router.add("POST", "/test2", handler2)

        request1 = Request("GET", "/test1", "", {}, b"")
        router.dispatch(request1)
        request2 = Request("POST", "/test2", "", {}, b"")
        router.dispatch(request2)

        handler1.assert_called_with(request1)
        handler2.assert_called_with(request2)

    def test_add__same_path__different_method(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router = Router()

        router.add("GET", "/test", handler1)
        router.add("POST", "/test", handler2)

        request1 = Request("GET", "/test", "", {}, b"")
        router.dispatch(request1)
        request2 = Request("POST", "/test", "", {}, b"")
        router.dispatch(request2)

        handler1.assert_called_with(request1)
        handler2.assert_called_with(request2)

    def test_add__same_path__same_method(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router = Router()

        router.add("GET", "/test", handler1)
        router.add("GET", "/test", handler2)

        request = Request("GET", "/test", "", {}, b"")
        router.dispatch(request)

        handler1.assert_not_called()
        handler2.assert_called()

    def test_remove__on_reload(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router = Router()

        router.add("GET", "/test", handler1)
        router.add("GET", "/test", handler2)
        router.remove("GET", "/test", handler1)

        request = Request("GET", "/test", "", {}, b"")
        router.dispatch(request)

        handler1.assert_not_called()
        handler2.assert_called()


class TestApi(unittest.TestCase):
    def test_route(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router_mock = mock.create_autospec(Router, instance=True)
        api = Api(router_mock)

        api.route("GET", "/test", handler1)
        api.route("POST", "/test", handler2)

        router_mock.add.assert_has_calls(
            [
                mock.call("GET", "/test", handler1),
                mock.call("POST", "/test", handler2),
            ]
        )

    def test_teardown(self):
        handler1 = mock.Mock(spec=HttpHandler)
        handler2 = mock.Mock(spec=HttpHandler)
        router_mock = mock.create_autospec(Router, instance=True)
        api = Api(router_mock)
        api.route("GET", "/test", handler1)
        api.route("POST", "/test", handler2)

        api.teardown()

        router_mock.remove.assert_has_calls(
            [
                mock.call("POST", "/test", handler2),
                mock.call("GET", "/test", handler1),
            ]
        )
