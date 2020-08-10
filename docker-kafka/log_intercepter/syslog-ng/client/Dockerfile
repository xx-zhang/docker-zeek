FROM centos:7
MAINTAINER actanble <actanble@gmail.com>

ENV LANG en_US.UTF-8
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
RUN sed -i -e '/mirrors.cloud.aliyuncs.com/d' -e '/mirrors.aliyuncs.com/d' /etc/yum.repos.d/CentOS-Base.repo
RUN curl -o /etc/yum.repos.d/epel.repo http://mirrors.aliyun.com/repo/epel-7.repo
RUN yum makecache

ENV SYSLOG_NG_VERSION 3.28.1

RUN yum -y install gcc gcc-c++ make wget curl
RUN yum -y install epel-release
RUN yum -y install python36 python36-devel python36-pip
RUN yum -y install glib* json-c json-c-devel openssl openssl-devel curl curl-devel
WORKDIR /software/syslog-ng
VOLUME /software/xetl

ADD ./requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

RUN wget https://github.com/balabit/syslog-ng/releases/download/syslog-ng-${SYSLOG_NG_VERSION}/syslog-ng-${SYSLOG_NG_VERSION}.tar.gz && \
tar zxvf syslog-ng-${SYSLOG_NG_VERSION}.tar.gz
RUN cd syslog-ng-${SYSLOG_NG_VERSION} && ./configure --prefix=/software/syslog-ng \
--enable-python --with-python=3 --enable-http && make && make install

ENV KAFKA_SERVER "172.21.7.166:90"
ADD entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

