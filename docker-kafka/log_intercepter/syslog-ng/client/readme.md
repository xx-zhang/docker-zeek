# 通过syslog-ng发送日志，通过python处理发送到最终的 Kafka 上。


## python3 环境 ub1804
```
sudo apt-get -y install python3-pip python3-setuptools 
sudo /usr/bin/python3 -m pip install -U pylint --user --index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 运行 slogsql 
```shell

docker run -itd --name=slog2 \
--net=host --restart=always \
-e KAFKA_SERVER=',' \
-v /spool/:/logs \
-v $(pwd)/py-es/xetl:/software/xetl \
-v $(pwd)/py-es/syslog-ng.conf:/software/syslog-ng/etc/syslog-ng.conf \
registry.cn-hangzhou.aliyuncs.com/meigea/py3-syslog-kafka::v1 \
/bin/bash /entrypoint.sh 
```

## 2020-8-10 
- 今天使用了本地日志阻截器发送日志到kafka,但是本地是否是异步多线程这里还不清楚。

```

```