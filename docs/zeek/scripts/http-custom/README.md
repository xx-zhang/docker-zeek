# zeek_scripts 

## 此脚本可以在zeek-3.0.7 http log中记录如下信息：

> * http request header name 和 value ; k-v
> * http response header name 和 value; list:list 
> * request body   - - - -- - - - post-body记录在 `main.zeek` 
> * response body  - - - -- - - - -  
> * response time  - -- - -- - -- 根据消息时间弄的
## 补充说明
- http-header-logs 记录的是如果取出键值对的话使用得方法
- 舍弃了`http-header-logs`因为需要已知的http头键值对来管理太麻烦。

## 2020-8-9
- [请求头和响应头的列表](./http-header-logs-vector.zeek)
- [请求阶段的请求体](./main.zeek)
- [请求阶段的请求体](./main.zeek)

## 参考
- [vector列表的http请求头和响应头](../zeek-log-all-http-headers)
- [request-body](../zeek-plugin-http-request-enrichment)
- [request-body-post-body2](../log-add-http-post-bodies)
- [重要参考](https://blog.csdn.net/roshy/article/details/89673851)
