#!/usr/bin/python
import numpy

class Color(object):
	lower_bound = 0
	upper_bound = 255
	def __init__(self, r, g, b, a):
		self.r = r
		self.g = g
		self.b = b
		self.a = a
	def __str__(self):
		return '(%s, %s, %s, %s)' % (self.r, self.g, self.b, self.a)
		
def composite_pixels(src, dest):
	new_color = Color(0,0,0,0)
	new_color.r = src.a * src.r * dest.a + src.r * (1 - dest.a) + dest.r * dest.a * (1 - src.a)
	new_color.g = src.a * src.g * dest.a + src.g * (1 - dest.a) + dest.g * dest.a * (1 - src.a)
	new_color.b = src.a * src.b * dest.a + src.b * (1 - dest.a) + dest.b * dest.a * (1 - src.a)
	new_color.a = src.a * dest.a + src.a * (1 - dest.a) + dest.a * (1 - src.a)
	return new_color
	
def simple_composite_pixels(src, dest):
	return Color(
		(src.r * src.a)/255 + ((dest.r * dest.a) * (255 - src.a))/255**2,
		(src.g * src.a)/255 + ((dest.g * dest.a) * (255 - src.a))/255**2,
		(src.b * src.a)/255 + ((dest.b * dest.a) * (255 - src.a))/255**2,
		src.a + dest.a - (src.a * dest.a)/255,
	)
	
def overlay_pixel(src, dest):
    a = numpy.array([
        (src[0] * src[3]) / 255 + ((dest[0] * dest[3]) * (255 - src[3])) / 255 ** 2,
        (src[1] * src[3]) / 255 + ((dest[1] * dest[3]) * (255 - src[3])) / 255 ** 2,
        (src[2] * src[3]) / 255 + ((dest[2] * dest[3]) * (255 - src[3])) / 255 ** 2,
        src[3] + dest[3] - (src[3] * dest[3]) / 255,
    ], dtype=numpy.uint8)
    print [
        (src[0] * src[3]) / 255 + ((dest[0] * dest[3]) * (255 - src[3])) / 255 ** 2,
        (src[1] * src[3]) / 255 + ((dest[1] * dest[3]) * (255 - src[3])) / 255 ** 2,
        (src[2] * src[3]) / 255 + ((dest[2] * dest[3]) * (255 - src[3])) / 255 ** 2,
        src[3] + dest[3] - (src[3] * dest[3]) / 255,
    ]
    print src, dest, a
    return a


if __name__ == '__main__':
	a = (120,120,120,255)
	b = (117,176,73,255)
	c = (134,96,67,255)
	d = (38,92,255,100)
	e = (0,0,0,0)

	print overlay_pixel(a,e)
	print (a[0] * a[3]) / 255 + ((e[0] * e[3]) * (255 - a[3])) / 255 ** 2