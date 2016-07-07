#!/bin/bash

HEADER_BLOCK="version: '2'
services:"

CONSUMER_BLOCK='  CONSUMERID:
    build:
      context: client
      dockerfile: Dockerfile-consumer
    command: ["/root/headless/runtest.sh", CLIENTNAME, HUBID, "/root/headless/config/test.cfg", $RUNTIME, $TAGS]
    container_name: CLIENTNAME
    depends_on:
     - HUBID
     - PRODUCERID
    networks:
     - local-testbed'

PRODUCER_BLOCK='  PRODUCERID:
    build: 
      context: client
      dockerfile: Dockerfile-producer
    container_name: CLIENTNAME
    command: ["/root/headless/runtest.sh", CLIENTNAME, HUBID, "/root/headless/config/test.cfg", $RUNTIME, $TAGS]
    depends_on:
     - HUBID
    networks:
     - local-testbed'

HUB_BLOCK='  HUBID:
    build: hub
    container_name: HUBID
    command: ["/root/headless/runtest.sh", HUBID, "NCLIENTS", $RUNTIME, $TAGS]
    networks:
     - local-testbed'

FOOTER_BLOCK='networks:
  default:
    ipam:
      config:
       - subnet: 10.10.11.0/24
  local-testbed:
    driver: overlay
    ipam:
      config:
       - subnet: 10.10.12.0/24'

function usage {
	echo "usage: $0 <number of consumers>"
	exit 1
}

function printFormatted {
	IFS='%'
	echo $1
	unset IFS
}

function printConsumers {
	nclients=$1
  hubid=$2
  producerid=$3
	for i in `seq 2 $nclients`; do
		let ci=i-1
		str=${CONSUMER_BLOCK//CLIENTNAME/client${i}}
		str=${str//CONSUMERID/consumer${ci}}
    str=${str//HUBID/$hubid}
    str=${str//PRODUCERID/$producerid}
		printFormatted "$str"
	done;
}

function printProducers {
	nproducers=$1
  hubid=$2
	for i in `seq 1 $nproducers`; do
		str=${PRODUCER_BLOCK//CLIENTNAME/client${i}}
		str=${str//PRODUCERID/producer${i}}
    str=${str//HUBID/$hubid}
		printFormatted "$str"
	done;
}

function printHubs {
	nhubs=$1
	nclients=$2
	for i in `seq 1 $nhubs`; do
		str=${HUB_BLOCK//NCLIENTS/$nclients}
		str=${str//HUBID/hub${i}}
		printFormatted "$str"
	done;
}

if [ $# -ne 1 ]; then 
	usage
else
	NCONSUMERS=$1
fi

let NCLIENTS=NCONSUMERS+1

# echo "generating docker-compose.yml for ${NCONSUMERS} consumers..."

printFormatted "$HEADER_BLOCK"
printConsumers $NCLIENTS hub1 producer1
printProducers 1 hub1
printHubs 1 $NCLIENTS
printFormatted "$FOOTER_BLOCK"
