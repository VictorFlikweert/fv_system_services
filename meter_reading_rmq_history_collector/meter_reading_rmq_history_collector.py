import hashlib
import os
import json
import shutil
from time import sleep

import pika
import configparser

import requests

from datetime import datetime

config = configparser.ConfigParser()

filename = r"G_device_settings.ini"
target_dir = r"/home/nvidia/QualityGrader"
# target_dir = r"/tmp"
target_path = os.path.join(target_dir, filename)


def parse_activity_str_to_duration(activity_str):
    date_str = activity_str.split('since ')[1].split(';')[0]
    start_ts = datetime.strptime(date_str, "%a %Y-%m-%d %H:%M:%S %Z").timestamp()
    current_ts = datetime.now().timestamp()
    return current_ts - start_ts


def run():
    config.read(target_path)

    machine_ip = config.get("G_os", "machine_ip")
    rmq_username = config.get("G_os", "fv_api_user")
    rmq_password = config.get("G_os", "fv_api_password")
    api_host = config.get("G_os", "fv_api_ip")
    machine_type = config.get("G_os", "machine_type")

    while True:
        try:
            print(f"Start with creating connection")
            credentials = pika.PlainCredentials(rmq_username, rmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=api_host, credentials=credentials, heartbeat=90))
            channel = connection.channel()
            print(f"Created connection")

            try:
                crop_type_l = [
                    'potato',
                    'oniony',
                    'onionr'
                ]

                for crop_type in crop_type_l:
                    try:
                        if machine_type in ['QG', 'QG_VS']:
                            with open(f"{target_dir}/Data/QG_{crop_type}_history.json", 'rb') as f:
                                stream_data = f.read()
                                file_hash = hashlib.md5(stream_data).hexdigest()

                                json_data = json.loads(stream_data)
                                channel.basic_publish(exchange="machine_meter_reading_history", body=json.dumps(
                                    {"message": json_data, "ip": machine_ip, "crop_type": crop_type,
                                     "file_hash": file_hash}),
                                                      routing_key="")

                        if machine_type in ['VS', 'QG_VS']:
                            with open(f"{target_dir}/Data/VS_{crop_type}_history.json", 'rb') as f:
                                stream_data = f.read()
                                file_hash = hashlib.md5(stream_data).hexdigest()

                                json_data = json.loads(stream_data)
                                channel.basic_publish(exchange="machine_meter_reading_history", body=json.dumps(
                                    {"message": json_data, "ip": machine_ip, "crop_type": crop_type,
                                     "file_hash": file_hash}),
                                                      routing_key="")
                        if machine_type in ['SG']:
                            with open(f"{target_dir}/Data/SG_{crop_type}_history.json", 'rb') as f:
                                stream_data = f.read()
                                file_hash = hashlib.md5(stream_data).hexdigest()

                                json_data = json.loads(stream_data)
                                channel.basic_publish(exchange="machine_meter_reading_history", body=json.dumps(
                                    {"message": json_data, "ip": machine_ip, "crop_type": crop_type,
                                     "file_hash": file_hash}),
                                                      routing_key="")
                    except FileNotFoundError as ex:
                        continue

                break

            except KeyboardInterrupt:
                connection.close()
                break
        except pika.exceptions.ConnectionClosedByBroker:
            continue
        # Do not recover on channel errors
        except pika.exceptions.AMQPChannelError as err:
            print("Caught a channel error: {}, stopping...".format(err))
            print("Trying to reconnect in 5 seconds...")
            sleep(5)
            break
        # Recover on all other connection errors
        except pika.exceptions.AMQPConnectionError:
            print("Connection was closed, retrying...")
            print("Trying to reconnect in 5 seconds...")
            sleep(5)
            continue


if __name__ == '__main__':
    run()

