import hashlib
import os
import logging
import ssl
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
        self.mqtt_use_ssl = os.getenv('MQTT_USE_SSL', '').lower() in ['true', '1', 'yes']
        self.mqtt_trusted_fingerprint = os.getenv('MQTT_TRUSTED_FINGERPRINT') or None

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if mqtt_id and mqtt_passw:
            self.client.username_pw_set(mqtt_id, mqtt_passw)
        #self.client.will_set(mqtt_topic_lwt, payload='Offline', qos=0, retain=True)
        self.client.on_connect = self.on_connect

        if self.mqtt_use_ssl:
            logger.info("Using TLS...")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # Deaktiviere Hostnamenprüfung
            ssl_context.verify_mode = ssl.CERT_NONE  # Verhindert automatische Ablehnung
            self.client.tls_set_context(ssl_context)
        else:
            logger.info("Using unencrypted connection...")

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

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("Connected to MQTT Broker")
            if self.mqtt_use_ssl and not self.validate_certificate(client):
                client.disconnect()
        else:
            logger.error(f"Failed to connect to MQTT Broker, return code {reason_code}")

    def _on_message(self, client, userdata, msg):
        if msg.topic in self.handlers:
            self.handlers[msg.topic](msg.payload.decode())

    def get_ssl_certificate(self, client):
        """Tries to extract the server certificate from the MQTT-SSL-connection."""
        try:
            sock = client.socket()
            if isinstance(sock, ssl.SSLSocket):
                return sock.getpeercert(binary_form=True)
            else:
                logger.error("MQTT socket is not using SSL.")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve SSL certificate: {e}")
            return None


    def get_certificate_fingerprint(self, cert):
        """Validates the certificate's SHA256-hash."""
        return hashlib.sha256(cert).hexdigest()


    def validate_certificate(self, client):
        """Validates the certificate by TOFU."""
       
        cert = self.get_ssl_certificate(client)
        if not cert:
            logger.error("No certificate!")
            return False
        
        current_fingerprint = self.get_certificate_fingerprint(cert)

        if self.mqtt_trusted_fingerprint is None:
            self.mqtt_trusted_fingerprint = current_fingerprint
            logger.warning(f"No fingerprint set. The current certificate has following fingerprint: {self.mqtt_trusted_fingerprint}")
            return False
        
        if current_fingerprint == self.mqtt_trusted_fingerprint:
            logger.info("Certificate fingerprint matches. Connection trusted.")
            return True
        else:
            logger.error("Certificate fingerprint mismatch! Connection rejected.")
            return False
