import tempfile
import subprocess
from . import YUV4MPEG2

workers_count = 1


def is_avif(file):
    file = open(file, 'rb')
    file.seek(4)
    header = file.read(8)
    file.close()
    return header == b'ftypavif'


def decode(file):
    if not is_avif(file):
        raise Exception
    tmp_file = tempfile.NamedTemporaryFile(mode='rb', delete=True, suffix='.y4m')
    subprocess.call(['avifdec', '-j', str(workers_count), str(file), tmp_file.name])
    decoder = YUV4MPEG2.YUV4MPEG2Decoder(tmp_file.name)
    return decoder.decode()