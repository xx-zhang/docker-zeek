# coding:utf-8
"""
TODO: https://zhuanlan.zhihu.com/p/38330574
"""

from kafka import KafkaConsumer, KafkaProducer
import json


# KAFKA_DEFUALT_SERVER = '172.21.7.239:23092'

KAFKA_DEFUALT_SERVER = '192.168.33.10:9092'


def test_topic_sender_01():
    producer = KafkaProducer(bootstrap_servers=[KAFKA_DEFUALT_SERVER],
                             value_serializer=lambda m: json.dumps(m).encode('ascii'))
    future = producer.send('http_log', value={'value_1': 'value_2'}, partition=0)
    future.get(timeout=10)


def test_topic_02():
    consumer = KafkaConsumer(group_id='group2', bootstrap_servers=[KAFKA_DEFUALT_SERVER],
                             value_deserializer=lambda m: json.loads(m.decode('ascii')))
    consumer.subscribe(topics=['http_log', ])
    for msg in consumer:
        print(msg)


def test_sender_data():
    pass


def test_send_http_log_line():
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_DEFUALT_SERVER],
        value_serializer=lambda m: json.dumps(m).encode('ascii')
    )
    future = producer.send('http_log', value={'RES_BODY': 'none'}, partition=0)
    future.get(timeout=10)


if __name__ == '__main__':
    # test_get_data()
    test_topic_sender_01()
    # test_topic_02()


