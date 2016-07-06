#!/bin/sh
# runas: docker exec client2 /root/headless/runtest.sh client2 client1 /root/headless/config/test.cfg 30 /tmp

ME=$1
HUB=$2
CONFIG=$3
TIME=$4
TAGS=$5

STATPATH="/tmp"
HOST=ec2-52-90-158-238.compute-1.amazonaws.com
DASHBOARD_URL="http://ec2-52-90-158-238.compute-1.amazonaws.com:3000/dashboard/db/ndn-rtc-test-metrics"
CAPTURED_METRICS="jitterPlay,jitterEst,jitterTar,dArr,framesAcq,framesResc,framesRec,framesDrop,skipNoKey,skipInc,skipBadGop,lambdaD,drdEst,drdPrime,rebuf,rawBytesRcvd,latEst,framesReq,framesPlayed,framesInc,skipBadGop,isent,segNumRcvd,timeouts,rtxNum"

if [ "$#" -ne 5 ]; then
    echo "    Usage: $0 <consumer_name> <hub_name> <config_file> <run_time> <tags>"
    exit 1
fi

echo "Client $ME connects to hub $HUB. "
echo "Headless app config at $CONFIG, runtime $TIME seconds"
echo "Gathering statistics from $STATPATH"

START=$(date +%s%N | cut -b1-13)

rm -f /run/nfd.sock
nfd-start && sleep 3 && nfd-status && nfdc register / udp://$HUB

cmd="ingest.py --iface=eth0 --username=$ME --stat-folder=$STATPATH --influx-adaptor --host=$HOST --tags=$TAGS --iuser=ingest --ipassword=1ng3st --metrics=$CAPTURED_METRICS"
echo "invoking ingest script: $cmd"

ingest.py --iface=eth0 --username=$ME --stat-folder=$STATPATH --influx-adaptor --host=$HOST --tags=$TAGS --iuser=ingest --ipassword=1ng3st --metrics=$CAPTURED_METRICS &


ndnrtc-client -c $CONFIG -t $TIME
killall "python"
nfd-stop
# nfd-status -f | grep udp4://10.10.12.2:6363 > /tmp/$ME-nfd-status

END=$(date +%s%N | cut -b1-13)

echo ""
echo "****"
echo "See results at $DASHBOARD_URL?from=$START&to=$END"
echo "***"

# sleep 9000