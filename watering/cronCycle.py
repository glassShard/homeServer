from httpClass import Http
from datetime import datetime
import json
import paho.mqtt.client as mqtt
import time
import os
from dotenv import load_dotenv

load_dotenv()

relays = [{
    'name': '1',
    'sleep': 300
}, {
    'name': '2',
    'sleep': 300
}, {
    'name': '3',
    'sleep': 720
}, {
    'name': '4',
    'sleep': 0
}]

mqtt_broker_host = os.getenv("MQTT_HOST")
mqtt_broker_port = float(os.getenv("MQTT_PORT"))

received_message = Http().getMoistureData()
commands = json.loads(received_message)

now = datetime.now()

current_time = now.strftime("%Y-%m-%d %H:%M:%S")

times = commands['hourly']['time']
precipitations = commands['hourly']['precipitation']
temperature = commands['hourly']['temperature_2m']
data = []

for index, item in enumerate(times):
    itemDate = datetime.fromisoformat(item)

    if itemDate < now:
        data.append({
            'date': itemDate,
            'precipitation': precipitations[index],
            'temperature': temperature[index]
        })

lastIndex = len(data) - 1

result = {
    '12': {
        'aveTemperature': 0,
        'sumPrecipitation': 0,
        'sumTemp': 0
        },
    '24': {
        'aveTemperature': 0,
        'sumPrecipitation': 0,
        'sumTemp': 0
        }
}

for index, hour in enumerate(data):
    if index > lastIndex - 12:
        result['12']['sumTemp'] += hour['temperature']
        result['12']['sumPrecipitation'] += hour['precipitation']
    if index > lastIndex - 24:
        result['24']['sumTemp'] += hour['temperature']
        result['24']['sumPrecipitation'] += hour['precipitation']

result['12']['aveTemperature'] = float(result['12']['sumTemp']) / 12
result['24']['aveTemperature'] = float(result['24']['sumTemp']) / 24

print(result)

def getResOutside():
    if result['12']['aveTemperature'] > 28:
        if result['12']['sumPrecipitation'] < 2:
            return True
        return False
    if result['12']['aveTemperature'] > 20:
        if result['12']['sumPrecipitation'] < 1:
            return True
        return False
    if result['24']['sumPrecipitation'] < 1:
        return True
    return False

res = getResOutside()

def sendRelayMessage(message):
    print(datetime.now())
    print(message)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "cronCycle")
    client.connect(mqtt_broker_host, mqtt_broker_port)
    client.publish("relay", message, 1)
    client.disconnect()

for i in relays:
    message = i['name'] + " - ON"
    sendRelayMessage(message)
    time.sleep(i['sleep'])