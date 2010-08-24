#!/usr/bin/python

import time

a = time.clock()
b = time.time()

time.sleep(5)

print 'clock: %s' % (time.clock() - a)
print 'time: %s' % (time.time() - b)
