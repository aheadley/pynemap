#!/usr/bin/env python
# encoding: utf-8
"""
topography.py

Created by Stephen Altamirano on 2010-09-20.
"""

import numpy

def _topographic_values(k):
    if k == 8 or k == 9:
        k = -1
    elif k > 0:
        k = 1
    return k

def _hypsometric(k):
    result = [0, 0, 0, 255]
    if k > 63:
        result[0] = 255
        result[1] = 255 - (k - 64) * 4
    else:
        result[1] = 255
        result[0] = k * 4

    return numpy.array(result)


translator = numpy.array([_topographic_values(n) for n in xrange(255)])
topographic_colors = numpy.array(
    [(255, 255, 255, 0), (0, 0, 255, 30)] +
    [_hypsometric(n) for n in xrange(128)]
)
