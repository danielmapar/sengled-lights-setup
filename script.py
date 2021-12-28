import sengled
from dotenv import load_dotenv
from threading import Thread
import random
import time
import pyaudio
import wave
import numpy as np
from math import *
from wavtorgb import *

load_dotenv()

class WavToRgb(object):
    '''A class for converting a WAV file into a set of RGB values.'''
    def __init__(self):
        self.chunk = 2048
        # use a Blackman window
        self.window = np.blackman(self.chunk)
        self.p = pyaudio.PyAudio()
        self.thefreq = 1.0
        self.c = 3*10**8
    
    def __del__(self):
        self.p.terminate()
    
    def convert(self, file_name):
        rgbs = []
        wf = wave.open(file_name, 'rb')
        SAMPLE_WIDTH = wf.getsampwidth()
        RATE = wf.getframerate()
        CHANNELS = wf.getnchannels()

        stream = self.p.open(format = self.p.get_format_from_width(SAMPLE_WIDTH),
                channels = CHANNELS,
                rate = RATE,
                output = True)

        # read the incoming data
        data = wf.readframes(self.chunk)

        # play stream and find the frequency of each chunk
        while len(data) == self.chunk * SAMPLE_WIDTH:
            # write data out to the audio stream
            stream.write(data)
            # unpack the data and times by the hamming window
            in_data = np.array(wave.struct.unpack("%dh"%(len(data)/SAMPLE_WIDTH), data))*self.window
            # Take the fft and square each value
            fftData=abs(np.fft.rfft(in_data))**2
            # find the maximum
            which = fftData[1:].argmax() + 1

            if which != len(fftData)-1:
                y0,y1,y2 = np.log(fftData[which-1:which+2:])
                x1 = (y2 - y0) * .5 / (2 * y1 - y2 - y0)
                # find the frequency and output it
                self.thefreq = (which+x1)*RATE/self.chunk
                self.thefreq = which*RATE/self.chunk
                print("The previous freq is: " + str(self.thefreq))
                while self.thefreq < 350 and self.thefreq > 15:
                    self.thefreq = self.thefreq*2
                    print("The new freq is: " + str(self.thefreq))
                while self.thefreq > 700:
                    self.thefreq = self.thefreq/2
                    print("The new freq is: " + str(self.thefreq))
                THz = self.thefreq*2**40
                pre = float(self.c)/float(THz)
                nm = int(pre*10**(-floor(log10(pre)))*100)	
                print("Your nm total: " + str(nm))
                rgb = wavelen2rgb(nm, MaxIntensity=255)
                print("The colors for this nm are: " + str(rgb))
                rgbs.append(rgb)
            
            # read some more data
            data = wf.readframes(self.chunk)
            if data:
                stream.write(data)
        stream.close()
        wf.close()
        return rgbs

class Recorder(object):
    '''A recorder class for recording audio to a WAV file.
    Records in mono by default.
    '''

    def __init__(self, channels=1, rate=44100, frames_per_buffer=1024):
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer

    def open(self, fname, mode='wb'):
        return RecordingFile(fname, mode, self.channels, self.rate,
                            self.frames_per_buffer)

class RecordingFile(object):
    def __init__(self, fname, mode, channels, 
                rate, frames_per_buffer):
        self.fname = fname
        self.mode = mode
        self.input_device_index = 2
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self.wavefile = self._prepare_file(self.fname, self.mode)
        self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, exception, value, traceback):
        self.close()
    
    def set_mic_input(self):
        if self.input_device_index is not None:
            return
            
        for index in range(0, self._pa.get_device_count()):
            print(index, self._pa.get_device_info_by_index(index)['name'])

        self.input_device_index = int(input())

        print("You selected: " + self._pa.get_device_info_by_index(self.input_device_index)['name'])

    def record(self, duration):
        self.set_mic_input()
        # Use a stream with no callback function in blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        input_device_index=self.input_device_index,
                                        frames_per_buffer=self.frames_per_buffer)
        for _ in range(int(self.rate / self.frames_per_buffer * duration)):
            audio = self._stream.read(self.frames_per_buffer)
            self.wavefile.writeframes(audio)
        return None

    def start_recording(self):
        self.set_mic_input()
        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        input_device_index=self.input_device_index,
                                        frames_per_buffer=self.frames_per_buffer,
                                        stream_callback=self.get_callback())
        self._stream.start_stream()
        return self

    def stop_recording(self):
        self._stream.stop_stream()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            self.wavefile.writeframes(in_data)
            return in_data, pyaudio.paContinue
        return callback


    def close(self):
        self._stream.close()
        self._pa.terminate()
        self.wavefile.close()

    def _prepare_file(self, fname, mode='wb'):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        wavefile.setframerate(self.rate)
        return wavefile

def change_light(device, color, brightness):
    device.set_color(color)
    device.set_brightness(brightness)

def main():
    recorder = Recorder(channels=1)
    wav_to_rgb = WavToRgb()

    sengled_api = sengled.api_from_env()
    devices = sengled_api.get_device_details()

    TEMP_FILE_NAME = 'nonblocking.wav'

    while True:
        with recorder.open(TEMP_FILE_NAME, 'wb') as recfile2:
            recfile2.start_recording()
            time.sleep(1)
            recfile2.stop_recording()

        # Returns an array of RGBs
        rgbs = wav_to_rgb.convert(TEMP_FILE_NAME)

        for rgb in rgbs:
            red = rgb[0]
            green = rgb[1]
            blue = rgb[2]
            #red = random.randrange(1, 255)
            #green = random.randrange(1, 255)
            #blue = random.randrange(1, 255)
            color = [red, green, blue]
            threads = []
            brightness = random.randrange(1, 100)
            for device in devices:
                threads.append(Thread(target=change_light, args=(device, color, brightness, )))
        
            for thread in threads:
                thread.start()
        
            for thread in threads:
                thread.join()

if __name__ == '__main__':
    main()


# 

# devices = api.get_device_details()

# def change_light(device, color):
#     device.set_color(color)
#     device.set_brightness(random.randrange(1, 100))
#     #device.set_color_temperature(10)

# while (True):
#     time.sleep(10)
#     red = random.randrange(1, 255)
#     green = random.randrange(1, 255)
#     blue = random.randrange(1, 255)
#     color = [red, green, blue]
#     threads = []
#     for device in devices:
#         threads.append(Thread(target=change_light, args=(device, color, )))
    
#     for thread in threads:
#         thread.start()
    
#     for thread in threads:
#         thread.join()
    

