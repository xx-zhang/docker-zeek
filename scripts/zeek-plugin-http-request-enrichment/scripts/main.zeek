module RequestBody;

export {
    ## Hook to include http request body
    global include: hook(hostname: string, url: string);
    
    ## Hook to exclude http request body
    global exclude: hook(hostname: string, url: string);
}

@load base/protocols/http/main

module HTTP;

export {
    ## The length of POST bodies to extract.
    const http_post_body_length = 200 &redef;
}

redef record HTTP::Info += {
    request_body: string &log &optional;
};

event log_post_bodies(f: fa_file, data: string)
    {
    for ( cid in f$conns )
        {
        local c: connection = f$conns[cid];
        if ( ! c$http?$request_body )
            c$http$request_body = "";
        # If we are already above the captured size here, just return.
        if ( |c$http$request_body| > http_post_body_length )
            return;
        c$http$request_body = c$http$request_body + data;
        if ( |c$http$request_body| > http_post_body_length )
            {
            c$http$request_body = c$http$request_body[0:http_post_body_length] + "...";
            }
        }
    }

event file_over_new_connection(f: fa_file, c: connection, is_orig: bool)
    {
    if ( (! c?$http) || (! c$http?$host) || (! c$http?$method) || (! c$http?$uri) )
        return;

    if ( ! hook RequestBody::exclude(c$http$host, c$http$uri) )
        return;

    if ( hook RequestBody::include(c$http$host, c$http$uri) )
        return;

    if ( is_orig && c$http$method == "POST" )
        {
        Files::add_analyzer(f, Files::ANALYZER_DATA_EVENT, [$stream_event=log_post_bodies]);
        }
    }
