#!/bin/bash
socket=/run/lighttpd/jte.socket
rm $socket
kill -9 `cat /var/run/jte.pid`
kill -9 `cat /var/run/jte_delete_old.pid`

