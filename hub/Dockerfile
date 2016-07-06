FROM peetonn/docker-ndnrtc-ubuntu14.04:latest
MAINTAINER Peter Gusev

ADD runtest.sh /root/headless/
RUN chmod +x /root/headless/runtest.sh

CMD ["/root/headless/runtest.sh", "hub", "5", "300"]