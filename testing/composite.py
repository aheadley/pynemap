#!/usr/bin/python

class Color(object):
	lower_bound = 0
	upper_bound = 255
	def __init__(self, r, g, b, a):
		self.r = float(r)/self.upper_bound
		self.g = float(g)/self.upper_bound
		self.b = float(b)/self.upper_bound
		self.a = float(a)/self.upper_bound
	def __str__(self):
		return str((int(self.r*self.upper_bound),int(self.g*self.upper_bound),int(self.b*self.upper_bound),int(self.a*self.upper_bound)))
		
def composite_pixels(src, dest):
	new_color = Color(0,0,0,0)
	new_color.r = src.a * src.r * dest.a + src.r * (1 - dest.a) + dest.r * dest.a * (1 - src.a)
	new_color.g = src.a * src.g * dest.a + src.g * (1 - dest.a) + dest.g * dest.a * (1 - src.a)
	new_color.b = src.a * src.b * dest.a + src.b * (1 - dest.a) + dest.b * dest.a * (1 - src.a)
	new_color.a = src.a * dest.a + src.a * (1 - dest.a) + dest.a * (1 - src.a)
	return new_color
	
def simple_composite_pixels(src, dest):
	new_color = Color(0,0,0,0)
	new_color.r = (src.r * src.a) + (dest.r * dest.a) * (1 - src.a)
	new_color.r = (src.g * src.a) + (dest.g * dest.a) * (1 - src.a)
	new_color.r = (src.b * src.a) + (dest.b * dest.a) * (1 - src.a)
	new_color.a = src.a + dest.a - src.a * dest.a
	return new_color

if __name__ == '__main__':
	over = Color(255,0,0,128)
	under = Color(0,255,0,255)
	first = composite_pixels(over,under)
	print 'first: %s' % first
	print 'second: %s' % composite_pixels(over,first)
