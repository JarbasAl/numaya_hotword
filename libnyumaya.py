from ctypes import *
from os.path import join, dirname
import platform
import sys


def _load_labels(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f]


def _get_lib():
    system = platform.system()
    if system == "Linux":
        machine = platform.machine()
        if machine == "x86_64":
            return join(dirname(__file__), "lib", "linux", "libnyumaya.so")
        elif machine == "armv6l":
            return join(dirname(__file__), "lib", "armv6l", "libnyumaya.so")
        elif machine == "armv7l":
            return join(dirname(__file__), "lib", "armv7l", "libnyumaya.so")
        else:
            raise RuntimeError("Machine not supported")
    elif system == "Windows":
        raise RuntimeError("Windows is currently not supported")

    else:
        raise RuntimeError("Your OS is currently not supported")


class AudioRecognition:
    lib = None

    def __init__(self, modelpath, label_path=None):

        if self.lib is None:
            AudioRecognition.lib = cdll.LoadLibrary(_get_lib())

            AudioRecognition.lib.create_audio_recognition.argtypes = [c_char_p]
            AudioRecognition.lib.create_audio_recognition.restype = c_void_p

            AudioRecognition.lib.GetVersionString.argtypes = [c_void_p]
            AudioRecognition.lib.GetVersionString.restype = c_char_p

            AudioRecognition.lib.GetInputDataSize.argtypes = [c_void_p]
            AudioRecognition.lib.GetInputDataSize.restype = c_size_t

            AudioRecognition.lib.SetSensitivity.argtypes = [c_void_p, c_float]
            AudioRecognition.lib.SetSensitivity.restype = None

            AudioRecognition.lib.RunDetection.argtypes = [c_void_p,
                                                          POINTER(c_uint8),
                                                          c_int]
            AudioRecognition.lib.RunDetection.restype = c_int

            AudioRecognition.lib.RunRawDetection.argtypes = [c_void_p,
                                                             POINTER(c_uint8),
                                                             c_int]
            AudioRecognition.lib.RunRawDetection.restype = POINTER(c_uint8)

        self.obj = AudioRecognition.lib.create_audio_recognition(
            modelpath.encode('ascii'))

        self.check_version()

        if label_path:
            self.labels_list = _load_labels(label_path)

    def check_version(self):
        if sys.version_info[0] < 3:
            major, minor, rev = self.GetVersionString().split('.')
        else:
            version_string = self.GetVersionString()[2:]
            version_string = version_string[:-1]
            major, minor, rev = version_string.split('.')

        if major != "0" and minor != "3":
            print("Your library version is not compatible with this API")

    def RunDetection(self, data):
        datalen = int(len(data))
        pcm = c_uint8 * datalen
        pcmdata = pcm.from_buffer_copy(data)
        prediction = AudioRecognition.lib.RunDetection(self.obj, pcmdata,
                                                       datalen)
        return prediction

    def RunRawDetection(self, data):
        datalen = int(len(data))
        pcm = c_uint8 * datalen
        pcmdata = pcm.from_buffer_copy(data)
        prediction = AudioRecognition.lib.RunRawDetection(self.obj, pcmdata,
                                                          datalen)
        re = [prediction[i] for i in range(2)]
        return re

    def GetPredictionLabel(self, index):
        if (self.labels_list):
            return self.labels_list[index]

    def SetGain(self, gain):
        pass

    def SetSensitivity(self, sens):
        AudioRecognition.lib.SetSensitivity(self.obj, sens)

    def GetVersionString(self):
        return str(AudioRecognition.lib.GetVersionString(self.obj))

    def GetInputDataSize(self):
        return AudioRecognition.lib.GetInputDataSize(self.obj)

    def RemoveDC(self, val):
        pass


class SpeakerVerification:
    lib = None

    def __init__(self, modelpath):
        if self.lib is None:
            SpeakerVerification.lib = cdll.LoadLibrary(_get_lib())

            SpeakerVerification.lib.create_speaker_verification.argtypes = [
                c_char_p]
            SpeakerVerification.lib.create_speaker_verification.restype = c_void_p

            SpeakerVerification.lib.VerifySpeaker.argtypes = [c_void_p,
                                                              POINTER(c_uint8),
                                                              c_int]
            SpeakerVerification.lib.VerifySpeaker.restype = POINTER(c_uint8)

        self.obj = SpeakerVerification.lib.create_speaker_verification(
            modelpath.encode('ascii'))

    def VerifySpeaker(self, data):
        datalen = int(len(data))

        pcm = c_uint8 * datalen
        pcmdata = pcm.from_buffer_copy(data)

        prediction = SpeakerVerification.lib.VerifySpeaker(self.obj, pcmdata,
                                                           datalen)
        fingerprint_len = 512
        re = [prediction[i] for i in range(fingerprint_len)]
        return re


class FeatureExtractor:
    lib = None

    def __init__(self, nfft=512, melcount=40, sample_rate=16000,
                 lowerf=20, upperf=8000, window_len=0.03, shift=0.01):

        self.melcount = melcount
        self.shift = sample_rate * shift
        self.gain = 1

        if self.lib is None:
            FeatureExtractor.lib = cdll.LoadLibrary(_get_lib())

            FeatureExtractor.lib.create_feature_extractor.argtypes = [c_int,
                                                                      c_int,
                                                                      c_int,
                                                                      c_int,
                                                                      c_int,
                                                                      c_float,
                                                                      c_float]
            FeatureExtractor.lib.create_feature_extractor.restype = c_void_p

            FeatureExtractor.lib.get_melcount.argtypes = [c_void_p]
            FeatureExtractor.lib.get_melcount.restype = c_int

            FeatureExtractor.lib.signal_to_mel.argtypes = [c_void_p,
                                                           POINTER(c_int16),
                                                           c_int,
                                                           POINTER(c_uint8),
                                                           c_float]
            FeatureExtractor.lib.signal_to_mel.restype = c_int

        self.obj = FeatureExtractor.lib.create_feature_extractor(nfft,
                                                                 melcount,
                                                                 sample_rate,
                                                                 lowerf,
                                                                 upperf,
                                                                 window_len,
                                                                 shift)

    # Takes audio data in the form of bytes which are converted to int16
    def signal_to_mel(self, data, gain=1):

        datalen = int(len(data) / 2)
        pcm = c_int16 * datalen
        pcmdata = pcm.from_buffer_copy(data)

        number_of_frames = int(datalen / self.shift)
        melsize = self.melcount * number_of_frames

        result = (c_uint8 * melsize)()

        reslen = FeatureExtractor.lib.signal_to_mel(self.obj, pcmdata, datalen,
                                                    result, gain)

        if reslen != melsize:
            print("Bad: melsize mismatch")
            print("Expected: " + str(melsize))
            print("Got: " + str(reslen))

        return bytearray(result)

    def SetGain(self, gain):
        self.gain = gain

    def get_melcount(self):
        return FeatureExtractor.lib.get_melcount(self.obj)

    def RemoveDC(self, val):
        FeatureExtractor.lib.RemoveDC(self.obj, val)
