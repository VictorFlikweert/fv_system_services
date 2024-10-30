import os
import json
from io import StringIO
from subprocess import check_output
from time import sleep

from datetime import datetime

import glob
import tarfile
import requests

import pika
import configparser

config = configparser.ConfigParser()

filename = r"G_device_settings.ini"
target_dir = r"/home/nvidia/QualityGrader"
backup_dir = r"/etc/fv"
# target_dir = r"/tmp"
target_path = os.path.join(target_dir, filename)

mac_address = os.popen(
    "ifconfig | grep -A 11 'eth4' | grep -o -E '([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}'"
).read().strip()

software_version = os.popen(
    "cat /home/nvidia/QualityGrader/settings.ini | grep 'version = '"
).read().strip().split(' = ')[1]


def run():
    config.read(target_path)

    machine_ip = config.get("G_os", "machine_ip")
    rmq_username = config.get("G_os", "fv_api_user")
    rmq_password = config.get("G_os", "fv_api_password")
    api_host = config.get("G_os", "fv_api_ip")
    machine_type = config.get("G_os", "machine_type")

    tar_name = f"{datetime.today().strftime('%Y-%m-%d_%H-%M-%S')}__{machine_ip}__{mac_address}__{software_version}.tar"
    backup_path = os.path.join(backup_dir, tar_name)

    while True:
        try:
            print(f"Start with creating connection")
            credentials = pika.PlainCredentials(rmq_username, rmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=api_host, credentials=credentials, heartbeat=30))
            channel = connection.channel()
            print(f"Created connection")

            try:
                device = None
                optional = False
                machine_types = []

                tar_file = tarfile.open(backup_path, "w")

                with open('./backup_list.txt', 'r') as file:
                    for line in file.readlines():
                        l = line.rstrip()
                        if len(l) == 0:
                            continue

                        if l.startswith('// '):
                            continue

                        if l.startswith('#'):
                            optional = False

                        if l.startswith('####'):
                            device = l.split(' ')[1]
                            continue
                        if l.startswith('## Optional'):
                            optional = True
                            continue
                        elif l.startswith('##'):
                            machine_types = l.split('## ')[1].split(' ')
                            continue

                        if machine_type in machine_types:
                            print("Backupped: \b\b", device, f'Optional: {optional}', machine_types, line)
                            file_list_by_path = glob.glob(line.strip())
                            print(line, file_list_by_path)
                            for file_path in file_list_by_path:
                                tar_file.add(file_path)
                                print(f"DEBUG: {file_path} -> {tar_name}")

                tar_file.close()

                # Open the tar file in binary mode
                # sudo tar -xvf 2024-06-14_12-56.tar -C /
                with open(backup_path, "rb") as file:
                    channel.basic_publish(exchange="backup",
                                          body=file.read(),
                                          routing_key="",
                                          properties=pika.BasicProperties(
                                              headers={'file_name': tar_name}  # Add a key/value header
                                          ))

                os.remove(backup_path)
                connection.close()
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
