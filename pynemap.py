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
    render_modes = dict({'blocks':None, 'oblique':None, 'oblique_angled':None, 'overhead':None})

    def __init__(self, level_file, verbose=False, use_alpha=False, keep_chunks=True):
        self._verbose       = verbose
        self._use_alpha     = use_alpha
        self._keep_chunks   = keep_chunks

        self.render_modes['blocks']         = self._render_blocks
        self.render_modes['oblique']        = self._render_oblique
        self.render_modes['oblique_angled'] = self._render_oblique_angled
        self.render_modes['overhead']       = self._render_overhead
        self.render_modes['slices']         = self._render_slices
        self.render_modes['text']           = self._render_text


        self._chunks = []
        self._chunks_loaded = False
        self._chunk_count = 0

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

    def get_map_size(self, use_chunks=False):
            map_size = dict({
                'x_min':0,
                'x_max':0,
                'z_min':0,
                'z_max':0
            })

            if not self._chunks_loaded:
                self._load_chunks()

            self.msg('Finding map size...')

            if self._keep_chunks:
                chunks_xpos = []
                chunks_zpos = []

                for chunk in self._chunks:
                    chunks_xpos.append(chunk['Level']['xPos'].value)
                    chunks_zpos.append(chunk['Level']['zPos'].value)
            else:
                chunks_xpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36), self._chunk_files)
                chunks_zpos = map(lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36), self._chunk_files)

            map_size['x_min'] = min(chunks_xpos)
            map_size['x_max'] = max(chunks_xpos)
            map_size['z_min'] = min(chunks_zpos)
            map_size['z_max'] = max(chunks_zpos)

            self.msg('Map size: %s' % str(map_size))

            return map_size

    def _load_chunks(self, load_sorted=False):
        try:
            self.msg('Loading chunks')
            self._chunk_files = glob.glob(os.path.join(self._level_dir, '*', '*', '*.dat'))
            
            if load_sorted:
                self._chunk_files = sorted(sorted(self._chunk_files, key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[1],36)), key=lambda chunk_file: int(os.path.basename(chunk_file).split('.')[2],36))
            if self._keep_chunks and not self._chunks_loaded:
                self._chunks = map(lambda map_file: nbt.NBTFile(map_file,'rb'), self._chunk_files)
        except Exception, err:
            self._chunks = []
            self._chunks_loaded = False
            self._chunk_count = 0
            self.err('Failed to load chunks')
            raise err
        else:
            self._chunks_loaded = True
            self._chunk_count = len(self._chunks if self._keep_chunks else self._chunk_files)
            self.msg('Loaded %i chunks' % self._chunk_count)

    def render(self, mode, output_file, options=None):
        if not options:
            options = dict({})
        if mode in Mapper.render_modes:
            self.msg('Rendering %s map of %s as %s...' % (mode, self._level_dir, output_file))
            self.render_modes[mode](output_file, options)
            self.msg('Render complete')
        else:
            raise MapperException('Unknown render mode: %s' % mode)

    def _render_text(self, output_file, options):
        print 'Not Yet Implemented'

    def _render_slices(self, output_file, options):
        print 'Not Yet Implemented'
    
    def _render_blocks(self, output_file, options):
        selected_blocks     = map(int, options.get('selected-blocks', [48]))
        overlayed           = options.get('overlayed', False)

        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z)
        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGBA', map_image_size, (255,255,255, 0))
        map_image_pixels = map_image.load()

        if self._verbose:
            progress = progressbar.ProgressBar(maxval=self._chunk_count)
            count = 0
            progress.start()

        for chunk in self._chunks if self._keep_chunks else self._chunk_files:
            if not self._keep_chunks:
                chunk = nbt.NBTFile(chunk, 'rb')
            chunk_pos_X = chunk['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = chunk['Level']['zPos'].value
            blocks = map(ord, chunk['Level']['Blocks'].value)
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z

            for x in range(Mapper.chunk_size_X):
                row = x * Mapper.chunk_size_Y
                for z in range(Mapper.chunk_size_Z)[::-1]:
                    column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                    for y in range(Mapper.chunk_size_Y)[::-1]:
                        block = blocks[y + row + column]
                        if block in selected_blocks:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            try:
                                map_image_pixels[chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x] = \
                                    (0,0,0,255)
                            except:
                                pass
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


    def _render_oblique_angled(self, output_file, options):
        height_shading = options.get('height_shading', 0.7)
        shade = lambda color_val: int(color_val * height_shading)
        shaded_block_colors = dict({})
        self.msg('Generating shaded block colors')
        for block in Mapper.block_colors:
            shaded_block_colors[block] = tuple(map(shade, Mapper.block_colors[block]))

        self._load_chunks(load_sorted=True)
        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((map_size['x_max'] + map_chunk_offset_X) * (Mapper.chunk_size_X * 2 - 1),
            (map_size['z_max'] + map_chunk_offset_Z) * (Mapper.chunk_size_Z * 2 - 1) + Mapper.chunk_size_Y)

        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGB', map_image_size, (255,255,255))
        map_image_pixels = map_image.load()

        if self._verbose:
            progress = progressbar.ProgressBar(maxval=self._chunk_count)
            count = 0
            progress.start()

        last_chunk_pos_Z = None
        angled_pixel_offset_Z = 0
        angled_pixel_offset_X = 0
        for chunk in self._chunks if self._keep_chunks else self._chunk_files:
            if not self._keep_chunks:
                chunk = nbt.NBTFile(chunk, 'rb')

            chunk_pos_X = chunk['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = chunk['Level']['zPos'].value

            if chunk_pos_Z == last_chunk_pos_Z:
                angled_pixel_offset_Z += Mapper.chunk_size_Z
            else:
                angled_pixel_offset_Z = 0
                angled_pixel_offset_X += Mapper.chunk_size_X
                last_chunk_pos_Z = chunk_pos_Z

            blocks = map(ord, chunk['Level']['Blocks'].value)
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X - angled_pixel_offset_X +500
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z + Mapper.chunk_size_Y + angled_pixel_offset_Z +200

            for z in range(Mapper.chunk_size_Z)[::-1]:
                column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                for x in range(Mapper.chunk_size_X):
                    row = x * Mapper.chunk_size_Y
                    for y in range(Mapper.chunk_size_Y):
                        block = blocks[y + row + column]
                        if block != 0:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            try:
                                map_image_pixels[chunk_pixel_offset_X + z - x, chunk_pixel_offset_Z + x - z - y] = \
                                    Mapper.block_colors.get(block, (0,0,0))
                                map_image_pixels[chunk_pixel_offset_X + z - x - 1, chunk_pixel_offset_Z + x - z - y] = \
                                    shaded_block_colors.get(block, (0,0,0))
                            except:
                                pass
            if self._verbose:
                count += 1
                progress.update(count)

        if self._verbose:
            progress.finish()
            self.msg('Render took %i seconds' % progress.seconds_elapsed)

        map_image.save(output_file)


    def _render_oblique(self, output_file, options):
        height_shading = options.get('height_shading', 0.5)
        shade = lambda color_val: int(color_val * height_shading)
        shaded_block_colors = dict({})
        self.msg('Generating shaded block colors')
        for block in Mapper.block_colors:
            shaded_block_colors[block] = tuple(map(shade, Mapper.block_colors[block]))

        self._load_chunks(load_sorted=True)
        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z + Mapper.chunk_size_Y)
        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGB', map_image_size, (255,255,255))
        map_image_pixels = map_image.load()

        if self._verbose:
            progress = progressbar.ProgressBar(maxval=self._chunk_count)
            count = 0
            progress.start()

        
        for chunk in self._chunks if self._keep_chunks else self._chunk_files:
            if not self._keep_chunks:
                chunk = nbt.NBTFile(chunk, 'rb')

            chunk_pos_X = chunk['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = chunk['Level']['zPos'].value
            blocks = map(ord, chunk['Level']['Blocks'].value)
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z + Mapper.chunk_size_Y

            for z in range(Mapper.chunk_size_Z)[::-1]:
                column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                for x in range(Mapper.chunk_size_X):
                    row = x * Mapper.chunk_size_Y
                    for y in range(Mapper.chunk_size_Y):
                        block = blocks[y + row + column]
                        if block != 0:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            try:
                                map_image_pixels[chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x - y] = \
                                    Mapper.block_colors.get(block, (0,0,0))
                                map_image_pixels[chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x - y + 1] = \
                                    shaded_block_colors.get(block, (0,0,0))
                            except:
                                pass
            if self._verbose:
                count += 1
                progress.update(count)

        if self._verbose:
            progress.finish()
            self.msg('Render took %i seconds' % progress.seconds_elapsed)

        map_image.save(output_file)

    def _render_overhead(self, output_file, options):
        map_size = self.get_map_size()
        map_chunk_offset_X = abs(map_size['x_min'])
        map_chunk_offset_Z = abs(map_size['z_min'])

        map_image_size = ((abs(map_size['x_max']) + map_chunk_offset_X) * Mapper.chunk_size_X, (abs(map_size['z_max']) + map_chunk_offset_Z) * Mapper.chunk_size_Z)
        self.msg('Map image size: %s' % str(map_image_size))
        map_image = Image.new('RGB', map_image_size, (255,255,255))
        map_image_pixels = map_image.load()

        if self._verbose:
            progress = progressbar.ProgressBar(maxval=self._chunk_count)
            count = 0
            progress.start()

        for chunk in self._chunks if self._keep_chunks else self._chunk_files:
            if not self._keep_chunks:
                chunk = nbt.NBTFile(chunk, 'rb')
            chunk_pos_X = chunk['Level']['xPos'].value
            #for chunks, z would be y on a graph
            chunk_pos_Z = chunk['Level']['zPos'].value
            blocks = map(ord, chunk['Level']['Blocks'].value)
            chunk_pixel_offset_X = (chunk_pos_X + map_chunk_offset_X) * Mapper.chunk_size_X
            chunk_pixel_offset_Z = (chunk_pos_Z + map_chunk_offset_Z) * Mapper.chunk_size_Z

            for x in range(Mapper.chunk_size_X):
                row = x * Mapper.chunk_size_Y
                for z in range(Mapper.chunk_size_Z)[::-1]:
                    column = z * Mapper.chunk_size_Y * Mapper.chunk_size_X
                    for y in range(Mapper.chunk_size_Y)[::-1]:
                        block = blocks[y + row + column]
                        if block != 0:
                            # for blocks in a chunk, x would be y on a graph, z would be x
                            try:
                                map_image_pixels[chunk_pixel_offset_X + z, chunk_pixel_offset_Z + x] = \
                                    Mapper.block_colors.get(block, (0,0,0))
                            except:
                                pass
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
    import time
    def main():
        short_options = 'o:r:v'
        long_options = ['output-file=', 'render-mode=', 'only-blocks=', 'verbose', 'keep-chunks', 'use-alpha']
        options = dict({
            'level-file':None,
            'render-mode':'overhead',
            'output-file':'map.png',
            'verbose':False,
            'keep-chunks':False,
            'use-alpha':False
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
                    if arg in Mapper.render_modes:
                        options['render-mode'] = arg
                    else:
                        raise getopt.GetoptError('Invalid option (%s) argument (%s)' %
                            (opt, arg))
                elif opt in ('-v', '--verbose'):
                    options['verbose'] = True
                elif opt == '--keep-chunks':
                    options['keep-chunks'] = True
                elif opt == '--use-alpha':
                    options['use-alpha'] = True
                elif opt == '--only-blocks':
                    render_options['selected-blocks'] = arg.split(',')
                else:
                    pass
        except getopt.GetoptError, error:
            print error
            usage()
            return False

        try:
            start = time.time()
            mapper = Mapper(
                level_file  = options['level-file'],
                verbose     = options['verbose'],
                keep_chunks = options['keep-chunks'],
                use_alpha   = options['use-alpha'])

            mapper.render(options['render-mode'], options['output-file'], render_options)
            mapper.msg('Total render time: %.5f seconds' % (time.time() - start))
        except MapperException, err:
            print str(err)
            return False

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
        --keep-chunks
            Keep chunks in loaded in memory, can use *a lot* of memory for large maps
            default: load chunks one at a time during render
        --use-alpha
            *NYI* Use transparency for nicer looking maps
            default: no alpha channel
    Render Options:
        *blocks*:
            --only-blocks <block[,block[,block]]>
                Comma separated list of (dec) block ids to render
            --overlayed
                *NYI* Overlay onto overhead map
""" % \
        (sys.argv[0], Mapper.render_modes.keys())

    main()