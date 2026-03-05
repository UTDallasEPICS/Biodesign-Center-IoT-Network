import paho.mqtt.client as mqtt
import json
import base64

MQTT_BROKER = "192.168.x.x"   # gateway IP
MQTT_PORT = 1883
APP_ID = "1"
DEV_EUI = "microcontrollerID"

MQTT_TOPIC = f"application/{APP_ID}/device/+/rx" # + means get all

#when connected, subscribe to the gateway to the topic above
def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    client.subscribe(MQTT_TOPIC)

#when a message is recieved, decode the message from base 64. it will be json.
def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)
    data_b64 = payload.get('data', '')
    try:
        decoded = base64.b64decode(data_b64).decode('utf-8', errors='replace')
        print("Received:", decoded)
    except Exception as e:
        print("Decode error:", e, "| Raw:", data_b64)

#make the client, set the relevant functions, connect to the gateway.
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()