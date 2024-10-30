import os
import json
from io import StringIO
from subprocess import Popen, PIPE
from time import sleep

import pika
import configparser

config = configparser.ConfigParser()

filename = r"G_device_settings.ini"
target_dir = r"/home/nvidia/QualityGrader"
# target_dir = r"/tmp"
target_path = os.path.join(target_dir, filename)


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
                pika.ConnectionParameters(host=api_host, credentials=credentials, heartbeat=30))
            channel = connection.channel()
            print(f"Created connection")

            try:
                with Popen(target_dir + "/qg log", stdout=PIPE, shell=True) as p:
                    for line in iter(p.stdout.readline, ''):
                        if not line:
                            break
                        try:
                            log_l = line.decode('UTF-8').split(" | ")
                            if "ERROR" in log_l[1] or "WARNING" in log_l[1]:
                                channel.basic_publish(exchange="log", body=json.dumps(
                                    {"message": line.decode('UTF-8'), "ip": machine_ip}), routing_key="")
                        except IndexError:
                            continue
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
