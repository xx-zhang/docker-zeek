#!/bin/bash

# Copyright (c) 2020 Battelle Energy Alliance, LLC.  All rights reserved.

function finish {
  pkill -f "zenity.*Preparing Storage"
}

if [ -f /etc/capture_storage_format.crypt ]; then
  CAPTURE_STORAGE_FORMAT_FILE="/etc/capture_storage_format.crypt"
else
  CAPTURE_STORAGE_FORMAT_FILE="/etc/capture_storage_format"
fi

if [[ -f "$CAPTURE_STORAGE_FORMAT_FILE" ]] || pgrep -f "sensor-capture-disk-config.py" >/dev/null 2>&1; then
  trap finish EXIT
  yes | zenity --progress --pulsate --no-cancel --auto-close --text "Capture storage media are being prepared..." --title "Preparing Storage" &
  while [[ -f "$CAPTURE_STORAGE_FORMAT_FILE" ]] || pgrep -f "sensor-capture-disk-config.py" >/dev/null 2>&1; do
    sleep 2
  done
fi
