#!/usr/bin/python

import multiprocessing
import nbt
import glob, os.path, sys
import time


def f(x, count):
	return

def test():
	map_files = glob.glob(os.path.join(sys.argv[1], '*', '*', '*.dat'))
	print 'File count: %i' % len(map_files)
	pool = multiprocessing.Pool()
	return pool.map(f, range(256), int(len(map_files)/multiprocessing.cpu_count())).get()

if __name__ == '__main__':
	start = time.time()
	x_pos = test()
	print 'Time: %.3f' % (time.time() - start)
	print min(x_pos), max(x_pos)
	
