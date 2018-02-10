from GCS_Storage import GCS_Storage
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types

import os
import sys
import wave
import threading
import math
import time

DEFAULT_SAMPLE_RATE = 44100
DEMO_FILE = 'output.wav'
VIDEO_DEMO_FILE = '''Trump_ 'We will build a wall'.mp4'''
LINE = ''.join(['\n', ('-' * 20), '\n'])

TEST_TRANSCRIBE = False
TEST_CONVERSION = False

class FFMPEG_Error(Exception):
    pass

class Transcribe():
    def __init__(self):
        self._client = speech.SpeechClient()
        self._gcs_storage = GCS_Storage()
        self._processing_done_event = threading.Event()

    def _print_progress(self, iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            bar_length  - Optional  : character length of bar (Int)
        """
        str_format = "{0:." + str(decimals) + "f}"
        percents = str_format.format(100 * (iteration / float(total)))
        filled_length = int(round(bar_length * iteration / float(total)))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

        if iteration == total:
            sys.stdout.write('\n')
        
        sys.stdout.flush()

    def transcribe(self, wav_file):
        """Transcribes a .wav file <80 minutes long"""

        sample_rate = DEFAULT_SAMPLE_RATE
        responses = []
        confidences = []

        if not os.path.isfile(wav_file):
            raise OSError('The .wav file "%s" could not be found.' % (wav_file,))
        if not wav_file.endswith('.wav'):
            raise TypeError('"%s" is not a .wav file!' % (wav_file,))

        try:
            with wave.open(wav_file, 'rb') as wav_file_handle:
                sample_rate = wav_file_handle.getframerate()
        except:
            pass

        uri = self._gcs_storage.upload(wav_file)
        audio = types.RecognitionAudio(uri=uri)
        config = types.RecognitionConfig(encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16, 
                                         sample_rate_hertz=sample_rate, 
                                         language_code='en-US')

        operation = self._client.long_running_recognize(config, audio)
        print('Processing "%s"...' % (wav_file,))
        self._response = None

        def get_result(operation_future):
            self._response = operation_future.result()
            self._processing_done_event.set()

        operation.add_done_callback(get_result)

        while not self._processing_done_event.is_set():
            if operation.metadata is not None:
                progress = operation.metadata.progress_percent
                time.sleep(.1)
                self._print_progress(progress, 100)

        self._print_progress(100, 100)

        for result in self._response.results:
            responses.append(result.alternatives[0].transcript)
            confidences.append(result.alternatives[0].confidence)
        
        transcript = ''.join(responses)
        confidence = sum(confidences)/len(responses)

        return (transcript, confidence)

def convert_video_to_wav_file(video_file, output_file_name=None):
    import subprocess

    if not os.path.isfile(video_file):
        raise OSError('The video "%s" could not be found.')
    if output_file_name is None:
        output_file_name = video_file

    suffix = '0'
    original_output_file_name = output_file_name

    while os.path.isfile(output_file_name):
        base, ext = os.path.splitext(original_output_file_name)
        suffix = str(int(suffix)+1)
        output_file_name = ''.join([base, suffix, '.wav'])
    
    return_code = subprocess.call('ffmpeg -i "%s" -vn -acodec pcm_s16le -ar 44100 -ac 1 "%s"' % (video_file, output_file_name), shell=True)

    if return_code != 0:
        raise FFMPEG_Error('[ffmpeg] Could not convert "%s" to a mono .wav file!' % (video_file,))

    return output_file_name

def convert_audio_to_wav_file(audio_file, output_file_name=None):
    import subprocess

    if not os.path.isfile(audio_file):
        raise OSError('The audio file "%s" could not be found.')
    if output_file_name is None:
        output_file_name = audio_file

    suffix = '0'
    original_output_file_name = output_file_name

    while os.path.isfile(output_file_name):
        base, ext = os.path.splitext(original_output_file_name)
        suffix = str(int(suffix)+1)
        output_file_name = ''.join([base, suffix, '.wav'])

    return_code = subprocess.call('ffmpeg -i "%s" -vn -acodec pcm_u8 -ar 44100 -ac 1 "%s"' % (audio_file, output_file_name), shell=True)

    if return_code != 0:
        raise FFMPEG_Error('[ffmpeg] Could not convert "%s" to a mono .wav file!' % (audio_file,))

    return output_file_name

if __name__ == '__main__':
    if TEST_TRANSCRIBE and not TEST_CONVERSION:
        transcriber = Transcribe()
        transcript, confidence = transcriber.transcribe(DEMO_FILE)
        print('Transcript:', LINE, transcript, LINE, 'This transcription was made with an average of %.2f confidence' % (confidence,))
    elif TEST_CONVERSION and not TEST_TRANSCRIBE:
        convert_video_to_wav_file('videoplayback.mp4')
    elif TEST_CONVERSION and TEST_TRANSCRIBE:
        transcriber = Transcribe()
        transcript, confidence = transcriber.transcribe(convert_video_to_wav_file(VIDEO_DEMO_FILE))
        print('Transcript:', LINE, transcript, LINE, 'This transcription was made with an average of %.2f confidence' % (confidence,))
    
    convert_audio_to_wav_file('y2mate.com - trump_we_will_build_a_wall_1e_7hZOdsxo.mp3')