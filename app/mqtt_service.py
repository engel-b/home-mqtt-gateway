import os
import logging
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MQTTService")

class MQTTService:

    def __init__(self):
        mqtt_id = os.getenv('MQTT_ID') or None
        mqtt_passw = os.getenv('MQTT_PASS') or None
        mqtt_host = os.getenv('MQTT_HOST')
        mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        #mqtt_topic = os.getenv('MQTT_TOPIC', 'test/gateway')
        #mqtt_topic_lwt = mqtt_topic + '/status'
        mqtt_use_ssl = os.getenv('MQTT_USE_SSL', '').lower() in ['true', '1', 'yes']
        mqtt_trusted_fingerprint = os.getenv('MQTT_TRUSTED_FINGERPRINT') or None

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if mqtt_id and mqtt_passw:
            self.client.username_pw_set(mqtt_id, mqtt_passw)
        #self.client.will_set(mqtt_topic_lwt, payload='Offline', qos=0, retain=True)
        self.client.connect(mqtt_host, mqtt_port, 60)

        self.handlers = {}

        self.client.on_message = self._on_message

    def start(self):
        self.client.loop_start()
        logger.info("MQTT client started")

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    def subscribe(self, topic, handler):
        self.handlers[topic] = handler
        self.client.subscribe(topic)

    def _on_message(self, client, userdata, msg):
        if msg.topic in self.handlers:
            self.handlers[msg.topic](msg.payload.decode())