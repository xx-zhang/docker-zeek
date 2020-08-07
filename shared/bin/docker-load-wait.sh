#!/bin/bash

# Copyright (c) 2020 Battelle Energy Alliance, LLC.  All rights reserved.

function finish {
  pkill -f "zenity.*Preparing Malcolm"
}

if [[ -f /malcolm_images.tar.gz ]] || pgrep -f "docker load" >/dev/null 2>&1 || pgrep -f "docker-untar" >/dev/null 2>&1; then
  trap finish EXIT
  yes | zenity --progress --pulsate --no-cancel --auto-close --text "Malcolm Docker images are loading, please wait..." --title "Preparing Malcolm" &
  while [[ -f /malcolm_images.tar.gz ]] || pgrep -f "docker load" >/dev/null 2>&1 || pgrep -f "docker-untar" >/dev/null 2>&1; do
    sleep 2
  done
fi
