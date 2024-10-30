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

    while True:
        try:
            print(f"Start with creating connection")
            credentials = pika.PlainCredentials(rmq_username, rmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=api_host, credentials=credentials, heartbeat=90))
            channel = connection.channel()
            print(f"Created connection")

            try:

                while True:
                    response1 = requests.get(f"http://{machine_ip}:5001/machine_status_monitorings_systeem")
                    response2 = requests.get(f"http://{machine_ip}:5001/machine_status")
                    channel.basic_publish(exchange="machine_data", body=json.dumps(
                        {"message": json.dumps(response1.json()), "ip": machine_ip}), routing_key="")
                    channel.basic_publish(exchange="machine_data_status", body=json.dumps(
                        {"message": json.dumps(response2.json()), "ip": machine_ip}), routing_key="")

                    try:
                        active_result = os.popen('systemctl status QualityGrader.service --no-pager | grep " active"').read()
                        inactive_result = os.popen('systemctl status QualityGrader.service --no-pager | grep "inactive"').read()

                        active_time_d = None
                        inactive_time_d = None

                        if active_result:
                            active_time_d = {
                                "QG_active_time": parse_activity_str_to_duration(active_result)
                            }

                        if inactive_result:
                            inactive_time_d = {
                                "QG_inactive_time": parse_activity_str_to_duration(inactive_result)
                            }

                        channel.basic_publish(exchange="machine_data_status", body=json.dumps(
                            {"message": json.dumps(active_time_d or inactive_time_d), "ip": machine_ip}), routing_key="")

                    except IndexError:
                        pass

                    try:
                        total, used, free = shutil.disk_usage('/home/nvidia/SSD')
                        prepared_d = {
                            "G_free_memory": free // (2 ** 30)
                        }
                    except FileNotFoundError:
                        prepared_d = {
                            "G_free_memory": 0
                        }
                    finally:
                        channel.basic_publish(exchange="machine_data_status", body=json.dumps(
                            {"message": json.dumps(prepared_d), "ip": machine_ip}), routing_key="")

                    connection.sleep(60)

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
