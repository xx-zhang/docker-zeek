# coding:utf-8
import json
try:
    from dateutil import parser
except:
    print('you shoud install `python-dateutil`; `pip3 install python-dateutil==2.7.5`')


def parse_zeek_http_custom_log_raw(msg):
    _obj = json.loads(msg)
    timestamp = parser.parse(_obj["ts"]).strftime("%Y:%m:%d %H:%M:%S")
    remote_ip = _obj["id.orig_h"]
    remote_port = _obj["id.orig_p"]
    server_host = _obj["id.resp_h"]
    server_port = _obj["id.resp_p"]
    del _obj["id.orig_h"], _obj["id.orig_p"], _obj["id.resp_h"], _obj["id.resp_p"]
    proxies, request_body, response_body = "", "", ""
    if "proxied" in _obj.keys():
        proxies = json.dumps(_obj['proxied'])
    if "post_body" in _obj.keys():
        request_body = _obj['post_body']
        del _obj['post_body']
    if "body" in _obj.keys():
        response_body = _obj['body']
        del _obj['body']
    # TODO :: fix missing url
    # TODO :: Parse request_header
    _request_header_names = ["-".join([y.capitalize() for y in x.split('-')]) for x in _obj['client_header_names']]
    _request_header_values = _obj['client_header_values']
    request_headers = {_request_header_names[i]: _request_header_values[i] for i in range(len(_request_header_names))}
    del _obj['client_header_names'], _obj['client_header_values']
    request_header_raw = "{request_method} {request_url} {http_version}\r\n{request_headers}\r\n\r\n{request_body}\r\n".format(
        request_method=_obj['method'], request_url=_obj['uri'], http_version=_obj['version'],
        request_headers='\r\n'.join(["{k}:{v}".format(k=x[0], v=x[1]) for x in request_headers.items()]),
        request_body=request_body
    )
    # TODO :: Parse response_header
    _response_header_names = ["-".join([y.capitalize() for y in x.split('-')]) for x in _obj['server_header_names']]
    _response_header_values = _obj['server_header_values']
    response_headers = {_response_header_names[i]: _response_header_values[i] for i in range(len(_response_header_names))}
    del _obj['server_header_names'], _obj['server_header_values']
    response_header_raw = "{request_method} {request_url} {status_code}\r\n{response_headers}\r\n".format(
        request_method=_obj['method'],
        request_url=_obj['uri'],
        status_code=str(_obj['status_code']),
        response_headers='\r\n'.join(["{k}:{v}".format(k=x[0], v=x[1]) for x in request_headers.items()]),
    )
    local_add = dict(
        timestamp=timestamp,
        remote_ip=remote_ip,
        remote_port=remote_port,
        server_host=server_host,
        server_port=server_port,
        request_headers=request_headers,
        response_headers=response_headers,
        proxies=proxies,
        request_body=request_body,
        response_body=response_body,
        request_header_raw=request_header_raw,
        response_header_raw=response_header_raw
    )
    item = dict(_obj, **local_add)
    return item


if __name__ == '__main__':
    with open('./test_data/zeek_custom_http.log', "r",  encoding='utf-8') as f:
        lines = f.read().split('\n')
    for x in lines:
        if x:
            res = parse_zeek_http_custom_log_raw(x)
            # print(res)
            from kafka_helper import KafkaHelper
            KafkaHelper(topic='http_log').send(res)
