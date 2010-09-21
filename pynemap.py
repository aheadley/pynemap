#!/usr/bin/python

import glob, os
import nbt
import numpy, shmem
import multiprocessing
import itertools

class LevelException(Exception):
    def __init__(self, err_msg):
        self.msg = err_msg
    def __str__(self):
        return self.msg

class Level(object):
    _base_block_colors = dict({
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
    base_block_colors = numpy.array([_base_block_colors.get(color, (255,255,255,0)) for color in range(255)], dtype=numpy.uint8)
    shaded_block_colors = base_block_colors >> 1
    color_depth = 4
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
        self.chunk_files = sorted(
            sorted(
                glob.glob(os.path.join(self.level_dir, '*', '*', 'c.*.*.dat')),
                key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36)
            ),
            key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36)
        )
        self.chunk_count = len(self.chunk_files)
        self.level_size = dict({
            'x_min':0,
            'x_max':0,
            'z_min':0,
            'z_max':0,
        })
        chunks_xpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36), self.chunk_files)
        chunks_zpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36), self.chunk_files)
        self.level_size['x_min'] = min(chunks_xpos)
        self.level_size['x_max'] = max(chunks_xpos)
        self.level_size['z_min'] = min(chunks_zpos)
        self.level_size['z_max'] = max(chunks_zpos)

        # Make sure that the dimensions of the level provide equal or more chunks
        #  than there are chunk files.
        assert (abs(self.level_size['x_min']) + 1 + self.level_size['x_max']) * \
            (abs(self.level_size['z_min']) + 1 + self.level_size['z_max']) >= \
            self.chunk_count

    def __str__(self):
        return 'Name: %s, Chunks: %i, Size: %s' % (os.path.basename(self.level_dir), self.chunk_count, str(self.level_size))

def render_overhead_chunk((chunk_file, map_size, render_options)):
    chunk = nbt.NBTFile(chunk_file, 'rb')
    array_offset_X = (abs(map_size['x_min']) + chunk['Level']['xPos'].value) * Level.chunk_size_X
    array_offset_Z = (abs(map_size['z_min']) + chunk['Level']['zPos'].value) * Level.chunk_size_Z

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.chunk_size_Y)
        for y in xrange(Level.chunk_size_Y):
            colors = Level.base_block_colors[blocks[...,y]].reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.color_depth)
            image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z,
                array_offset_X : array_offset_X + Level.chunk_size_X] = overlay_chunk(
                    colors.swapaxes(0, 1),
                    image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z,
                        array_offset_X : array_offset_X + Level.chunk_size_X])
        print 'Finished chunk %s' % str((array_offset_X, array_offset_Z))
    except IndexError, err:
        print 'Failed chunk: %s' % err

def render_oblique_chunk((chunk_file, map_size, render_options)):
    chunk = nbt.NBTFile(chunk_file, 'rb')
    array_offset_X = (abs(map_size['x_min']) + chunk['Level']['xPos'].value) * Level.chunk_size_X
    array_offset_Z = (abs(map_size['z_min']) + chunk['Level']['zPos'].value) * Level.chunk_size_Z

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.chunk_size_Y)
        new_chunk_pixels = image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z * 2 + Level.chunk_size_Y,
            array_offset_X : array_offset_X + Level.chunk_size_X]

        for y in range(Level.chunk_size_Y):
            colors = Level.base_block_colors[blocks[...,y]].reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.color_depth)
            shaded_colors = Level.base_block_colors[blocks[...,y]].reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.color_depth)
            for z,x in itertools.product(*map(xrange, [Level.chunk_size_X, Level.chunk_size_Z])):
                try:
                    new_chunk_pixels[(Level.chunk_size_Y - y) + z, x] = overlay_pixel(colors[x, z], new_chunk_pixels[(Level.chunk_size_Y - y) + z, x])
                    new_chunk_pixels[(Level.chunk_size_Y - y) + z + 1, x] = overlay_pixel(shaded_colors[x, z], new_chunk_pixels[(Level.chunk_size_Y - y) + z + 1, x])
                except IndexError:
                    pass
        image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z * 2 + Level.chunk_size_Y,
            array_offset_X : array_offset_X + Level.chunk_size_X] = new_chunk_pixels
    except IndexError, err:
        print 'Failed chunk: %s' % err

def render_topographic_chunk((chunk_file, map_size, render_options)):
    import topography
    chunk = nbt.NBTFile(chunk_file, 'rb')
    array_offset_X = (abs(map_size['x_min']) + chunk['Level']['xPos'].value) * Level.chunk_size_X
    array_offset_Z = (abs(map_size['z_min']) + chunk['Level']['zPos'].value) * Level.chunk_size_Z

    try:
        blocks = numpy.fromstring(chunk['Level']['Blocks'].value, dtype=numpy.uint8).reshape(Level.chunk_size_X, Level.chunk_size_Z, Level.chunk_size_Y)
        for y in xrange(Level.chunk_size_Y):
            profile = topography.translator[blocks[...,y]]
            water = (profile == -1) * 1
            colors = topography.topographic_colors[((profile + water) * (y + 2)) + water].reshape(
                Level.chunk_size_X, Level.chunk_size_Z, Level.color_depth
            )

            image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z,
                array_offset_X : array_offset_X + Level.chunk_size_X] = overlay_chunk(
                    colors.swapaxes(0, 1),
                    image_array[array_offset_Z : array_offset_Z + Level.chunk_size_Z,
                        array_offset_X : array_offset_X + Level.chunk_size_X])
        print 'Finished chunk %s' % str((array_offset_X, array_offset_Z))
    except IndexError, err:
        print 'Failed chunk: %s' % err


def init_image_array(map_image_size, default_color=(0,0,0,0)):
    image_array = shmem.create((map_image_size[1], map_image_size[0], Level.color_depth), dtype=numpy.uint8)
    image_array[:] = default_color
    return image_array

def overlay_chunk(src_chunk, dest_chunk):
    # Courtesy of Peter B. (peter.be...ton@gmail.com)
    chunk = numpy.zeros((Level.chunk_size_Z, Level.chunk_size_X, Level.color_depth), dtype=numpy.uint32)
    """

    blend( (sL,sA), (dL,dA) ) = t1 + t2 + t3

    t1 = sL * sA *   dA  / (255^2)
    t2 = dL * dA * (!sA) / (255^2)
    t3 = sL *      (!dA) /  255

    """

    src_channel_R  = src_chunk[:,:,0].astype(numpy.uint32)
    dest_channel_R = dest_chunk[:,:,0].astype(numpy.uint32)
    src_channel_G  = src_chunk[:,:,1].astype(numpy.uint32)
    dest_channel_G = dest_chunk[:,:,1].astype(numpy.uint32)
    src_channel_B  = src_chunk[:,:,2].astype(numpy.uint32)
    dest_channel_B = dest_chunk[:,:,2].astype(numpy.uint32)
    src_channel_A  = src_chunk[:,:,3].astype(numpy.uint32)
    dest_channel_A = dest_chunk[:,:,3].astype(numpy.uint32)

    for i, (s,d) in enumerate(zip(
        (src_channel_R, src_channel_G, src_channel_B),
        (dest_channel_R, dest_channel_G, dest_channel_B)
    )):
        chunk[:,:,i] = (
            #t1 =  sL * sA *   dA  / (255^2)
            (s * src_channel_A * dest_channel_A / 65025) +
            #t2 = dL * dA * (!sA) / (255^2)
            (d * dest_channel_A * (255 - src_channel_A) / 65025) +
            #t3 = sL *      (!dA) /  255
            (s * (255 - dest_channel_A) / 255)
        )
    chunk[:,:,3] = (src_channel_A * dest_channel_A) / 255 + \
        (src_channel_A * (255 - dest_channel_A)) / 255 + \
        (dest_channel_A * (255 - src_channel_A) / 255)

    return chunk.reshape(Level.chunk_size_Z, Level.chunk_size_X, Level.color_depth).astype(numpy.uint8)

def overlay_pixel(src, dst):
    pixel = numpy.array([
        #RED
        ((src[3] * src[0] * dst[3])/255**2) +
        ((src[0] * (255 - dst[3]))/255    ) +
        ((dst[0] * dst[3] * (255 - src[3]))/255**2),
        #GREEN
        ((src[3] * src[1] * dst[3])/255**2) +
        ((src[1] * (255 - dst[3]))/255    ) +
        ((dst[1] * dst[3] * (255 - src[3]))/255**2),
        #BLUE
        ((src[3] * src[2] * dst[3])/255**2) +
        ((src[2] * (255 - dst[3]))/255    ) +
        ((dst[2] * dst[3] * (255 - src[3]))/255**2),
        #ALPHA
        (src[3] * dst[3]         )/255    + (src[3] * (255 - dst[3]))/255 + (dst[3] * (255 - src[3])/255)
        ],
        dtype=numpy.uint8)
    return pixel

render_modes = dict({
    'overhead':     render_overhead_chunk,
    #'oblique':      render_oblique_chunk,
    'topographic':  render_topographic_chunk,
})

if __name__ == '__main__':
    import getopt, sys
    import Image

    def main():
        short_options = 'o:r:v'
        long_options = [
            'output-file=',
            'render-mode=',
            'processes=',
            'verbose',
        ]
        options = dict({
            'level-file':None,
            'render-mode':'overhead',
            'output-file':'map.png',
            'verbose':False,
            'processes':multiprocessing.cpu_count(),
        })
        render_options = dict({
            'slices':None,
            'blocks':None,
        })

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
                elif opt == '--processes':
                    options['processes'] = max(int(arg), 1)
                else:
                    pass
        except getopt.GetoptError, error:
            print error
            usage()
            return None

        def _get_chunk_args(chunk_file):
            return (chunk_file, level.level_size, render_options)

        def _init_multiprocess(array):
            global image_array
            image_array = array

        level = Level(level_file=options['level-file'])
        if options['verbose']: print level

        if options['render-mode'] == 'oblique':
            map_image_size_addon = (0,Level.chunk_size_Y)
        else:
            map_image_size_addon = (0,0)
        map_image_size = (
            (level.level_size['x_max'] + abs(level.level_size['x_min']) + 1) * Level.chunk_size_X + map_image_size_addon[0],
            (level.level_size['z_max'] + abs(level.level_size['z_min']) + 1) * Level.chunk_size_Z + map_image_size_addon[1],
        )
        global image_array
        image_array = init_image_array(map_image_size)

        pool = multiprocessing.Pool(options['processes'], _init_multiprocess, (image_array,))
        if options['verbose']: print 'Rendering...'
        pool.map(render_modes[options['render-mode']], map(_get_chunk_args, level.chunk_files), level.chunk_count/options['processes'])
        #for x in range(5): render_oblique_chunk((level.chunk_files[x], level.level_size, render_options))
        Image.fromarray(image_array, 'RGBA').save(options['output-file'])

    def usage():
        print """%s: [options] path/to/world/level.dat
    General Options:
        -o|--output-file <filename>
            The filename of the resulting image. Should end with ".png"
            default: map.png
        -r|--render-mode <%s>
            The method for rendering the map image
            default: overhead
        -v|--verbose
            Output progress and other messages
            default: off (quiet)
        --processes <count>
            Set the number of render processes
            default: # of cpu cores""" % \
        (sys.argv[0], render_modes.keys())
    main()
