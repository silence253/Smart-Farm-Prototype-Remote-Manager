import json
import requests
import time

# Key MB
ADAFRUIT_AIO_USERNAME = 'SmartFarmUSTH'
ADAFRUIT_AIO_KEY = ''

# CHANNEL
OUT_CHANNEL = "sfout"
IN_CHANNEL = "sfinp"
WIFI_CHANNEL = "wfout"


def sf_send(topic, msg):
    cmd = f"https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{IN_CHANNEL}/data"
    requests.post(cmd, data=json.dumps({"value": str(msg)}), headers={"X-AIO-Key": ADAFRUIT_AIO_KEY, "Content-Type": "application/json"})


def sf_recv_from_sfout(topic):
    cmd = f"https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{OUT_CHANNEL}/data/last"
    return requests.get(cmd, headers={"X-AIO-Key": ADAFRUIT_AIO_KEY, "Content-Type": "application/json"}).json()['value']

def sf_recv_from_wfout(topic):
    cmd = f"https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{WIFI_CHANNEL}/data/last"
    return requests.get(cmd, headers={"X-AIO-Key": ADAFRUIT_AIO_KEY, "Content-Type": "application/json"}).json()['value']

# control
sf_send(IN_CHANNEL, "win_close")

# sensor
# while True:
#     print(sf_recv(OUT_CHANNEL))
#     time.sleep(5)