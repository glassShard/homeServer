from datetime import datetime
import csv
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

mqtt_broker_host = os.getenv("MQTT_HOST")
mqtt_broker_port = float(os.getenv("MQTT_PORT"))

mqtt_topic = [("water", 0), ("relayWater", 0)]

soil_file_path = "soil.csv"
relay_file_path = "relay.csv"

def sendRelayMessage(client, message):
    client.publish("relay", message)

def on_message(client, userdata, message):
    add_data(client, message.topic, message.payload.decode())

def add_data(client, topic, message):
    print("Message received on topic " + topic)
    print(message)
    data_list = message.split(" - ")
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    data_list.append(current_time)

    file_path = soil_file_path if topic == "water" else relay_file_path

    if topic == "water" and int(data_list[1]) < 50:
        relayMessage = data_list[0] + ' - ON'
        sendRelayMessage(client, relayMessage)

    try:
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data_list)
    except IOError:
        print("File not found: " + file_path)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Subscriber")
client.on_message = on_message
client.connect(mqtt_broker_host, mqtt_broker_port)
client.subscribe(mqtt_topic)
client.loop_forever()