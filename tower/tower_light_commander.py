import paho.mqtt.client as mqtt
import threading, logging

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client = None

def init(host, port):
    global _client
    with _lock:
        if _client is not None:
            return
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="LightCommander")
        c.reconnect_delay_set(min_delay=1, max_delay=10)
        c.connect(host, port, keepalive=30)
        c.loop_start()
        _client = c

def set_light(host, port, message):
    global _client
    if _client is None:
        init(host, port)

    info = _client.publish("tower/actuators/set", payload=message, qos=1)
    info.wait_for_publish(timeout=1)









