# HomeMqttGateway Docker image

This is a wrapper used to get smart home device data from special apis or manufacturer cloud services into the local smart home. It requests the registered systems an pushes the data to the configured mqtt topic.

| Service | API -> Broker | Api <- Broker | API |
| :--- | :--- | :--- | :--- |
| Ecowater | :heavy_check_mark: | :heavy_minus_sign: | Cloud |
| MyVaillant | :heavy_check_mark: | :heavy_minus_sign: | Cloud |
| Uponor | :heavy_check_mark: | :heavy_check_mark: | Local gateway |

I tried to make this reusable. If something is missing to get it running on your machine, let me know.


## Parameters

### MQTT

Initialize MQTT connection to broker

```python
MQTT_HOST=<hostname or IP of broker, required>
MQTT_PORT=<port, if different from default; default is 1883>
MQTT_ID=<username, if required; default is null>
MQTT_PASS=<password, if required; default is null>
MQTT_USE_SSL=<true, if secured connection; default is false>
MQTT_TRUSTED_FINGERPRINT=""
```

#### Validate TLS connection

In HomeMqttGateway a light check of a ssl-connection is implemented by verifing the broker's certificate hash. To do so, set `MQTT_USE_SSL=True`. Start the container again and have a lock into the log. There should be a message like 
`No fingerprint set. The current certificate has following fingerprint: f50cdfdb6122d16b...` 
Copy the hash and add the attribute `MQTT_TRUSTED_FINGERPRINT=f50cdfdb6122d16b...` to your commandline.


### Ecowater

Retrieve a list of all devices associated with the Ecowater account

```python
ECOWATER_EMAIL=<username, required>
ECOWATER_PASS=<password, required>
ECOWATER_SERIAL=<serial to filter, if multiple devices are requistered to this account; default is null>
ECOWATER_TOPIC=<MQTT-topic, where the data needs to be pushed to; default is "test/ecowater/{serial}">
ECOWATER_POLL_INTERVALL=<time in seconds between update; default is 30>
```


### MyVaillant

Get the device model (string)

```python
MYVAILLANT_USER=<username, required>
MYVAILLANT_PASS=<password, required>
MYVAILLANT_BRAND=<brand the account is registered in; default is "vaillant">
MYVAILLANT_COUNTRY=<country the account is registered in; default is "germany">
MYVAILLANT_TOPIC=<MQTT-topic, where the data needs to be pushed to; default is "test/vaillant">
MYVAILLANT_POLL_INTERVALL=<time in seconds between update; default is 600>
```


### Uponor

Get the device model (string)

```python
UPONOR_GATEWAY=<hostname or IP of gateway, required>
UPONOR_TOPIC=<MQTT-topic, where the data needs to be pushed to; default is "test/uponor/{roomname}">
UPONOR_POLL_INTERVALL=<time in seconds between update; default is 60>
```


## Build & push
```bash
docker build -t engelb/homemqttgateway:<version> .
docker push engelb/homemqttgateway:<version>
```

The build and deployment is done by Github Actions automatically when something is pushed to main.


## Run
```bash
docker run -d \
--name='home-mqtt-gateway' \
--network=host \
-e MQTT_HOST=... \
-e ECOWATER_EMAIL=... \
-e ECOWATER_PASS=... \
-e MYVAILLANT_USER=... \
-e MYVAILLANT_PASS=... \
-e UPONOR_GATEWAY=... \
-e engelb/homemqttgateway:latest
```

Hashes in variable values ​​should be avoided!

or by env-file:
```bash
docker run -d --env-file envfile.env engelb/homemqttgateway:latest
```
