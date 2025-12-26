from datetime import datetime
import json
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import tower_light_commander
import tempfile
from tower_lock import tower_lock

load_dotenv()

mqtt_broker_host = os.getenv("MQTT_HOST")
mqtt_broker_port = int(os.getenv("MQTT_PORT"))

tower_json_path = "tower.json"

light = 5000

mqtt_topic = [("tower/actuators/status", 0), ("tower/sensors/status", 0)]

def read_data_dict(path: str):
    with tower_lock:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

def replace_file(data: dict):
    with tower_lock:
        file_name = None
        dir_name = os.path.dirname(tower_json_path) or "."
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=dir_name) as tmp:
                file_name = tmp.name
                json.dump(data, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())

            os.replace(file_name, tower_json_path)
        except Exception:
            if file_name and os.path.exists(file_name):
                os.remove(file_name)
            raise

def upsert_json_dict(key: str, updates: dict):
    global tower_json_path
    data = read_data_dict(tower_json_path)
    data.update({key: updates})
    replace_file(data)

def on_message(_client, _userdata, message):
    try:
        payload_str = message.payload.decode("utf-8")
        data = json.loads(payload_str)

        if message.topic == "tower/sensors/status":
            global light
            light = data["light_raw"]
            upsert_json_dict("sensor_status", data)

        elif message.topic == "tower/actuators/status":
            upsert_json_dict("actuator_status", data)
            send_light_command()

    except Exception as e:
        print("on_message error:", repr(e))

def is_daytime():
    now = datetime.now().time()
    return now >= datetime.strptime("05:00", "%H:%M").time() and now < datetime.strptime("22:00", "%H:%M").time()

def send_light_command():
    global light
    old = read_data_dict(tower_json_path)
    switch_state = old["switch_status"] 
    actuator_state = old["actuator_status"]
    daytime = is_daytime()
    
    for key, value in actuator_state.items():
        if key.startswith("light"):
            switch_value = switch_state.get(key)
            print (f"key: {key}, switch_value: {switch_value}, daytime: {daytime}")

            payload_dict = None

            if switch_value and daytime and light < 3000 and not value:
                payload_dict = {"channel": key, "value": 1}
                
            if (not switch_value or not daytime or light >=3000) and value:
                payload_dict = {"channel": key, "value": 0}

            if payload_dict is not None:
                payload = json.dumps(payload_dict, ensure_ascii=False)
                print(payload)
                tower_light_commander.setLight(mqtt_broker_host, mqtt_broker_port, payload)
    
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "TowerLightSubscriber")
client.on_message = on_message
client.connect(mqtt_broker_host, mqtt_broker_port)
client.subscribe(mqtt_topic)
client.loop_forever()