#!/usr/bin/python

import glob, os.path
import nbt
import Image, ImageDraw
import progressbar
import sys, logging, logging.handlers
import numpy, shmem
import multiprocessing

class LevelException(Exception):
    def __init__(self, err_msg):
        self.msg = err_msg
    def __str__(self):
        return self.msg

image_array_global = None

class Level(object):
    base_block_colors = dict({
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
    base_block_colors_n = numpy.array([base_block_colors.get(color, (255,255,255)) for color in range(255)], dtype=numpy.uint8)
    chunk_size_X = 16
    chunk_size_Z = 16
    chunk_size_Y = 128

    def __init__(self, level_file):
        self.level_file = level_file
        try:
            self.level_file = nbt.NBTFile(self.level_file, 'rb')
            #do something here to checkout the level file?
        except IOError, err:
            #should probably do something more worthwhile here
            raise err
        self.level_dir = os.path.dirname(level_file)
        self.chunk_files = glob.glob(os.path.join(self.level_dir, '*', '*', '*.dat'))
        self.chunk_files = sorted(
            sorted(
                glob.glob(os.path.join(self.level_dir, '*', '*', '*.dat')),
                key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36)
            ),
            key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36)
        )
        self.chunk_count = len(self.chunk_files)
        self.level_size = dict({
            'x_min':0,
            'x_max':0,
            'z_min':0,
            'z_max':0
        })
        chunks_xpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36), self.chunk_files)
        chunks_zpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36), self.chunk_files)
        self.level_size['x_min'] = min(chunks_xpos)
        self.level_size['x_max'] = max(chunks_xpos)
        self.level_size['z_min'] = min(chunks_zpos)
        self.level_size['z_max'] = max(chunks_zpos)

        print str(self)

    def __str__(self):
        return 'Name: %s, Chunks: %i, Size: %s' % (os.path.basename(self.level_dir), self.chunk_count, str(self.level_size))

def _init_multiprocess(array):
    global image_array_global
    image_array_global = array


def render_overhead_chunk((map_size, chunk_file)):
    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])
    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X + 1) * Level.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z + 1) * Level.chunk_size_Z)

    chunk = nbt.NBTFile(chunk_file, 'rb')

    chunk_pos_X = chunk['Level']['xPos'].value
    chunk_pos_Z = chunk['Level']['zPos'].value

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(16, 16, 128)
        tops = [z[z.nonzero()][-1] for x in blocks for z in x]
        colors = Level.base_block_colors_n[tops].reshape(16, 16, 3)

        global image_array_global
        image_array_global[(map_chunk_offset_Z+chunk_pos_Z)*16 : (map_chunk_offset_Z+chunk_pos_Z)*16+16,
                    (map_chunk_offset_X+chunk_pos_X)*16 : (map_chunk_offset_X+chunk_pos_X)*16+16] = colors.swapaxes(0, 1)
    except Exception, err:
        print 'Failed chunk %s: %s' % (str((chunk_pos_X, chunk_pos_Z)), err)

def init_mmap(map_image_size, default_color=(255,255,255)):
    image_array = shmem.create((map_image_size[1], map_image_size[0], 3), dtype=numpy.uint8)
    image_array[:] = default_color
    return image_array

render_modes = dict({
    'overhead':render_overhead_chunk
})

if __name__ == '__main__':
    import getopt, sys

    def main():
        short_options = 'o:r:v'
        long_options = ['output-file=', 'render-mode=', 'only-blocks=', 'processes=', 'verbose', 'use-alpha']
        options = dict({
            'level-file':None,
            'render-mode':'overhead',
            'output-file':'map.png',
            'verbose':False,
            'use-alpha':False,
            'processes':multiprocessing.cpu_count()
        })
        render_options = dict({})

        try:
            opts, args = getopt.gnu_getopt(sys.argv[1:], short_options, long_options)
            try:
                options['level-file'] = args[0]
            except IndexError:
                raise getopt.GetoptError('Missing level-file argument')
            for opt,arg in opts:
                if opt in ('-o', '--output-file'):
                    options['output-file'] = arg
                elif opt in ('-r', '--render-mode'):
                    if arg in render_modes:
                        options['render-mode'] = arg
                    else:
                        raise getopt.GetoptError('Invalid option (%s) argument (%s)' %
                            (opt, arg))
                elif opt in ('-v', '--verbose'):
                    options['verbose'] = True
                elif opt == '--use-alpha':
                    options['use-alpha'] = True
                elif opt == '--only-blocks':
                    render_options['selected-blocks'] = arg.split(',')
                elif opt == '--processes':
                    options['processes'] = max(int(arg), 1)
                else:
                    pass
        except getopt.GetoptError, error:
            print error
            usage()
            return None

        def _get_chunk_args(chunk_file):
            return (level.level_size, chunk_file)

        """
        def _init_multiprocess(array):
            global image_array
            image_array = array
        """

        print 'Options; %s' % options
        level = Level(level_file=options['level-file'])
        map_image_size = ((abs(level.level_size['x_max']) + abs(level.level_size['x_min']) + 1) * Level.chunk_size_X, (abs(level.level_size['z_max']) + abs(level.level_size['z_min']) + 1) * Level.chunk_size_Z)
        #image_array = init_mmap(map_image_size)
        image_array = shmem.create((map_image_size[1], map_image_size[0], 3), dtype=numpy.uint8)
        image_array[:] = (255,255,255)

        pool = multiprocessing.Pool(options['processes'], _init_multiprocess, (image_array,))
        pool.map(render_modes[options['render-mode']], map(_get_chunk_args, level.chunk_files), level.chunk_count/options['processes'])
        try:
            Image.fromarray(image_array).save(options['output-file'])
        except:
            print 'Failed to save image'

    def usage():
        print """%s: [options] path/to/world/level.dat
    General Options:
        -o|--output-file <filename>
            The filename of the resulting image. Should end with ".png"
            default: map.png
        -r|--render-mode <%s>
            The method for rendering the map image, currently only supports "overview"
            default: overview
        -v|--verbose
            Output progress and other messages
            default: off (quiet)
        --processes <count>
            Set the number of render processes
            default: # of cpu cores
        --use-alpha
            *NYI* Use transparency for nicer looking maps
            default: no alpha channel
    Render Options:
        *blocks*:
            --only-blocks <block[,block[,block]]>
                Comma separated list of (dec) block ids to render
            --overlayed
                *NYI* Overlay onto overhead map""" % \
        (sys.argv[0], render_modes.keys())
    main()