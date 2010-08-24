#!/usr/bin/python

import glob, os.path
import nbt
import Image, ImageDraw
import progressbar

class MapperException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
    def __repr__(self):
        return self.msg

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
    render_modes = ['text', 'overhead', 'oblique']

    def __init__(self, level_file, verbose=False):
        self._verbose = verbose
        self._render_modes = dict({
            'text':self._renderText,
            'overhead':self._renderOverhead,
            'oblique':self._renderOblique
        })

        try:
            nbt.NBTFile(level_file, 'rb')
        except Exception, e:
            raise MapperException(str(e))
        else:
            self._level_dir = os.path.dirname(level_file)

    def msg(self, msg):
        if self._verbose:
            print '[INFO] %s' % str(msg)

    def err(self, msg):
        print '[ERROR] %s' % str(msg)

    def get_map_size(self):
            self.msg('Finding map size...')
            map_files = glob.glob(os.path.join(self._level_dir, '*', '*', '*.dat'))
            map_size = dict({
                'x_min':0,
                'x_max':0,
                'z_min':0,
                'z_max':0
            })
            if self._verbose:
                progress = progressbar.ProgressBar(maxval=len(map_files))
                progress.start()
                count = 0
            for map_file in map_files:
                nbtfile = nbt.NBTFile(map_file, 'rb')
                map_size['x_min'] = min(map_size['x_min'], nbtfile['Level']['xPos'].value)
                map_size['x_max'] = max(map_size['x_max'], nbtfile['Level']['xPos'].value)
                map_size['z_min'] = min(map_size['z_min'], nbtfile['Level']['zPos'].value)
                map_size['z_max'] = max(map_size['z_max'], nbtfile['Level']['zPos'].value)
                if self._verbose:
                    count += 1
                    progress.update(count)
            if self._verbose:
                progress.finish()
            self.msg('Map size: %s' % str(map_size))
            return map_size

    def render(self, mode, output_file):
        if mode in Mapper.render_modes:
            self.msg('Rendering %s map of %s as %s...' % (mode, self._level_dir, output_file))
            self._render_modes[mode](output_file)
            self.msg('Render complete')
        else:
            raise MapperException('Unknown render mode: %s' % mode)

    def _renderText(self, output_file):
        print 'Not Yet Implemented'

    def _renderOblique(self, output_file, height_shading=0.5):
        shade = lambda color_val: int(color_val * height_shading)
        shaded_block_colors = dict({})
        for block in Mapper.block_colors:
            shaded_block_colors[block] = tuple(map(shade, Mapper.block_colors[block]))

        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z + Mapper.chunk_size_Y)
        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGB', map_image_size, (255,255,255))
        draw_point = ImageDraw.Draw(map_image).point

        map_files = glob.glob(os.path.join(self._level_dir, '*', '*', '*.dat'))
        map_files.sort()
        if self._verbose:
            progress = progressbar.ProgressBar(maxval=len(map_files))
            count = 0
            progress.start()

        for map_file in map_files:
            nbtfile = nbt.NBTFile(map_file, 'rb')
            chunk_pos_X = nbtfile['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = nbtfile['Level']['zPos'].value
            blocks = nbtfile['Level']['Blocks'].value
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z + Mapper.chunk_size_Y

            for z in range(Mapper.chunk_size_Z)[::-1]:
                column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                for x in range(Mapper.chunk_size_X):
                    row = x * Mapper.chunk_size_Y
                    for y in range(Mapper.chunk_size_Y):
                        block = ord(blocks[y + row + column])
                        if block != 0:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            draw_point(
                                (chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x - y),
                                Mapper.block_colors.get(block, (0,0,0))
                            )

                            draw_point(
                                (chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x - y + 1),
                                shaded_block_colors.get(block, (0,0,0))
                            )
            if self._verbose:
                count += 1
                progress.update(count)

        if self._verbose:
            progress.finish()
            self.msg('Render took %i seconds' % progress.seconds_elapsed)

        map_image.save(output_file)

    def _renderOverhead(self, output_file):
        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z)
        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGB', map_image_size, (255,255,255))
        draw_point = ImageDraw.Draw(map_image).point

        map_files = glob.glob(os.path.join(self._level_dir, '*', '*', '*.dat'))
        if self._verbose:
            progress = progressbar.ProgressBar(maxval=len(map_files))
            count = 0
            progress.start()

        for map_file in map_files:
            nbtfile = nbt.NBTFile(map_file, 'rb')
            chunk_pos_X = nbtfile['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = nbtfile['Level']['zPos'].value
            blocks = nbtfile['Level']['Blocks'].value
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z

            for x in range(Mapper.chunk_size_X):
                row = x * Mapper.chunk_size_Y
                for z in range(Mapper.chunk_size_Z)[::-1]:
                    column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                    for y in range(Mapper.chunk_size_Y)[::-1]:
                        block = ord(blocks[y + row + column])
                        if block != 0:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            draw_point(
                                (chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x),
                                Mapper.block_colors.get(block, (0,0,0))
                            )
                            break
            if self._verbose:
                count += 1
                progress.update(count)

        if self._verbose:
            progress.finish()
            self.msg('Render took %i seconds' % progress.seconds_elapsed)

        try:
            map_image.save(output_file)
        except IOError, err:
            self.err(err)

if __name__ == '__main__':
    import getopt, sys

    def main():
        short_options = 'o:r:v'
        long_options = ['output-file=', 'render-mode=', 'verbose']
        options = dict({
            'level-file':None,
            'render-mode':'overhead',
            'output-file':'map.png',
            'verbose':False
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
                    if arg in Mapper.render_modes:
                        options['render-mode'] = arg
                    else:
                        raise getopt.GetoptError('Invalid option (%s) argument (%s)' %
                            (opt, arg))
                elif opt in ('-v', '--verbose'):
                    options['verbose'] = True
                else:
                    pass
        except getopt.GetoptError, error:
            print error
            usage()
            return False

        try:
            mapper = Mapper(level_file=options['level-file'], verbose=options['verbose'])
            mapper.render(options['render-mode'], options['output-file'])
        except MapperException, err:
            print str(err)
            return False

    def usage():
        print """%s: [options] path/to/world/level.dat
        Options:
        -o|--output-file <filename>
            The filename of the resulting image. Should end with ".png"
            default: map.png
        -r|--render-mode <%s>
            The method for rendering the map image, currently only supports "overview"
            default: overview
        -v|--verbose
            Output progress and other messages""" % \
        (sys.argv[0], Mapper.render_modes)

    main()