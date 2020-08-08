@load ../__load__

module RequestBody;

hook RequestBody::include(hostname: string, url: string) &priority = 10
    {
    break;
    }
