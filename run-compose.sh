#!/bin/sh

HOST=ec2-52-90-158-238.compute-1.amazonaws.com
DASHBOARD_URL="http://ec2-52-90-158-238.compute-1.amazonaws.com:3000/dashboard/db/ndn-rtc-test-metrics"

if [ "$#" -ne 2 ]; then
	echo "Usage: $0 <number_of_tests> <test_group>"
	exit 1
fi

if [ -z "$RUNTIME"  ] ; then
	echo "RUNTIME variable is not set"
	exit 1
fi

if [ -z "$TAGS"  ] ; then
	echo "TAGS variable is not set"
	exit 1
fi

NTESTS=$1
TEST_GROUP=$2

now=$(date)
tmp=${now// /_}
groupid=${tmp//:/_}

echo "" >> results.txt
echo "*** new run at $(date)" >> results.txt
echo "" >> results.txt

for i in `seq 1 $NTESTS`; do
	TAGS="test-group=$TEST_GROUP,test=test${i},group-id=$TEST_GROUP-$groupid"
	
	echo "Test run ${i}"
	echo "Run time $RUNTIME sec, tags $TAGS"

	START="$(date +%s)000"
	echo "Building topology..."
	docker-compose up -d --force-recreate --build
	docker-compose ps
	echo "Running test..."
	sleep $RUNTIME
	END="$(date +%s)000"
	
	echo ""
	echo "****"
	echo "Test ${i} results at $DASHBOARD_URL?from=$START&to=$END (or results.txt)"
	echo "***"

	echo "group ${TEST_GROUP} test ${i}\t$DASHBOARD_URL?from=$START&to=$END" >> results.txt
	
	echo "Cleaning after test${i}..."
	docker-compose down
	echo "Arbitrary pause..."
	sleep 20
done