from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Protocol


@dataclass(slots=True)
class Range:
    lo: int
    hi: int


type Atom[T] = T | Sequence[T] | Every
Minute = Atom[Annotated[int, Range(0, 59)]]
Hour = Atom[Annotated[int, Range(0, 23)]]
DayOfMonth = Atom[Annotated[int, Range(1, 31)]]
Month = Atom[Annotated[int, Range(1, 12)]]
DayOfWeek = Atom[Annotated[int, Range(0, 6)]]  # Sun=0, Mon=1
Every = None

CronCallback = Callable[[], None]


class CronApi(Protocol):
    def at(
        self,
        M: Minute,
        H: Hour,
        d: DayOfMonth,
        m: Month,
        w: DayOfWeek,
        callback: CronCallback,
    ) -> None: ...


class HttpRequest(Protocol):
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: bytes


class HttpResponse(Protocol):
    status: int
    headers: dict[str, str]
    body: bytes


HttpHandler = Callable[[HttpRequest], HttpResponse]


class HttpApi(Protocol):
    def route(self, method: str, path: str, handler: HttpHandler) -> None: ...


class MqttMessage(Protocol):
    topic: str
    payload: bytes
    qos: int
    retain: bool


MqttHandler = Callable[[MqttMessage], None]


class MqttApi(Protocol):
    def subscribe(self, topic: str, handler: MqttHandler, qos: int = 0) -> None: ...
    def publish(
        self,
        topic: str,
        payload: bytes,
        qos: int = 0,
        retain: bool = False,
    ) -> None: ...


class Context(Protocol):
    cron: CronApi
    http: HttpApi
    mqtt: MqttApi


Setup = Callable[[Context], None]
