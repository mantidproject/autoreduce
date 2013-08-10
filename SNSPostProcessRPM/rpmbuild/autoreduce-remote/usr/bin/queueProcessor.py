#!/usr/bin/env python
"""
Post Process master
"""

from PostProcessQueueHandler import PostProcessQueueHandler
from PostProcessQueueConnector import PostProcessQueueConnector
from Configuration import Configuration

if __name__ == "__main__":
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    ppQConnector = PostProcessQueueConnector(conf.brokers, conf.amq_user, conf.amq_pwd, conf.queues, "post_process_consumer")
    ppQConnector.set_listener(PostProcessQueueHandler())
    ppQConnector.listen_and_wait(0.1)