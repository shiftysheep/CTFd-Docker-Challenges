FROM ctfd/ctfd 

COPY docker_challenges /opt/CTFd/CTFd/plugins/docker_challenges
COPY wrong_flag_submissions /opt/CTFd/CTFd/plugins/wrong_flag_submissions