#!/bin/bash
# runas: docker exec client2 /root/headless/runtest.sh client2 client1 /root/headless/config/test.cfg 30 /tmp

ME=$1
CLIENTS=$2
TIME=$3
TAGS=$4

HOST=ec2-52-90-158-238.compute-1.amazonaws.com

let() {
    IFS=, command eval test '$(($*))' -ne 0
}

echo "Hub $ME starts. Connects to ${NCLIENTS} clients"

rm -f /run/nfd.sock
# sleep for 15 seconds - allow for other containers to be configured
nfd-start && sleep 15

BASE_PREFIX="/ndn/edu/ucla/remap/ndnrtc/user"

for client in $CLIENTS; do
	if [[ $client == *"producer"* ]]; then
		echo "register ${BASE_PREFIX}/$client ==> "$client
		nfdc register "${BASE_PREFIX}/$client" udp://$client || true
	else
		echo "register ${BASE_PREFIX} ==> "$client
		nfdc register "${BASE_PREFIX}" udp://$client
	fi
done;

nfd-status
ingest.py --iface=eth0 --username=$ME --no-ndncon --influx-adaptor --host=$HOST --tags=$TAGS --iuser=ingest --ipassword=1ng3st &

echo "sleep for $TIME seconds..."
sleep $TIME
echo "shut down $ME"

# tcpdumping: tcpdump -ni eth0 -s0 -w /var/tmp/capture.pcap
# nfd-status -fr > /tmp/$ME-nfd-status
# sleep 9000
