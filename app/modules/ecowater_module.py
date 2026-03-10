import os
import logging

# https://github.com/barleybobs/ecowater-softener
import ecowater_softener 

from modules.base_module import BaseModule

ECOWATER_POLL_INTERVALL = os.getenv('ECOWATER_POLL_INTERVALL', 30)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EcowaterModule")

DEFAULT_ATTRS = [
        "model",
        "serial_number",
        "software_version",
        "rssi",
        "ip_address",

        "water_use_avg_daily",
        "water_use_today",
        "water_available",

        "current_water_flow",

        "salt_level_percentage",
        "out_of_salt_days",
        "out_of_salt_date",
        "salt_type",

        "rock_removed_avg_daily",
        "rock_removed",

        "device.recharge_status",
        "recharge_enabled",
        "recharge_scheduled",
        "recharge_recharging",
        "last_recharge_days",
        "last_recharge_date"
    ]

class EcowaterModule(BaseModule):
    """MyVaillant-Integration: Nur lesen & pushen an MQTT."""

    def __init__(self, mqtt_client):
        super().__init__(mqtt_client, ECOWATER_POLL_INTERVALL)

        self.ecowater_serial = os.getenv('ECOWATER_SERIAL') or None
        self.ecowater_user = os.getenv('ECOWATER_EMAIL')
        self.ecowater_pass = os.getenv('ECOWATER_PASS')
        self.ecowater_topic = os.getenv('ECOWATER_TOPIC', 'test/ecowater')

        # Account-Objekt einmalig erstellen
        self.ecowater_account = self.getAccount()
        

    def getAccount(self):
        try:
            ecowater_account = ecowater_softener.EcowaterAccount(
                self.ecowater_user,
                self.ecowater_pass
            )
            logger.info("Ecowater account initialized")
            return ecowater_account
        except Exception as e:
            logger.exception("Failed to initialize Ecowater account")
            raise


    def fetch_and_publish(self):
        """Holt Systeme aus der Cloud und pusht nur geänderte Werte."""
        devices = self.ecowater_account.get_devices()
        if not devices:
            logger.warning("No devices found for Ecowater account")
            return
        
        for device in devices:

            device.update()   # holt aktuelle Werte
            device_sn = device.serial_number

            if self.ecowater_serial and device_sn != self.ecowater_serial:
                # skip processing
                continue

            # Attribute filtern
            current_values = {}
            for attr in DEFAULT_ATTRS:
                if hasattr(device, attr):
                    current_values[attr] = getattr(device, attr)

            device_root_topic = f"{self.ecowater_topic}/{device_sn}"

            # nur Änderungen publishen
            for k, v in current_values.items():
                if self.last_values.get(k) != v:
                    topic = f"{device_root_topic}/{k}"
                    self.mqtt.publish(topic, str(v))
                    self.last_values[k] = v
