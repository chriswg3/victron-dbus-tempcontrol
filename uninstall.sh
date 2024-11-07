#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )
DAEMON_NAME=${SCRIPT_DIR##*/}

rm /service/$DAEMON_NAME
kill $(pgrep -f "supervise $DAEMON_NAME")
kill $(pgrep -f "python $SCRIPT_DIR/dbus-tempcontrol.py")
chmod a-x $SCRIPT_DIR/service/run
sed -i "s/\/data\/$DAEMON_NAME\/install.sh//" /data/rc.local
