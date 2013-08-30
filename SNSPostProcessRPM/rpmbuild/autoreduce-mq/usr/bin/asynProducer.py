
import json
import logging

from twisted.internet import defer, reactor

from stompest.config import StompConfig

from stompest.async import Stomp
from stompest.async.listener import ReceiptListener

class Producer(object):

    def __init__(self, config=None):
        if config is None:
            config = StompConfig('tcp://localhost:61613')
        self.config = config

    @defer.inlineCallbacks
    def run(self, queue, data):
        client = yield Stomp(self.config).connect()
        client.add(ReceiptListener(1.0))
        yield client.send(queue, json.dumps(data), receipt='message-%s' % data)
        
        client.disconnect(receipt='bye')
        yield client.disconnected # graceful disconnect: waits until all receipts have arrived
        reactor.stop()

if __name__ == '__main__':
    Producer().run()
    reactor.run()
