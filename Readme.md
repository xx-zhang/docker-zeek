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
```bash 
docker run -itd --name=zeek \
    -v 
```