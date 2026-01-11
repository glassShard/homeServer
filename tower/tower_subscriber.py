from datetime import datetime
import json, os, logging, tempfile
from threading import Thread
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import tower_light_commander
from tower_lock import tower_lock
from logging.handlers import TimedRotatingFileHandler
from db import db_worker, queue_db_write

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        TimedRotatingFileHandler(os.getenv("LOGPATH"), when="midnight", backupCount=3)
    ]
)

logger = logging.getLogger(__name__)

mqtt_broker_host = os.getenv("MQTT_HOST")
mqtt_broker_port = int(os.getenv("MQTT_PORT"))

tower_json_path = os.getenv("TOWER_JSON_PATH")

light = 5000
LIGTH_FROM = "05:00"
LIGHT_TO = "21:00"

SENSOR_FREQUENCY = 10
ACTUATOR_FREQUENCY = 10

sensor = 0
actuator = 0

mqtt_topic = [("tower/actuators/status", 0), ("tower/sensors/status", 0)]

def read_data_dict(path: str):
    with tower_lock:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    #print(json.load(f))
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

def send_data(topic_str: str, payload: dict):
    logger.info(f"topic_str: {topic_str}, payload: {payload}")
    topic = topic_str.split("/")[1]
    fields = []
    values = []
    for key, value in payload.items():
        fields.append(key)
        values.append(value)

    try:
        logger.info(f"fields: {fields}, values: {values}")
        queue_db_write({"table": topic, "fields": fields, "values": values})
    except Exception as e: 
        logger.error(str(e))
        pass

def on_message(_client, _userdata, message):
    global sensor, actuator
    try:
        payload_str = message.payload.decode("utf-8")
        data = json.loads(payload_str)
        logger.info(f"topic: {message.topic}, data: {data}")

        if message.topic == "tower/sensors/status":
            global light
            light = data["light_raw"]
            upsert_json_dict("sensor_status", data)
            sensor += 1
            logger.info(f"sensor: {sensor}")
            if sensor == SENSOR_FREQUENCY:
                send_data(message.topic, data)
                sensor = 0

        elif message.topic == "tower/actuators/status":
            upsert_json_dict("actuator_status", data)
            send_light_command()
            actuator += 1
            if actuator == ACTUATOR_FREQUENCY:
                send_data(message.topic, data)
                actuator = 0

    except Exception as e:
        logger.error(f"on_message error: {e!r}")

def is_daytime():
    now = datetime.now().time()
    return now >= datetime.strptime(LIGTH_FROM, "%H:%M").time() and now < datetime.strptime(LIGHT_TO, "%H:%M").time()

def send_light_command():
    global light
    old = read_data_dict(tower_json_path)
    switch_state = old["switch_status"] 
    actuator_state = old["actuator_status"]
    daytime = is_daytime()
    
    for key, value in actuator_state.items():
        if key.startswith("light"):
            switch_value = switch_state.get(key)
            payload_dict = None

            if switch_value and daytime and light < 3200 and not value:
                payload_dict = {"channel": key, "value": 1}
                
            if (not switch_value or not daytime or light >=3400) and value:
                payload_dict = {"channel": key, "value": 0}

            if payload_dict is not None:
                payload = json.dumps(payload_dict, ensure_ascii=False)
                logger.info(f"payload: {payload}")
                #tower_light_commander.setLight(mqtt_broker_host, mqtt_broker_port, payload)
    
def on_connect(client, userdata, flags, reason_code, properties=None):
    logger.info(f"CONNECTED, {reason_code}")
    client.subscribe(mqtt_topic)

def on_disconnect(client, userdata, flags, reason_code, properties=None):
    logger.info(f"DISCONNECTED, {reason_code}")

Thread(target=db_worker, daemon=True).start()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, os.getenv("LIGHT_SUBSCRIBER_CLIENT_NAME"))
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=10)
client.connect(mqtt_broker_host, mqtt_broker_port, keepalive=30)
client.loop_forever(retry_first_connection=True)
