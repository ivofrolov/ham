import itertools
import threading
import unittest
from datetime import datetime, timedelta
from unittest import mock

from ham.cron import Cron, Expr, is_it_time
from ham.proto import CronCallback


class TestCronExpression(unittest.TestCase):
    def _test_is_it_time(self, expr, t, range_, want=True):
        for d in range_:
            dt = t + d
            with self.subTest(expr=expr, dt=dt):
                self.assertEqual(want, is_it_time(expr, dt))

    def test_day_or_weekday(self):
        now = datetime.now()
        self._test_is_it_time(
            Expr(M=now.minute, H=now.hour, d=now.day, w=now.isoweekday() % 7),
            now,
            itertools.chain(
                (timedelta(weeks=w) for w in range(1, 5)),
                (now.replace(month=now.month + 1) - now,),
            ),
        )
        self._test_is_it_time(
            Expr(M=now.minute, H=now.hour, d=now.day, w=now.isoweekday() % 7),
            now,
            (timedelta(days=d) for d in range(1, 7)),
            want=False,
        )


class TestCronScheduler(unittest.TestCase):
    def setUp(self):
        self.patcher = mock.patch.multiple(Cron, _wake_timeout=0.01, _granularity=0.0)
        self.patcher.start()

        self.cron = Cron()

        self.thread = threading.Thread(target=self.cron.run)
        self.thread.start()

    def tearDown(self):
        self.cron.cancel()
        self.thread.join(0.1)

        self.patcher.stop()

    def test_cancel(self):
        self.cron.cancel()

        self.thread.join(timeout=0.1)
        assert not self.thread.is_alive()

    @mock.patch("datetime.datetime")
    def test_run(self, datetime_mock):
        datetime_mock.now.return_value = datetime.min

        callback = mock.ThreadingMock(spec=CronCallback)
        self.cron.add(Expr(), callback)

        callback.wait_until_called(timeout=0.1)

    @mock.patch("datetime.datetime")
    def test_remove(self, datetime_mock):
        datetime_mock.now.return_value = datetime.min

        callback = mock.ThreadingMock(spec=CronCallback)
        self.cron.add(Expr(), callback)

        callback.wait_until_called(timeout=0.1)

        self.cron.remove(Expr(), callback)
        callback.reset_mock()

        self.thread.join(timeout=0.1)
        callback.assert_not_called()
