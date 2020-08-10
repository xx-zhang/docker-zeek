#!/usr/bin/env bash

echo "add python-path>>>>>>>>>>>>>>"
export PYTHONPATH=$PYTHONPATH:/software/xetl

echo "Start syslog-ng ...>>>>>>>>>>>>>>>>>>"
/software/syslog-ng/sbin/syslog-ng -F

