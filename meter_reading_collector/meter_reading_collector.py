import configparser
import os

import requests

config = configparser.ConfigParser()

filename = r"G_device_settings.ini"
target_dir = r"/home/nvidia/QualityGrader"
target_path = os.path.join(target_dir, filename)

config.read(target_path)

machine_ip = config.get("G_os", "machine_ip")
api_host = config.get("G_os", "fv_api_ip")
machine_type = config.get("G_os", "machine_type")

crop_type_l = [
    'potato',
    'oniony',
    'onionr'
]

for crop_type in crop_type_l:
    try:
        if machine_type in ['QG', 'QG_VS']:
            with open(f"{target_dir}/Data/QG_{crop_type}_history.json", 'rb') as f:
                requests.post(f"http://{api_host}:5001/meter_readings?machine_type=QualityGrader&ip={machine_ip}&crop_type={crop_type}",
                              files={'file': f})

        if machine_type in ['VS', 'QG_VS']:
            with open(f"{target_dir}/Data/VS_{crop_type}_history.json", 'rb') as f:
                requests.post(f"http://{api_host}:5001/meter_readings?machine_type=RejectSeparator&ip={machine_ip}&crop_type={crop_type}",
                              files={'file': f})
    except FileNotFoundError as ex:
        continue
