@load ../__load__

module RequestBody;

const host_url: set[string, string] = {
    ["www.google.com", "/product/product/real_time_prices"],
    ["www.baidu.com", "/product/product/real_time_prices"],
};

hook RequestBody::include(hostname: string, url: string) &priority = 5
    {
    url = split_string(url, /\?/)[0];

    if ( [hostname, url] in host_url )
        break;
    }
