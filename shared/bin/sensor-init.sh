#!/bin/bash

# Copyright (c) 2020 Battelle Energy Alliance, LLC.  All rights reserved.

SCRIPT_PATH="$(dirname $(realpath -e "${BASH_SOURCE[0]}"))"

echo "sensor" > /etc/installer

MAIN_USER="$(id -nu 1000)"

if [[ -r "$SCRIPT_PATH"/common-init.sh ]]; then
  . "$SCRIPT_PATH"/common-init.sh

  # remove default accounts/groups we don't want, create/set directories for non-user users for stig to not complain
  CleanDefaultAccounts

  # get a list of the hardware interfaces
  PopulateInterfaces

  # set up some sensor-specific stuff
  if [[ -d /opt/sensor ]]; then

    # set ownership for /opt/sensor files for sensor UID:GID
    chown -R 1000:1000 /opt/sensor
    find /opt/sensor/ -type d -exec chmod 750 "{}" \;
    find /opt/sensor/ -type f -exec chmod 640 "{}" \;
    find /opt/sensor/ -type f -name "*.sh" -exec chmod 750 "{}" \;
    find /opt/sensor/ -type f -name "*.keystore" -exec chmod 600 "{}" \;

    if [[ -f /opt/sensor/sensor_ctl/control_vars.conf ]]; then
      # if the capture interface hasn't been set in control_vars.conf, set it now
      if grep --quiet CAPTURE_INTERFACE=xxxx /opt/sensor/sensor_ctl/control_vars.conf; then
        CAP_IFACE="$(DetermineCaptureInterface)"
        if [[ -n "${CAP_IFACE}" ]]; then
          sed -i "s/CAPTURE_INTERFACE=xxxx/CAPTURE_INTERFACE=${CAP_IFACE}/g" /opt/sensor/sensor_ctl/control_vars.conf
        fi
      fi
      chmod 600 /opt/sensor/sensor_ctl/control_vars.conf*
    fi

    [[ -d /opt/sensor/sensor_ctl/moloch/config.ini ]] && chmod 600 /opt/sensor/sensor_ctl/moloch/config.ini

  fi

  # zeekctl won't like being run by a non-root user unless the whole stupid thing is owned by the non-root user
  if [[ -d /opt/zeek.orig ]]; then
    # as such, we're going to reset zeek to a "clean" state after each reboot. the config files will get
    # regenerated when we are about to deploy zeek itself
    [[ -d /opt/zeek ]] && rm -rf /opt/zeek
    rsync -a /opt/zeek.orig/ /opt/zeek
  fi
  if [[ -d /opt/zeek ]]; then
    chown -R 1000:1000 /opt/zeek/*
    [[ -f /opt/zeek/bin/zeek ]] && setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /opt/zeek/bin/zeek
  fi

  # if the sensor needs to do clamav scanning, configure it to run as the sensor user
  if dpkg -s clamav >/dev/null 2>&1 ; then
    mkdir -p /var/log/clamav /var/lib/clamav
    chown -R 1000:1000 /var/log/clamav  /var/lib/clamav
    chmod -R 750 /var/log/clamav  /var/lib/clamav
    sed -i 's/^Foreground .*$/Foreground true/g' /etc/clamav/freshclam.conf
    sed -i 's/^Foreground .*$/Foreground true/g' /etc/clamav/clamd.conf
    if [[ -d /opt/sensor/sensor_ctl ]]; then
      # disable clamd/freshclam logfiles as supervisord will handle the logging from STDOUT instead
      sed -i 's@^UpdateLogFile .*$@#UpdateLogFile /var/log/clamav/freshclam.log@g' /etc/clamav/freshclam.conf
      sed -i 's@^LogFile .*$@#LogFile /var/log/clamav/clamd.log@g' /etc/clamav/clamd.conf
      # use local directory for socket file
      mkdir -p /opt/sensor/sensor_ctl/clamav
      chown -R 1000:1000 /opt/sensor/sensor_ctl/clamav
      chmod -R 750 /opt/sensor/sensor_ctl/clamav
      sed -i 's@^LocalSocket .*$@LocalSocket /opt/sensor/sensor_ctl/clamav/clamd.ctl@g' /etc/clamav/clamd.conf
    fi
    if [[ -n $MAIN_USER ]]; then
      sed -i "s/^User .*$/User $MAIN_USER/g" /etc/clamav/clamd.conf
      sed -i "s/^LocalSocketGroup .*$/LocalSocketGroup $MAIN_USER/g" /etc/clamav/clamd.conf
      sed -i "s/^DatabaseOwner .*$/DatabaseOwner $MAIN_USER/g" /etc/clamav/freshclam.conf
    fi
    [[ -r /opt/sensor/sensor_ctl/control_vars.conf ]] && source /opt/sensor/sensor_ctl/control_vars.conf
    [[ -z $EXTRACTED_FILE_MAX_BYTES ]] && EXTRACTED_FILE_MAX_BYTES=134217728
    sed -i "s/^MaxFileSize .*$/MaxFileSize $EXTRACTED_FILE_MAX_BYTES/g" /etc/clamav/clamd.conf
    sed -i "s/^MaxScanSize .*$/MaxScanSize $(echo "$EXTRACTED_FILE_MAX_BYTES * 4" | bc)/g" /etc/clamav/clamd.conf
    grep -q "^TCPSocket" /etc/clamav/clamd.conf && (sed -i 's/^TCPSocket .*$/TCPSocket 3310/g' /etc/clamav/clamd.conf) || (echo "TCPSocket 3310" >> /etc/clamav/clamd.conf)
  fi

  # if the network configuration files for the interfaces haven't been set to come up on boot, configure that now.
  InitializeSensorNetworking

  # fix some permisions to make sure things belong to the right person
  [[ -n $MAIN_USER ]] && FixPermissions "$MAIN_USER"

  # chromium tries to call home despite my best efforts
  BadGoogle

  exit 0
else
  exit 1
fi

