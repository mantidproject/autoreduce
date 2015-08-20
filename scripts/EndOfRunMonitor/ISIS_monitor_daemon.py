from daemon import Daemon
import sys, time
import ISISendOfRunMonitor


class InstrumentMonitorDaemon(Daemon):
    def run(self):
        ISISendOfRunMonitor.main()

if __name__ == "__main__":
    daemon = InstrumentMonitorDaemon('/tmp/InstrumentMonitorDaemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)