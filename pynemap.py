#!/usr/bin/python

import glob, os
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

class Level(object):
    base_block_colors = dict({
        0:(255,255,255,0),          #air
        1:(120,120,120,255),        #stone
        2:(117,176,73,255),         #grass
        3:(134,96,67,255),          #dirt
        4:(115,115,115,255),        #cobblestone
        5:(157,128,79,255),         #wood (planks)
        6:(120,120,120,0),          #sapling
        7:(84,84,84,255),           #adminium
        8:(38,92,255,51),           #water (flowing?)
        9:(38,92,255,51),           #water (source)
        10:(255,90,0,255),          #lava (flowing?)
        11:(255,90,0,255),          #lava (source)
        12:(218,210,158,255),       #sand
        13:(136,126,126,255),       #gravel
        14:(143,140,125,255),       #gold ore
        15:(136,130,127,255),       #iron ore
        16:(115,115,115,255),       #coal ore
        17:(102,81,51,255),         #log
        18:(60,192,41,100),         #leaves
        19:(247,232,43,255),        #sponge
        20:(255,255,255,64),        #glass
        21:(207,24,24,255),         #red cloth
        22:(234,140,15,255),        #orange cloth
        23:(242,231,6,255),         #yellow cloth
        24:(45,204,101,255),        #lime cloth
        25:(68,194,54,255),         #green cloth
        26:(94,208,191,255),        #aqua cloth
        27:(111,149,251,255),       #cyan cloth
        28:(61,45,255,255),         #blue cloth
        29:(167,41,250,255),        #purple cloth
        30:(122,112,250,255),       #indigo cloth
        31:(193,51,240,255),        #violet cloth
        32:(249,43,162,255),        #magenta cloth
        33:(255,106,252,255),       #pink cloth
        34:(0,0,0,255),             #black cloth
        35:(222,222,222,255),       #white cloth
        36:(222,222,222,255),       #white cloth
        37:(255,255,0,255),         #yellow flower
        38:(255,0,0,255),           #red flower
        39:(193,168,108,127),       #brown mushroom
        40:(255,0,0,127),           #red mushroom
        41:(231,165,45,255),        #gold block
        42:(191,191,191,255),       #iron block
        43:(200,200,200,255),       #double stair
        44:(200,200,200,255),       #stair
        45:(170,86,62,255),         #brick
        46:(160,83,65,255),         #tnt
        47:(157,128,79,255),        #bookcase
        48:(115,115,115,255),       #mossy cobblestone
        49:(26,11,43,255),          #obsidian
        50:(245,220,50,200),        #torch
        51:(255,170,30,200),        #fire
        52:(245,220,50,255),        #mob spawner
        53:(157,128,79,255),        #wooden stairs
        54:(125,91,38,255),         #chest
        55:(245,220,50,255),        #redstone wire
        56:(129,140,143,255),       #diamond ore
        57:(45,166,152,255),        #diamond block
        58:(114,88,56,255),         #workbench
        59:(146,192,0,255),         #crops
        60:(95,58,30,255),          #tilled dirt
        61:(96,96,96,255),          #furnace
        62:(96,96,96,255),          #lit furnace
        63:(111,91,54,255),         #sign post
        64:(136,109,67,255),        #wooden door
        65:(181,140,64,32),         #ladder
        66:(150,134,102,180),       #minecart rail
        67:(115,115,115,255),       #stone stairs
        68:(111,91,54,255),         #sign
        69:(111,91,54,200),         #lever
        70:(120,120,120,255),       #stone pressure plate
        71:(191,191,191,255),       #iron door
        72:(157,128,79,255),        #wooden pressure plate
        73:(131,107,107,255),       #redstone ore
        74:(131,107,107,255),       #lit redstone ore
        75:(181,140,64,32),         #redstone torch (off)
        76:(255,0,0,200),           #redstone torch (on)
        77:(120,120,120,63),        #stone button
        78:(255,255,255,255),       #snow
        79:(83,113,163,51),         #ice
        80:(250,250,250,255),       #snow block
        81:(25,120,25,255),         #cactus
        82:(151,157,169,255),       #clay
        83:(193,234,150,255),       #reeds
        84:(107,71,50,255),         #jukebox
        85:(157,128,79,191),        #fence
    })
    base_block_colors_array = numpy.array([base_block_colors.get(color, (255,255,255,0)) for color in range(255)], dtype=numpy.uint8)
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

        assert sum(map(abs, self.level_size.values())) <= self.chunk_count

        print str(self)

    def __str__(self):
        return 'Name: %s, Chunks: %i, Size: %s' % (os.path.basename(self.level_dir), self.chunk_count, str(self.level_size))

def render_overhead_chunk((map_size, chunk_file)):
    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])
    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X + 1) * Level.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z + 1) * Level.chunk_size_Z)

    chunk = nbt.NBTFile(chunk_file, 'rb')

    chunk_pos_X = chunk['Level']['xPos'].value
    chunk_pos_Z = chunk['Level']['zPos'].value

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(16, 16, 128)
        #tops = [z[z.nonzero()][-1] for x in blocks for z in x]
        #colors = Level.base_block_colors_array[tops].reshape(16, 16, 3)
        for y in range(Level.chunk_size_Y):
            slice = [z[y]  for x in blocks for z in x]
            colors = Level.base_block_colors_array[slice].reshape(16, 16, 4)
            image_array[y][(map_chunk_offset_Z+chunk_pos_Z)*16 : (map_chunk_offset_Z+chunk_pos_Z)*16+16,
                        (map_chunk_offset_X+chunk_pos_X)*16 : (map_chunk_offset_X+chunk_pos_X)*16+16] = colors.swapaxes(0, 1)
    except Exception, err:
        print 'Failed chunk %s: %s' % (str((chunk_pos_X, chunk_pos_Z)), err)

def render_oblique_chunk((map_size, chunk_file)):
    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])
    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X + 1) * Level.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z + 2) * Level.chunk_size_Z)

    chunk = nbt.NBTFile(chunk_file, 'rb')

    chunk_pos_X = chunk['Level']['xPos'].value
    chunk_pos_Z = chunk['Level']['zPos'].value

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(16, 16, 128)
        for y in range(Level.chunk_size_Y):
            slice = [z[y]  for x in blocks for z in x]
            colors = Level.base_block_colors_array[slice].reshape(16, 16, 4)
            image_array[y][(map_chunk_offset_Z+chunk_pos_Z)*16-y : (map_chunk_offset_Z+chunk_pos_Z)*16+16-y,
                        (map_chunk_offset_X+chunk_pos_X)*16 : (map_chunk_offset_X+chunk_pos_X)*16+16] = colors.swapaxes(0, 1)
    except Exception, err:
        print 'Failed chunk %s: %s' % (str((chunk_pos_X, chunk_pos_Z)), err)


def init_mmap(map_image_size, default_color=(255,255,255,0)):
    image_array = shmem.create((Level.chunk_size_Y, map_image_size[1], map_image_size[0], 4), dtype=numpy.uint8)
    image_array[:] = default_color
    return image_array

def overlay_pixel(src, dest):
    new_pixel = numpy.array(
        [(src[3] * src[0] * dest[3])/255**2 + (src[0] * (255 - dest[3]))/255 + (dest[0] * dest[3] * (255 - src[3]))/255**2,
        (src[3] * src[1] * dest[3])/255**2 + (src[1] * (255 - dest[3]))/255 + (dest[1] * dest[3] * (255 - src[3]))/255**2,
        (src[3] * src[2] * dest[3])/255**2 + (src[2] * (255 - dest[3]))/255 + (dest[2] * dest[3] * (255 - src[3]))/255**2,
        (src[3] * dest[3])/255 + (src[3] * (255 - dest[3]))/255 + (dest[3] * (255 - src[3])/255)], dtype=numpy.uint8)
    return new_pixel

render_modes = dict({
    'overhead':render_overhead_chunk,
    'oblique':render_oblique_chunk,
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

        def _init_multiprocess(array):
            global image_array
            image_array = array

        print 'Options; %s' % options
        level = Level(level_file=options['level-file'])
        map_image_size = ((abs(level.level_size['x_max']) + abs(level.level_size['x_min']) + 1) * Level.chunk_size_X, (abs(level.level_size['z_max']) + abs(level.level_size['z_min']) + 1+1) * Level.chunk_size_Z)
        image_array = init_mmap(map_image_size)

        pool = multiprocessing.Pool(options['processes'], _init_multiprocess, (image_array,))
        pool.map(render_modes[options['render-mode']], map(_get_chunk_args, level.chunk_files), level.chunk_count/options['processes'])
        print 'Compositing...'
        if not os.path.isdir('tmp'):
            os.mkdir('tmp')
        Image.new('RGBA', map_image_size, (0,0,0,0)).save('composite-map.png')
        for y in range(Level.chunk_size_Y):
            #this is a temporary hack until I figure out how to properly overlay images in Python itself
            Image.fromarray(image_array[y], 'RGBA').save('tmp/layer-%i.png' % y)
            os.system('composite -compose over tmp/layer-%i.png composite-map.png composite-map.png' % y)

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
