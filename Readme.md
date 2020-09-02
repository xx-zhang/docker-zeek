# Docker-zeek 

- 参考了 rita / malcolm 


## 基础使用
- 为了测试和管理的方便，这里我们自己定义的所有脚本都放置再 `scripts` 中并再`packages.zeek`中管理
- 不需要干涉 `local.zeek` 这个核心的配置文件; 当然如果增加对应的协议检测，在后面是一样

### Docker 运行最新的
- `packages.zeek`
- `scripts` 自定以的一些脚本
- `/usr/local/zeek/logs` 日志位置、当前自动轮转。
- `registry.cn-beijing.aliyuncs.com/rapid7/zeek` 镜像构建。 


## Docker-Upgrade-For-RITA
```bash
touch node.cfg

docker run --rm -it --network host \
    -v $(pwd)/node.cfg:/node.cfg \
    registry.cn-beijing.aliyuncs.com/rapid7/docker-zeek \
    zeekcfg -o /node.cfg --type afpacket

docker run --cap-add net_raw --cap-add net_admin \
    --network host --detach \
    --name zeek \
    --restart always \
    -v /etc/localtime:/etc/localtime:ro \
    -v $(pwd)/share/zeek/site/my.zeek:/usr/local/zeek/share/zeek/site/local.zeek \
    -v $(pwd)/docs/zeek/scripts:/usr/local/zeek/share/zeek/site/scripts \
    -v /spool/zeek/:/usr/local/zeek/logs/ \
    -v /spool/zeek/real_time:/usr/local/zeek/spool/manager \
    -v $(pwd)/node.cfg:/usr/local/zeek/etc/node.cfg \
    registry.cn-beijing.aliyuncs.com/rapid7/docker-zeek
```

## 2020-8-20 
- 出现了问题，上面的基于rita的无法正常运转。
- NOTE: 注意脚本编码，windows拷贝后有问题。