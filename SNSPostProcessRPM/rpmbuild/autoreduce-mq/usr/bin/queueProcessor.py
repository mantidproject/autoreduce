#!/usr/bin/env python
"""
Post Process including autoreduce and cataloging after a nexus file is created.
"""
import os, sys, subprocess, psutil, time

from PostProcessQueueHandler import PostProcessQueueHandler
from PostProcessQueueConnector import PostProcessQueueConnector
from Configuration import Configuration

if __name__ == "__main__":
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    ppQHandler = PostProcessQueueHandler(conf)
    ppQConnector = PostProcessQueueConnector(conf.brokers, conf.amq_user, conf.amq_pwd, conf.queues, "post_process_consumer")
    ppQConnector.set_listener(ppQHandler)
    ppQConnector.listen_and_wait(0.1)