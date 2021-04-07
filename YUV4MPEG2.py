from PIL import Image, ImageFile

from . import CustomDecoder

import enum

FILE_SIGNATURE = b"YUV4MPEG2"
SIGNATURE_LENGTH = len(FILE_SIGNATURE)
MAX_HEADER_LINE_SIZE = 2048

LIMITED_COLOR_RANGE = "XCOLORRANGE=LIMITED"


class SUPPORTED_COLOR_SPACES(enum.Enum):
    NONE = 0
    YUV420 = 420
    YUV422 = 422
    YUV444 = 444
    YUVA4444 = 4444


class COLOOR_SPACE(enum.Enum):
    FULL = enum.auto()
    LIMITED = enum.auto()


def is_Y4M(file_path):
    file = open(file_path, 'rb')
    header = file.read(9)
    file.close()
    return header == FILE_SIGNATURE


class YUV4MPEG2Decoder(CustomDecoder.CustomDecoder):
    def __init__(self, file_path):
        self._file_path = file_path
        self._file = open(file_path, 'rb')
        header = self._file.readline(MAX_HEADER_LINE_SIZE)
        if header[:SIGNATURE_LENGTH] != FILE_SIGNATURE:
            self._file.close()
            raise Exception
        _width, _height = 0, 0
        self._profile = SUPPORTED_COLOR_SPACES.NONE
        self._color_space = COLOOR_SPACE.FULL
        header_raw_data = str(header).split(' ')[1:]
        for raw_data in header_raw_data:
            if raw_data[0] == 'W':
                _width = int(raw_data[1:])
            elif raw_data[0] == 'H':
                _height = int(raw_data[1:])
            elif raw_data[0] == 'C':
                if raw_data[1:] == "444":
                    self._profile = SUPPORTED_COLOR_SPACES.YUV444
                elif raw_data[1:] == "444alpha":
                    self._profile = SUPPORTED_COLOR_SPACES.YUVA4444
                elif raw_data[1:] == "422":
                    self._profile = SUPPORTED_COLOR_SPACES.YUV422
                elif raw_data[1:] == "420jpeg":
                    self._profile = SUPPORTED_COLOR_SPACES.YUV420
                else:
                    raise NotImplementedError("color space {} is not supported".format(raw_data))
            elif raw_data[0] == 'I':
                if raw_data != 'Ip':
                    raise NotImplementedError("Interlacing is not supported")
            elif raw_data[0] == 'A':
                if raw_data != "A0:0" and raw_data != "A1:1":
                    raise NotImplementedError("Non square pixel format")
            elif LIMITED_COLOR_RANGE == raw_data[:len(LIMITED_COLOR_RANGE)]:
                self._color_space = COLOOR_SPACE.LIMITED
        self._size = (_width, _height)

    def get_size(self):
        return self._size

    @staticmethod
    def expand_limited_color_range(plane):
        result_plane = bytearray(len(plane))
        for i in range(len(plane)):
            result_plane[i] = int((plane[i] - 16) / 219 * 255)
        return bytes(result_plane)

    def decode(self):
        self._alpha_plane = None
        if self._profile != SUPPORTED_COLOR_SPACES.NONE:
            plane_size = self._size[0] * self._size[1]
            frame_flag = self._file.read(6)
            if frame_flag != b"FRAME\n":
                print("frame flag = {}".format(frame_flag))
                raise SyntaxError("frame flag = {}".format(frame_flag))
            Y_plane = self._file.read(plane_size)
            if self._color_space == COLOOR_SPACE.LIMITED:
                Y_plane = self.expand_limited_color_range(Y_plane)
            Y_channel = Image.frombytes("L", self._size, Y_plane, "raw", "L", 0, 1)
            Cb_plane = b""
            Cr_plane = b""
            color_size = self._size
            if self._profile == SUPPORTED_COLOR_SPACES.YUV444 or self._profile == SUPPORTED_COLOR_SPACES.YUVA4444:
                Cb_plane = self._file.read(plane_size)
                Cr_plane = self._file.read(plane_size)
            elif self._profile == SUPPORTED_COLOR_SPACES.YUV420:
                Cb_plane = self._file.read(plane_size//4)
                Cr_plane = self._file.read(plane_size//4)
                color_size = (self._size[0]//2, self._size[1]//2)
            elif self._profile == SUPPORTED_COLOR_SPACES.YUV422:
                Cb_plane = self._file.read(plane_size//2)
                Cr_plane = self._file.read(plane_size//2)
                color_size = (self._size[0]//2, self._size[1])

            if self._color_space == COLOOR_SPACE.LIMITED:
                Cb_plane = self.expand_limited_color_range(Cb_plane)
                Cr_plane = self.expand_limited_color_range(Cr_plane)

            Cb_channel = Image.frombytes("L", color_size, Cb_plane, "raw", "L", 0, 1)
            Cr_channel = Image.frombytes("L", color_size, Cr_plane, "raw", "L", 0, 1)
            if self._profile != SUPPORTED_COLOR_SPACES.YUV444 and self._profile != SUPPORTED_COLOR_SPACES.YUVA4444:
                Cb_channel = Cb_channel.resize(self._size)
                Cr_channel = Cr_channel.resize(self._size)

            image = Image.merge("YCbCr", (Y_channel, Cb_channel, Cr_channel))
            if self._profile == SUPPORTED_COLOR_SPACES.YUVA4444:
                alpha_channel = Image.frombytes("L", self._size, self._file.read(plane_size), "raw", "L", 0, 1)
                image = image.convert(mode="RGB")
                image.putalpha(alpha_channel)
            self._file.close()
            return image

    def __del__(self):
        self._file.close()
