import asyncio
import aiohttp
import os
import logging
from myPyllant.api import MyPyllantAPI
from modules.base_module import BaseModule


VAILLANT_POLL_INTERVALL = os.getenv('VAILLANT_POLL_INTERVALL', 600)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyVaillantModule")

DEFAULT_ATTRS = [
    "temperature", "humidity", "setpoint", "status",
    "connection_status", "diagnostic_trouble_codes", "rts", "mpc", "energy_management", "eebus"
]

class MyVaillantModule(BaseModule):
    """MyVaillant-Integration: Nur lesen & pushen an MQTT."""

    def __init__(self, mqtt_client):
        super().__init__(mqtt_client, VAILLANT_POLL_INTERVALL)
        self.user = os.getenv("MYVAILLANT_USER")
        self.passw = os.getenv("MYVAILLANT_PASS")
        self.brand = os.getenv("MYVAILLANT_BRAND", "vaillant")
        self.country = os.getenv("MYVAILLANT_COUNTRY", "germany")
        self.topic = os.getenv('VAILLANT_TOPIC', 'test/vaillant')
        self.last_values = {}


    def fetch_and_publish(self):
        """Sync-Methode für BaseModule, kapselt async-Aufrufe in Eventloop."""
        asyncio.run(self._async_fetch_and_publish())


    async def _async_fetch_and_publish(self):
        """Holt Systeme aus der Cloud und pusht nur geänderte Werte."""
        async with MyPyllantAPI(self.user, self.passw, self.brand, self.country) as api:
            try:
                async for system in api.get_systems():
                    await self.publish_system(system)
            except aiohttp.client_exceptions.ClientResponseError as e:
                if e.status == 403:
                    logger.warning(f"Vaillant API Quota exceeded: {e}")
                    # eine kurze Pause einlegen
                    await asyncio.sleep(300)
                else:
                    raise

            # Optional: detailreichere Abfragen
            async for system in api.get_systems(
                include_connection_status=True,
                include_diagnostic_trouble_codes=True,
                include_rts=True,
                include_mpc=True,
                include_energy_management=True,
                include_eebus=True
            ):
                await self.publish_system(system)


    async def publish_system(self, system):
        """Geht alle Attribute durch und publisht nur geänderte Werte."""

        system_id = getattr(system, "id", "system")

        for key, value in vars(system).items():

            topic = f"{self.topic}/{system_id}/{key}"
            value_str = str(value)

            if self.last_values.get(topic) != value_str:
                self.mqtt.publish(topic, value_str)
                self.last_values[topic] = value_str