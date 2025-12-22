from httpClass import Http
import paho.mqtt.client as mqtt
import json

mqtt_broker_host = "192.168.1.10"
mqtt_broker_port = 1883
mqtt_topic = "relay"

received_message = Http().getFile()
print(received_message)
commands = json.loads(received_message)
print(commands)

def sendRelayMessage(message):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Poll")
    client.connect(mqtt_broker_host, mqtt_broker_port)
    client.publish("relay", message, 1)
    client.disconnect()

if commands["success"]:
    data = commands["data"]

    for command in data:
        relay = command["relay"]
        turn = command["turn"]
        message = relay + " - " + turn
        sendRelayMessage(message)