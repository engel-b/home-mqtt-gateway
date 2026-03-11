import threading
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModuleBase")

class BaseModule:
    """Basisklasse für alle Integrationen"""

    def __init__(self, mqtt_client, poll_interval=30):
        self.mqtt = mqtt_client
        self.poll_interval = int(poll_interval)
        self.last_values = {}
        self._stop_thread = False


    def start(self):
        t = threading.Thread(target=self.loop, daemon=True)
        t.start()
        logger.info("%s started", self.__class__.__name__)


    def stop(self):
        self._stop_thread = True


    def loop(self):
        while not self._stop_thread:
            try:
                self.fetch_and_publish()
            except Exception:
                logger.exception("Error in %s loop", self.__class__.__name__)
            time.sleep(self.poll_interval)


    def fetch_and_publish(self):
        """Soll von Subklasse überschrieben werden"""
        raise NotImplementedError()