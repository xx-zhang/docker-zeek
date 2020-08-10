# coding:utf-8
import os
from kafka import KafkaConsumer, KafkaProducer
import json

default_kafka_server = os.environ.get('KAFKA_SERVER') \
    if 'KAFKA_SERVER' in os.environ.keys() else '192.168.33.10:9092'


class KafkaHelper:

    def __init__(self, topic='default_topic_0810', kafka_server=default_kafka_server):
        self.kafka_server = kafka_server
        self.topic = topic

    def send(self, msg):
        producer = KafkaProducer(
            bootstrap_servers=list(self.kafka_server.split(',')),
            value_serializer=lambda m: json.dumps(m).encode('ascii')
        )
        future = producer.send(self.topic, value=msg, partition=0)
        future.get(timeout=5)

    def consumer_topic(self):
        consumer = KafkaConsumer(
            group_id='group2',
            bootstrap_servers=self.kafka_server,
            value_deserializer=lambda m: json.loads(m.decode('ascii'))
        )
        consumer.subscribe(topics=[self.topic, ])
        for msg in consumer:
            print(msg)

    def consumer_topics(self, topics):
        consumer = KafkaConsumer(
            group_id='group2',
            bootstrap_servers=self.kafka_server,
            value_deserializer=lambda m: json.loads(m.decode('ascii'))
        )
        consumer.subscribe(topics=topics.split(','))
        for msg in consumer:
            # TODO 开始消费当前的topic集合。这里就是简单打印，生产环境中要做处理的，比如入ES
            print(msg)
