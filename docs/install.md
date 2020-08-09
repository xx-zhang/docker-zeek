# 部署文档 - 基于 debian-10
> 从来没有什么岁月静好，不过是有人在为你负重前行。
- 这里借鉴了 rita / malcolm 

## 部署说明

- [debian10-国内源](./sources.list) 是清华源, 注释了deb-src所以比较快。
- [zeek插件](./zeek_install_plugins.sh)
- [zeek环境变量](./zeek.env)


## docker-main 
```bash
docker run -itd --name=zeek \
    -v $(pwd)zeek/packages.zeek:/usr/local/zeek/share/zeek/site/packages/packages.zeek \
    -v $(pwd)zeek/scripts/:/usr/local/zeek/share/zeek/site/packages/scripts \
    -v /data/zeek/logs:/usr/local/zeek/logs \
    -v /data/zeek/current:/usr/local/zeek/spool/manager/ \
    -v $(pwd)/zeek/docker-entrypoint.sh:/etc/entrypoint.sh \
    -v $(pwd)/zeek/node.cfg:/usr/local/zeek/etc/node.cfg \
    registry.cn-beijing.aliyuncs.com/rapid7/zeek \
    /entrypoint.sh
```