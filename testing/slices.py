#!/usr/bin/python
import numpy
import nbt

blocks = numpy.fromstring(nbt.NBTFile('/home/aheadley/.minecraft/saves/World1/0/0/c.0.0.dat','rb')['Level']['Blocks'].value, dtype=numpy.uint8).reshape(16,16,128)

print blocks
