# coding:utf-8
import os
# import json
import ast
from zeek_parser.custom_http_log import parse_zeek_http_custom_log_raw
from zeek_parser.kafka_helper import KafkaHelper


class Py3HttpKafka(object):

    def send(self, msg):
        """
        # TODO 日志输入进来后进行先格式化为我们需要的，另外再发送到kafka
        :param msg:
        :return:
        """
        data = msg['LEGACY_MSGHDR'] + msg['MESSAGE']
        item = ast.literal_eval(data.decode())
        _raw = parse_zeek_http_custom_log_raw(item)
        KafkaHelper(topic='zeek_custom_http_log_raw', ).send(_raw)
        return True

