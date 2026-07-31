import argparse
import logging
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

from ham import cron, http, mqtt
from ham.context import Context
from ham.loader import Loader

parser = argparse.ArgumentParser(description="Home Automation Machine")
parser.add_argument(
    "-s",
    "--scripts",
    type=Path,
    default="scripts",
    help="scripts folder path (default: %(default)s)",
)
parser.add_argument(
    "--http-host",
    default="127.0.0.1",
    help="HTTP server bind address (default: %(default)s)",
)
parser.add_argument(
    "--http-port",
    type=int,
    default=8080,
    help="HTTP server bind port (default: %(default)s)",
)
parser.add_argument(
    "--mqtt-host",
    default="127.0.0.1",
    help="MQTT broker address (default: %(default)s)",
)
parser.add_argument(
    "--mqtt-port",
    type=int,
    default=1883,
    help="MQTT broker port (default: %(default)s)",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="increase log level (default: ERROR)",
)


def main() -> int:
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s [%(threadName)s] %(message)s",
        level=(
            logging.ERROR,
            logging.WARNING,
            logging.INFO,
            logging.DEBUG,
        )[min(args.verbose, 3)],
    )

    logger = logging.getLogger(__name__)

    stop = threading.Event()

    def _on_thread_exception(args: threading.ExceptHookArgs) -> None:
        logger.critical(
            "unhandled exception, shutting down",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        stop.set()

    threading.excepthook = _on_thread_exception

    http_router = http.Router()
    http_server = ThreadingHTTPServer(
        (args.http_host, args.http_port),
        partial(http.Handler, router=http_router),
    )
    http_server_thread = threading.Thread(
        target=http_server.serve_forever,
        name="HTTPServerThread",
    )
    http_server_thread.start()
    logger.info("http server listening on %s:%d", args.http_host, args.http_port)

    mqtt_client = mqtt.Client(args.mqtt_host, args.mqtt_port)
    mqtt_thread = threading.Thread(target=mqtt_client.run, name="MQTTClientThread")
    mqtt_thread.start()
    logger.info("mqtt client connecting to %s:%d", args.mqtt_host, args.mqtt_port)

    cron_scheduler = cron.Cron()
    cron_thread = threading.Thread(target=cron_scheduler.run, name="CronThread")
    cron_thread.start()
    logger.info("cron scheduling")

    loader = Loader(
        args.scripts,
        partial(Context, cron_scheduler, http_router, mqtt_client),
    )
    loader_thread = threading.Thread(target=loader.run, name="LoaderThread")
    loader_thread.start()
    logger.info("loader polling %s", args.scripts)

    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        logger.info("got interrupt signal, shutting down")
    finally:
        loader.cancel()
        loader_thread.join()
        cron_scheduler.cancel()
        cron_thread.join()
        mqtt_client.cancel()
        mqtt_thread.join()
        http_server.shutdown()
        http_server_thread.join()

    return 1 if stop.is_set() else 0
