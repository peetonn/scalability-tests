#!/bin/bash
# runas: docker exec client2 /root/headless/runtest.sh client2 client1 /root/headless/config/test.cfg 30 /tmp

ME=$1
NCLIENTS=$2
TIME=$3
TAGS=$4

HOST=ec2-52-90-158-238.compute-1.amazonaws.com

let() {
    IFS=, command eval test '$(($*))' -ne 0
}

echo "Hub $ME starts. Connects to ${NCLIENTS} clients"

rm -f /run/nfd.sock
nfd-start && sleep 3 && nfd-status

COUNTER=1
while [ $COUNTER -le $NCLIENTS ]; do
	echo "register prefix towards client${COUNTER}..."
	nfdc register /ndn/edu/ucla/remap/ndnrtc/user/client${COUNTER} udp://client${COUNTER} || true
	let COUNTER=COUNTER+1
done

ingest.py --username=$ME --no-ndncon --influx-adaptor --host=$HOST --tags=$TAGS --iuser=ingest --ipassword=1ng3st &

echo "sleep for $TIME seconds..."
sleep $TIME
echo "shut down $ME"

# nfd-status -fr > /tmp/$ME-nfd-status
# sleep 9000
