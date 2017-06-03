#!/bin/bash
socket=/run/lighttpd/jte.socket
python site.fcgi $socket &
echo $! > /var/run/jte.pid
sleep 3
chown www-data:www-data $socket

./delete_old.sh &
echo $! > /var/run/jte_delete_old.pid
