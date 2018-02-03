#!/bin/bash

GAMES_DIR="./games"
TIMEOUT=1800

mkdir -p "$GAMES_DIR"

while true; do
    for file in $GAMES_DIR/*; do
        [ -e $file ] || continue

        now=`date +"%s"`
        t=`stat -c "%Y" $file`
        diff=$(( now - t ))

        if [ "$diff" -gt "$TIMEOUT" ]; then
            rm $file
        fi
    done
    sleep 60
done
