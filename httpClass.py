import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

class Http():
    def __init__(self):
        self.endpoint = os.getenv("BACKEND") + "uploadSensorData.php"
        self.localhost = os.getenv("LOCALHOST")
        self.datapoint = os.getenv("BACKEND") + "getFile.php"
        self.moisturepoint = os.getenv("WEATHER_API")
        self.headers = {'Referer': self.localhost}

    def send(self, data):
        payload = {'sensor': json.dumps(data, indent=4)}
        try:
            response = requests.post(self.endpoint, data=payload, headers=self.headers)

            return response.text

        except requests.exceptions.RequestException as e:
            print(e)

    def getFile(self):
        try:
            response = requests.get(self.datapoint, headers=self.headers, timeout=15)

            return response.text

        except requests.exceptions.RequestException as e:
            print(e)

            return '{"success": false, "data": []}'

    def getMoistureData(self):
        params = {
            "latitude": float(os.getenv("LATITUDE")),
            "longitude": float(os.getenv("LONGITUDE")),
            "timezone": "Europe/Budapest",
            "hourly": "precipitation,temperature_2m",
            "past_days": 2,
            "forecast_days": 1
        }
        try:
            response = requests.get(self.moisturepoint, params=params)

            return response.text
        except requests.exceptions.RequestException as e:
            print(e)