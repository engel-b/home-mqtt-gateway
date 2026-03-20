import os
import logging
import requests

from modules.base_module import BaseModule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UponorModule")

UPONOR_POLL_INTERVALL = os.getenv('UPONOR_POLL_INTERVALL', 60)

DEFAULT_ATTRS = ["temperature", "humidity", "setpoint"]

class UponorModule(BaseModule):
    """Uponor-Integration: lesen & pushen an MQTT, MQTT lesen und pushen an Thermostat."""

    required_config = ["UPONOR_GATEWAY"]
    
    def __init__(self, mqtt_client):
        super().__init__(mqtt_client, UPONOR_POLL_INTERVALL)

        if not self._enabled:
            logger.info("%s disabled", self.__class__.__name__)
            return
        
        gateways = os.getenv('UPONOR_GATEWAY')
        self.gateways = [g.strip() for g in gateways.split(",") if g.strip()]
        self.topic = os.getenv('UPONOR_TOPIC', 'test/uponor')
        self.room_map = {}
        self.room_topic_map = self.createRoomTopicMap(os.getenv('UPONOR_ROOM_TOPIC_MAPPING',) or None)
        self.devices = {}  # key: room_name -> dict mit Werten
        # Keine Subscribes hier, erst nach erster Abfrage

    # -------------------------------
    # Helper Funktionen
    # -------------------------------
    @staticmethod
    def fahrenheit2celsius(value):
        celsius = (float(value) - 32) * 5 / 9
        return round(celsius, 1)

    @staticmethod
    def celsius2fahrenheit(value):
        fahrenheit = (float(value) * 9 / 5) +32
        return round(fahrenheit, 1)


    def createRoomTopicMap(self, roomTopicMappings):
        return dict(item.split("=", 1) for item in roomTopicMappings.split(";")) if roomTopicMappings is not None else {}


    def room2topic(self, room):
        return self.room_topic_map.get(room, room)


    def topic2room(self, topic):
        for k, v in self.room_topic_map.items():
            if v == topic:
                return  k

        return topic


    def api_call(self, gateway, action, payload):
        headers = {
            "Content-Type": "application/json",
            "x-jnap-action": action
        }

        url = f"http://{gateway}/JNAP/"

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            if r.status_code != 200:
                logger.warning("API call %s failed: %s", action, r.status_code)
                return None
            return r.json()
        except requests.RequestException as e:
            logger.warning("API call exception on %s: %s", gateway, e)
            return None


    def get_attributes(self):
        results = []

        for gateway in self.gateways:
            data = self.api_call(
                gateway,
                "http://phyn.com/jnap/uponorsky/GetAttributes",
                {}
            )
            if data:
                results.append(data)

        return results
    

    # -------------------------------
    # MQTT Rückrichtung: Soll-Werte setzen
    # -------------------------------
    def subscribe_topic_for_room(self, room):
        topic = f"{self.topic}/{self.room2topic(room)}/setpoint/set"
        self.mqtt.subscribe(topic, lambda payload, r=room: self.set_setpoint(r, payload))

    def set_setpoint(self, room, payload):
        try:
            value = float(payload)
        except ValueError:
            logger.warning("Invalid setpoint value for %s: %s", room, payload)
            return

        if room not in self.room_map:
            logger.warning("Unknown room for setpoint: %s", room)
            return

        var = self.room_map[room] + "_setpoint"
        payload = {"vars": [{"waspVarName": var, "waspVarValue": str(int(self.celsius2fahrenheit(value)*10))}]}
        self.api_call("http://phyn.com/jnap/uponorsky/SetAttributes", payload)
        logger.info("Setpoint for %s updated to %s", room, value)


    # -------------------------------
    # Daten verarbeiten
    # -------------------------------
    def parse(self, data):
        vars = data.get("output", {}).get("vars", [])
        rooms = {}

        for v in vars:
            name = v["waspVarName"]
            value = v["waspVarValue"]

            # Raumzuordnung
            if "_name" in name:
                room_id = name.replace("cust_", "").replace("_name", "")
                room_name = value.lower().replace(" ", "_")
                self.room_map[room_name] = room_id
                rooms.setdefault(room_name, {})

            # Temperatur
            if "_room_temperature" in name:
                room_id = name.split("_room_temperature")[0]
                for r, rid in self.room_map.items():
                    if rid == room_id:
                        rooms.setdefault(r, {})
                        rooms[r]["temperature"] = self.fahrenheit2celsius(int(value)/10)

            # Luftfeuchtigkeit
            if "_rh" in name:
                room_id = name.split("_rh")[0]
                for r, rid in self.room_map.items():
                    if rid == room_id:
                        rooms.setdefault(r, {})
                        rooms[r]["humidity"] = int(value)

            # Sollwert
            if "_setpoint" in name:
                room_id = name.split("_setpoint")[0]
                for r, rid in self.room_map.items():
                    if rid == room_id:
                        rooms.setdefault(r, {})
                        rooms[r]["setpoint"] = self.fahrenheit2celsius(int(value)/10)

        return rooms


    # -------------------------------
    # Polling + Publish
    # -------------------------------
    def fetch_and_publish(self, forceUpdate):
        all_data = self.get_attributes()
        if not all_data:
            return

        merged_rooms = {}

        for data in all_data:
            rooms = self.parse(data)

            for room, values in rooms.items():
                merged_rooms.setdefault(room, {}).update(values)

        # Neue Räume abonnieren
        new_rooms = {r: v for r, v in merged_rooms.items() if r not in self.devices}
        for room in new_rooms:
            self.subscribe_topic_for_room(room)

        # Geräte aktualisieren
        self.devices.update(merged_rooms)

        # nur Änderungen publishen
        for room, values in merged_rooms.items():
            for attr, val in values.items():
                if attr not in DEFAULT_ATTRS:
                    continue
                key = f"{self.room2topic(room)}/{attr}"
                if self.last_values.get(key) != val or forceUpdate:
                    topic = f"{self.topic}/{key}"
                    self.mqtt.publish(topic, str(val))
                    self.last_values[key] = val
