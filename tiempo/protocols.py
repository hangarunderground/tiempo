# from twisted.internet import protocol
# from twisted.internet import reactor
# import re
#
# class TiempoProcessProtocol(protocol.ProcessProtocol):
#
#     def connectionMade(self):
#         print "starting tiempo process"
#
#     def outReceived(self, data):
#         print data
#
#     def errReceived(self, data):
#         print 'error/warning from tiempo process:', data
#
#     def inConnectionLost(self):
#         print "tiempo process (probably) killed by ctrl-c"
#
#     def outConnectionLost(self):
#         print "lost tiempo process connection"
#
#     def processEnded(self, reason):
#         print "tiempo processEnded, status %d" % (reason.value.exitCode,)
