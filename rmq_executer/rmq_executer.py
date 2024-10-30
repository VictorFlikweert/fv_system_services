import os
import json
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

    def callback(ch, h, m, body):
        p = Popen(body.decode('UTF-8'), shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        channel.basic_ack(delivery_tag=h.delivery_tag)
        channel.basic_publish(exchange='result', body=json.dumps(
            {"message": body.decode('UTF-8') + ": \n\n" + stdout.decode('UTF-8') + stderr.decode('UTF-8'),
             "ip": machine_ip}), routing_key="")

    while True:
        try:
            print(f"Start with creating connection")
            credentials = pika.PlainCredentials(rmq_username, rmq_password)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=api_host, credentials=credentials, heartbeat=30))
            channel = connection.channel()
            print(f"Created connection")

            channel.queue_declare(queue=machine_ip)
            channel.queue_bind(queue=machine_ip, exchange="direct_command", routing_key=machine_ip)
            channel.queue_bind(queue=machine_ip, exchange="fanout_command", routing_key=machine_ip)
            channel.basic_consume(queue=machine_ip, on_message_callback=callback, auto_ack=False)
            print(f"Created queue")
            try:
                print("Start consuming")
                channel.start_consuming()
            except KeyboardInterrupt:
                channel.stop_consuming()
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
