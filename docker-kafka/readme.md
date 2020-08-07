## kafka-docker 


## 2020-8-7 
- 后续需要日志发送相关的预研。

```bash


docker run -d \
     --net=host \
     --name=kfk_manager \
     -e ZK_HOSTS="localhost:2181" \
     hlebalbau/kafka-manager:stable \
     -Dpidfile.path=/dev/null
```