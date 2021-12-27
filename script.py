import sengled
from dotenv import load_dotenv
from threading import Thread

load_dotenv()

api = sengled.api_from_env()

devices = api.get_device_details()

def change_light(device):
    device.set_color([11, 102, 35])
    device.set_brightness(100)
    #device.set_color_temperature(10)

for device in devices:
    print(device)
    Thread(target=change_light, args=(device, )).start()
    

