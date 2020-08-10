## 




## server-run 
```bash 

docker run -itd --name=syslog-server \
    --net=host \
    -v /data/logs/:/opt/ \
    -v $(pwd)/syslog-ng.conf:/etc/syslog-ng/syslog-ng.conf \
    registry.cn-shenzhen.aliyuncs.com/rapid7/syslog-ng \
    -edv
```

```conf 
@version: 3.18
@include "scl.conf"

source src_path { network(
        ip("0.0.0.0")
        port(30051)
        flags(syslog-protocol)
        transport("tcp")
    ); };

destination dst_path { file("/opt/test.log"); };

log { source(src_path); destination(dst_path); };
```