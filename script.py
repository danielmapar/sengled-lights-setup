import sengled
from dotenv import load_dotenv
from threading import Thread
import random
import time

load_dotenv()

api = sengled.api_from_env()

devices = api.get_device_details()



def change_light(device, color):
    device.set_color(color)
    device.set_brightness(random.randrange(1, 100))
    #device.set_color_temperature(10)

while (True):
    time.sleep(10)
    red = random.randrange(1, 255)
    green = random.randrange(1, 255)
    blue = random.randrange(1, 255)
    color = [red, green, blue]
    threads = []
    for device in devices:
        threads.append(Thread(target=change_light, args=(device, color, )))
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    

