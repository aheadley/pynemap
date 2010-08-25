#!/usr/bin/python

import glob
import os.path
import nbt
import Image
import numpy
import multiprocessing
import time
import shmem


mmap_array = None


class Mapper(object):
    block_colors = dict({
        1:(120,120,120),
        2:(117,176,73),
        3:(134,96,67),
        4:(115,115,115),
        5:(157,128,79),
        6:(120,120,120),
        7:(84,84,84),
        8:(0,0,255),
        9:(0,0,255),
        10:(255,90,0),
        11:(255,90,0),
        12:(228,228,149),
        13:(136,126,126),
        14:(143,140,125),
        15:(136,130,127),
        16:(115,115,115),
        17:(102,81,51),
        18:(0,255,0),
        20:(255,255,255),
        35:(222,222,222),
        38:(255,0,0),
        37:(255,255,0),
        41:(231,165,45),
        42:(191,191,191),
        43:(200,200,200),
        44:(200,200,200),
        45:(170,86,62),
        46:(160,83,65),
        49:(26,11,43),
        50:(245,220,50),
        51:(255,170,30),
        52:(245,220,50),
        53:(157,128,79),
        54:(125,91,38),
        55:(245,220,50),
        56:(129,140,143),
        57:(45,166,152),
        58:(114,88,56),
        59:(146,192,0),
        60:(95,58,30),
        61:(96,96,96),
        62:(96,96,96),
        63:(111,91,54),
        64:(136,109,67),
        65:(181,140,64),
        66:(150,134,102),
        67:(115,115,115),
        71:(191,191,191),
        73:(131,107,107),
        74:(131,107,107),
        75:(181,140,64),
        76:(255,0,0),
        78:(255,255,255),
        79:(83,113,163),
        80:(250,250,250),
        81:(25,120,25),
        82:(151,157,169),
        83:(193,234,150),
        83:(100,67,50)
    })

    chunk_size_X = 16
    chunk_size_Y = 128
    chunk_size_Z = 16


def init_multiprocess(array):
    global mmap_array
    mmap_array = array


def render_chunk((map_size, chunk_file)):
    chunk_setup = time.clock()

    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])
    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X + 16, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z + 16)

    block_colors = numpy.array([Mapper.block_colors.get(color, (255,255,255)) for color in xrange(255)], dtype=numpy.uint8)
    chunk = nbt.NBTFile(chunk_file, 'rb')

    chunk_pos_X = chunk['Level']['xPos'].value
    chunk_pos_Z = chunk['Level']['zPos'].value
    chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
    chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z

    end_chunk_setup = time.clock()

    chunk_render = time.clock()
    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(16, 16, 128)
        tops = [z[z.nonzero()][-1] for x in blocks for z in x]
        colors = block_colors[tops].reshape(16, 16, 3)

        global mmap_array
        mmap_array[(map_chunk_offset_Z+chunk_pos_Z)*16 : (map_chunk_offset_Z+chunk_pos_Z)*16+16,
                   (map_chunk_offset_X+chunk_pos_X)*16 : (map_chunk_offset_X+chunk_pos_X)*16+16] = colors.swapaxes(0, 1)
    except:
        pass

    end_chunk_render = time.clock()

    return (end_chunk_setup - chunk_setup, end_chunk_render - chunk_render)


if __name__ == '__main__':
    start = time.clock()

    setup = time.clock()

    # setup

    #chunk_files = glob.glob(os.path.join('ArsSMP1', '*', '*', '*.dat'))
    chunk_files = glob.glob(os.path.join('testworld', '*', '*', '*.dat'))

    # map size
    chunks_xpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36), chunk_files)
    chunks_zpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36), chunk_files)

    map_size = {'x_min': min(chunks_xpos), 'x_max': max(chunks_xpos),
                'z_min': min(chunks_zpos), 'z_max': max(chunks_zpos)}

    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])

    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X + 16, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z + 16)

    init_array = time.clock()

    image_array = shmem.create((map_image_size[1], map_image_size[0], 3), dtype=numpy.uint8)
    image_array[:] = (255, 255, 255)

    end_init_array = time.clock()

    pool = multiprocessing.Pool(multiprocessing.cpu_count()*2, init_multiprocess, (image_array,))

    end_setup = time.clock()

    render = time.clock()

    # multi cpu render
    print 'go', len(chunk_files), map_image_size
    def create_data(file):
        return (map_size, file)

    times = pool.map(render_chunk, map(create_data, chunk_files))

    end_render = time.clock()

    save_image = time.clock()

    # save image
    Image.fromarray(image_array).save('map.png')

    end_save_image = time.clock()

    end = time.clock()

    # print some stats
    chunk_setup_times = map(lambda x: x[0], times)
    chunk_render_times = map(lambda x: x[1], times)

    print 'Setup: %.5fs' % (end_setup - setup)
    print 'Init array: %.5fs' % (end_init_array - init_array)
    print 'Render: %.5fs' % (end_render - render)
    print '\tAverage chunk setup: %.5fs' % numpy.average(chunk_setup_times)
    print '\tAverage chunk render: %.5fs' % numpy.average(chunk_render_times)
    print 'Save image: %.5fs' % (end_save_image - save_image)
    print 'Total: %.5fs' % (end - start)
