#!/usr/bin/python
#import argparse
import getopt, sys
import glob, os.path
import nbt
import Image, ImageDraw
import progressbar

def debug(msg):
    debug = False
    if debug:
        print '[DEBUG] %s' % msg

def main():
    global chunk_size_X, chunk_size_Y, chunk_size_Z
    chunk_size_X = 16
    chunk_size_Y = 128
    chunk_size_Z = 16

    short_options = 'o:r:'
    long_options = ['output-file=', 'render-mode=']
    global render_modes
    render_modes = dict({
        'text': _renderText,
        'overhead': _renderOverhead
    })
    global options
    options = dict({
        'level-file':None,
        'render-mode':'overhead',
        'output-file':'map.png'
    })
    global block_colors
#colors shamelessly taken from cartograph
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
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], short_options, long_options)
        debug(opts)
        debug(args)
        try:
            options['level-file'] = args[0]
        except IndexError:
            raise getopt.GetoptError('Missing level-file argument')
        for opt,arg in opts:
            if opt in ('o', 'output-file'):
                options['output-file'] = arg
            elif opt in ('r', 'render-mode'):
                if arg in render_modes:
                    options['render-mode'] = arg
                else:
                    raise getopt.GetoptError('Invalid option (%s) argument (%s)' %
                        (opt, arg))
            else:
                pass
        debug(options)
    except getopt.GetoptError, error:
        print error
        usage()
        return False

    render(options['render-mode'], os.path.dirname(options['level-file']))

def usage():
    print """%s: [options] path/to/world/level.dat
    Options:
    -o|--output-file <filename>
        The filename of the resulting image. Should end with ".png"
        default: map.png
    -r|--render-mode <%s>
        The method for rendering the map image, currently only supports "overview"
        default: overview""" % \
    (sys.argv[0], render_modes.keys())


def get_map_size(path_to_level):
    if not os.path.isdir(path_to_level):
        raise Exception('Level not found')
    else:
        print 'Finding map size'
        map_files = glob.glob(os.path.join(path_to_level, '*', '*', '*.dat'))
        map_size = dict({
            'x_min':0,
            'x_max':0,
            'z_min':0,
            'z_max':0
        })
        for map_file in map_files:
            nbtfile = nbt.NBTFile(map_file, 'rb')
            map_size['x_min'] = min(map_size['x_min'], nbtfile['Level']['xPos'].value)
            map_size['x_max'] = max(map_size['x_max'], nbtfile['Level']['xPos'].value)
            map_size['z_min'] = min(map_size['z_min'], nbtfile['Level']['zPos'].value)
            map_size['z_max'] = max(map_size['z_max'], nbtfile['Level']['zPos'].value)

        debug(map_size)
        return map_size

def render(mode, map):
    if mode in render_modes:
        print 'Rendering %s map of %s' % (mode, map)
        render_modes[mode](map)
    else:
        raise Exception('Unknown render mode: %s' % mode)

def _renderText(path_to_level):
    print 'Not Yet Implemented'

def _renderOverhead(path_to_level):
    map_size = get_map_size(path_to_level)
    map_chunk_offset_X = abs(map_size['x_min'])
    map_chunk_offset_Z = abs(map_size['z_min'])

    map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * chunk_size_Z)
    debug(str(map_image_size))
    map_image = Image.new('RGB', map_image_size, (255,255,255))
    map_drawer = ImageDraw.Draw(map_image)

    map_files = glob.glob(os.path.join(path_to_level, '*', '*', '*.dat'))
    progress = progressbar.ProgressBar(maxval=len(map_files))
    count = 0
    progress.start()
    for map_file in map_files:
        nbtfile = nbt.NBTFile(map_file, 'rb')
        chunk_pos_X = nbtfile['Level']['xPos'].value
        #for chunks, z would be y on a graph
        chunk_pos_Z = nbtfile['Level']['zPos'].value
        blocks = nbtfile['Level']['Blocks'].value
        chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * chunk_size_X
        chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * chunk_size_Z

        for x in range(chunk_size_X):
            row = x * chunk_size_Y
            for z in range(chunk_size_Z)[::-1]:
                column = z * chunk_size_Y * chunk_size_X
                for y in range(chunk_size_Y)[::-1]:
                    block = ord(blocks[y + row + column])
                    if block != 0:
                        # for blocks in a chunk, x would be y on a graph, z would be x
                        map_drawer.point(
                            (chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x),
                            block_colors.get(block, (0,0,0))
                        )
                        break
        count += 1
        progress.update(count)
    progress.finish()
    print 'Render took %is' % progress.seconds_elapsed

    map_image.save(options['output-file'])

if __name__ == '__main__':
    main()