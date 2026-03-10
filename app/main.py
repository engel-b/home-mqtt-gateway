import time
from mqtt_service import MQTTService

# Modules
from modules.ecowater_module import EcowaterModule
from modules.myvaillant_module import MyVaillantModule
from modules.uponor_module import UponorModule

mqtt = MQTTService()
mqtt.start()

modules = [
    EcowaterModule(mqtt),
    MyVaillantModule(mqtt),
    UponorModule(mqtt),
]

for module in modules:
    module.start()

while True:
    time.sleep(60)