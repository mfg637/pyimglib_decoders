from . import ACLMMP, ffmpeg_frames_stream
from .video import open_video
import json

SRS_FILE_HEADER = "{\"ftype\":\"CLSRS\""

def is_ACLMMP_SRS(file_path):
    file = open(file_path, 'r')
    header = file.read(16)
    file.close()
    return header == SRS_FILE_HEADER

def decode(file_path):
    fp = open(file_path, "r")
    content_metadata, streams_metadata, minimal_content_compatibility_level = ACLMMP.srs_parser.parseJSON(fp)
    fp.close()

    video = streams_metadata[0].get_compatible_files(0)[0]
    return ffmpeg_frames_stream.FFmpegFramesStream(video, original_filename=file_path)