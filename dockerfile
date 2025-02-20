FROM ctfd/ctfd 

USER root

COPY docker_challenges /opt/CTFd/CTFd/plugins/docker_challenges

USER 1001