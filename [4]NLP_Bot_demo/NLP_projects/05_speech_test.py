from pyaudio import PyAudio, paInt16
import numpy as np
from datetime import datetime
import wave
import time
import os
import speech_recognition as sr
from multiprocessing import Process, Queue

class speak_to_text(Process):
    NUM_SAMPLES = 2000  # pyaudio 內置緩衝大小
    SAMPLING_RATE = 16000  # 取樣頻率
    LEVEL = 500  # 聲音保存的閥值
    COUNT_NUM = 1000  # NUM_SAMPLES 個取樣之內出現 COUNT_NUM 個大於 LEVEL 的 取樣 則記錄聲音
    SAVE_LENGTH = 8  # 聲音紀錄 的 最小長度：SAVE_LENGTH * NUM_SAMPLES 個取樣
    
    Voice_String = []
    
    def __init__(self):
        Process.__init__(self)
        
        self.dialogue = ''
        
    def run(self):
        self.recoder()
    
    def recoder(self):
        pa = PyAudio()
        stream = pa.open(format=paInt16,
                         channels=1,
                         rate=self.SAMPLING_RATE,
                         input=True,
                         frames_per_buffer=self.NUM_SAMPLES)
        
        save_count = 0
        save_buffer = []
        self.TIME = 0
        
        while True:
            # 讀取 NUM_SAMPLES 個取樣
            string_audio_data = stream.read(self.NUM_SAMPLES)
            # 將讀取的數據轉換為數組
            audio_data = np.fromstring(string_audio_data, dtype=np.short)
            # 計算大於 LEVEL 的取樣的個數
            large_sample_count = np.sum(audio_data > self.LEVEL)
#             print(np.max(audio_data))
#             print(large_sample_count)

            # 如果個數大於 COUNT_NUM，則至少保存 SAVE_LENGTH 個塊
            if large_sample_count > 100:
                # 將要保存的數據存放到 save_buffer 中
                save_buffer.append(string_audio_data)
                print('錄音')
            else: 
                # print (save_buffer)
                # 將 save_buffer 中的數據 寫入 WAV 文件，WAV 文件的文件名是保存的時刻
                # print ("debug")
                if len(save_buffer) > 0:
                    print('儲存')
                    self.Voice_String = save_buffer
                    save_buffer = []
                    
                    self.savewav()
                    
    def savewav(self):
        wf = wave.open("temp.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(self.SAMPLING_RATE)
        wf.writeframes(np.array(self.Voice_String).tostring())
        # wf.writeframes(self.Voice_String.decode())
        wf.close()
        
        r = sr.Recognizer()  # 建立 辨識器
        r.energy_threshold = 4000 # 雜音去除
        with sr.WavFile("temp.wav") as source:  # 讀取 wav 檔
            audio = r.record(source)
        try:
            self.dialogue = r.recognize_google(audio, language="zh-TW")  # 透過 語音辨識 將 錄音資料 轉為 文字
            self.dialogue = self.dialogue.lower()
        except sr.UnknownValueError as e:
            error = '聽不懂'
        except sr.RequestError as e:
            error = '無法連線'

        print(self.dialogue)
        while True:
            if os.path.exists('temp.wav'):
                os.remove('temp.wav')
                self.dialogue = ''
                break

if __name__ == "__main__": 
    r = speak_to_text()
    r.start()
    
    while True:
        pass