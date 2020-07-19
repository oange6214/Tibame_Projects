#!/usr/bin/env python
# coding: utf-8

import tkinter as tk             # Tkinter GUI 主套件
import tkinter.ttk as ttk        # Tkinter Style
import tempfile                  # 產生暫存檔案
from gtts import gTTS            # 文字 轉 語音
from pygame import mixer         # 播放音訊

from nlp import *                # 文字處理
import cv2                       # 影像處理

from PIL import Image, ImageFont, ImageDraw ,ImageTk     # 圖片處理
import speech_recognition as sr                          # 語音辨識 轉 文字
from datetime import datetime                            # 顯示時間

from threading import Timer                              # 定時多執行緒
import threading                                         # 多執行緒
import glob                                              # 檔案搜尋

from multiprocessing import Process, Queue               # 多程序
from pyaudio import PyAudio, paInt16                     # 語音處理套件
import numpy as np                                       # 資料處理套件
import time                                              # 時間套件

import wave                                              # wave 處理套件
import os                                                # windows 系統套件

def get_backstage_answer_list():
    # 載入 分類判斷用答案
    answer_list = []
    with open('04_Answer_create/backstage_ans.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line.strip().split()
            line = tokenize(line)
            lines = ''
            for i in line:
                lines += i

            answer_list.append(lines)
    return answer_list

def get_display_answer_list():
    # 載入 用於顯示的回答
    answer_list = {}
    lebel = 0
    with open('04_Answer_create/display_ans.txt', 'r', encoding='utf-8') as f:
        for All_file in f:
            Sort_text = All_file.split()
            line = tokenize(Sort_text[0])
            lines = ''
            for i in line:
                lines += i
            answer_list[lebel] = [lines]

            lebel += 1
            
    return answer_list

def get_image():
    # 載入圖片，並利用 tk 迴圈連續存入 list
    image_list = sorted(glob.glob('./QRcode/*.jpg',recursive=True))
    
    qrcode = []
    for path in image_list:
        img = Image.open(path)
        img = img.resize((200, 200), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)
        qrcode.append(img)
        
    return qrcode

class Create_database:
    # 初始化: 資料庫預載
    def __init__(self):
        self.dim, self.word_vecs = load_WordVector()                         # 語料庫
        self.wd_feature = set_word_vector(self.word_vecs, self.dim)          # 建立 句子向量機率

        self.bk_ans_list = get_backstage_answer_list()                       # 答案 比對資料庫
        self.dp_ans_list = get_display_answer_list()                         # 答案 顯示資料庫

class Create_wait_cap:
    # 閒置時 臉部辨識
    def __init__(self, root, catch = 3, index = 0, debug = False):
        self.root = root      # 主框架
        self.catch = catch    # 捕捉次數解鎖
        self.delay = 10       # 更新頻率
        self.debug = debug    # 開啟 影像

        self.recognizer = cv2.face.LBPHFaceRecognizer_create()               # 建立 臉部 辨識器
        self.recognizer.read('trainer/trainer.yml')                          # 辨識器 資料檔
        self.cascadePath = "Cascades/haarcascade_frontalface_default.xml"    # 分類器 資料檔
        self.faceCascade = cv2.CascadeClassifier(self.cascadePath)           # 設置 臉部分類器

        self.cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)    # 抓取 攝影機
        self.cam.set(3, 640)    # 影像 寬度
        self.cam.set(4, 480)    # 影像 高度
        self.minW = 0.1 * self.cam.get(3)    # 根據影像寬度 設置 偵測最小寬度
        self.minH = 0.1 * self.cam.get(4)    # 根據影像高度 設置 偵測最小高度
        
        root.configure(background='black')      # 框架背景
        root.attributes("-fullscreen", True)    # 全螢幕
        
    def update(self):
        # 畫面更新
        _, img = self.cam.read()                        # 攝影機 影像讀取 一次 一張圖片
        img = cv2.flip(img, 1)                          # 垂直翻转
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)    # 轉換 成 灰階
        
        # 臉部 偵測
        faces = self.faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(int( self.minW ), int( self.minH ))
        )
        
        # 偵測 訊息 處理
        for (x, y, w, h) in faces:
            _, confidence = self.recognizer.predict(gray[y:y + h, x:x + w])    # 臉部 識別
            if confidence > 10:     # 傳回的識別機率，用來做出解鎖
                self.catch -= 1
            if self.debug:          # 開啟 臉部捕捉功能，用於檢查
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
        if self.debug:     # 將 影片 顯示
            cv2.imshow('camera', img)
            
        if self.catch <= 0:     # 關閉攝影機、清除 cv2、結束 主框架
            self.cam.release()
            cv2.destroyAllWindows()
            self.root.destroy()
        
        self.root.after(self.delay, self.update)     # 再次呼叫自己，作為更新的功能

class speak_to_text(Process):
    def __init__(self, time_queue, dialogue_queue):
        Process.__init__(self)
        
        self.NUM_SAMPLES = 2000  # pyaudio 內置緩衝大小
        self.SAMPLING_RATE = 16000  # 取樣頻率
        self.LEVEL = 500  # 聲音保存的閥值
        self.Voice_String = []
        self.VOLUME = 100 # 聲音音量
        self.time = time.time()                # 時間紀錄
        self.time_queue = time_queue           # 時間佇列
        self.dialogue_queue = dialogue_queue   # 對話佇列
        self.dialogue = ''                     # 對話紀錄
            
    def run(self):
        pa = PyAudio()
        stream = pa.open(format=paInt16,
                         channels=1,
                         rate=self.SAMPLING_RATE,
                         input=True,
                         frames_per_buffer=self.NUM_SAMPLES)
        
        save_count = 0
        save_buffer = []

        while True:
            # 讀取 NUM_SAMPLES 個取樣
            string_audio_data = stream.read(self.NUM_SAMPLES)
            # 將讀取的數據轉換為數組
            audio_data = np.fromstring(string_audio_data, dtype=np.short)
            # 計算大於 LEVEL 的取樣的個數
            large_sample_count = np.sum(audio_data > self.LEVEL)
#             print(np.max(audio_data))
#             print(large_sample_count)
            
            if large_sample_count > self.VOLUME:
                # 聲量 大於 VOLUME 則表示 有人使用中
                self.time = time.time()
            
            if (time.time() - self.time) > 20:
                self.root.destroy()
                break

            if large_sample_count > 100:
                # 將要保存的數據存放到 save_buffer 中
                save_buffer.append(string_audio_data)
            else: 
                # print (save_buffer)
                # 將 save_buffer 中的數據 寫入 WAV 文件，WAV 文件的文件名是保存的時刻
                # print ("debug")
                if len(save_buffer) > 0:
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

        if self.dialogue != '':
            # 時間佇列，與 Start_Audio_Detection 搭配，判斷是否閒置
            self.time_queue.put( time.time() )

            self.dialogue_queue.put(self.dialogue)

        while True:
            if os.path.exists('temp.wav'):
                os.remove('temp.wav')
                self.dialogue = ''
                break
            
class Start_Audio_Detection(threading.Thread):
    def __init__(self, root):
        threading.Thread.__init__(self)

        self.root = root
        self.time = time.time()            # 計算 時間
        self.time_queue = Queue()          # 時間佇列，用於判斷 使用者 有無說話
        self.dialogue_queue = Queue()      # 對話佇列，用於擷取 使用者 說的話

    def run(self):
        insert_text("您好，請問有甚麼需要服務嗎?")
        speak_activate('您好，請問有甚麼需要服務嗎?')
        
        # 開 多程序 進行 串流語音
        stt = speak_to_text(self.time_queue, self.dialogue_queue)
        stt.start()
        
        while True:
            # 時間佇列，將時間取出來。 與 Get_Audio_Text_Predict() 搭配
            if not self.time_queue.empty():
                self.time = self.time_queue.get()

            # 時間超過 30 秒，離開
            if (time.time() - self.time) > 30:
                self.root.destroy()
                break

            # 使用者 有說話就進行語音轉文字、預測
            if not self.dialogue_queue.empty():
                Get_Audio_Text_Predict(self.dialogue_queue.get())

# TTS
def speak_activate(sentence):
    mixer.init()
    # 將文字 轉語音 並撥放
    with tempfile.NamedTemporaryFile(delete = True) as fp:
        tts = gTTS(text=sentence, lang="zh-tw")
        tts.save('{}.mp3'.format(fp.name))
        mixer.music.load('{}.mp3'.format(fp.name))
        mixer.music.play()
        
    while mixer.music.get_busy():
        pass

# 回答 預判
def predict_text(question, debug):
    # 初始化
    avg_dlg_emb = data.wd_feature(question)  # 取得 問題特徵 (70 維的 浮點數)
    max_idx = len(data.dp_ans_list) - 1      # 取得 回應語句最後一句
    max_sim = -10                            # 用於 儲存 
    
    # 判斷 使用者 的回應
    for idx, ans in enumerate(data.bk_ans_list):
        avg_ans_emb = data.wd_feature(ans)
        sim = cosine_similarity(avg_dlg_emb, avg_ans_emb) 
        
        if sim > max_sim: # 紀錄 機率最大的 索引、機率
            max_idx = idx
            max_sim = sim
        
        if (debug): # 比對 各個資料庫的機率f20
            print(idx, '-' * 30)
            print('用於判斷回應的詞:', ans)
            print("回應的分詞   %s:" % clean_text(ans))
            print("計算的機率   %f" % sim)
            
    if (debug): # 機率最大的 結果
        print('=' * 30)
        print(clean_text(question))
        print('回應的分詞：', data.dp_ans_list[max_idx][0])
        print('計算的機率：', max_sim)
        print()

    if max_idx == 13:
        data.dp_ans_list[max_idx][0] = "現在時間是 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 將 回應 設置 時間資料

    return data.dp_ans_list[max_idx][0], max_idx      # 傳回 對應回應、最大索引值

# List box
def insert_text(sentence):
    list_box.insert(tk.END, sentence)     # 在最底下 新增 一筆資訊
    list_box.see(tk.END)                  # 顯示最後一筆

def Get_Audio_Text_Predict(dialogue):
    insert_text('你說 => ' + dialogue)
    
    # 使用者的話，進行 前處理
    dialogue = ''.join( clean_text(dialogue) )
    
    # 預測 回應結果
    pre_sentence, max_idx = predict_text(dialogue, debug=False)
    
    # 更換 圖片
    display_fram.img_num = max_idx
    display_fram.panel.configure(image = qrcode_list[ max_idx ])
    
    # TTS，文字轉語音
    insert_text('我說=> ' + pre_sentence)
    speak_activate(pre_sentence)
    
    # 對話儲存
    ansspeak = str(max_idx) + " " + pre_sentence
    save_data(dialogue , ansspeak)

class Display_img(ttk.Frame):
    # 顯示 圖片
    def __init__(self, master=None, qrcode_list=None):
        ttk.Frame.__init__(self, master)
        self.img_num = 20
        self.panel = tk.Label(master, image = qrcode_list[ self.img_num ], bg = 'white' )
        self.panel.pack( fill = tk.BOTH ,expan = True)

def save_data(dialogue , ansspeak):
    with open("data.txt", "a", encoding="utf8") as f: 
        f.write("Q: " + dialogue +"  " + "A: " + ansspeak + "\n")

if __name__ == '__main__':
    data = Create_database()
    
    while 1:
        # Face_Unlock
        face_window = tk.Tk()
        face_unLock = Create_wait_cap(face_window, debug = True)
        face_unLock.update()
        face_window.mainloop()

        # NLP 介面
        root = tk.Tk()
        root.configure(bg='#00ff00')
        root.attributes("-fullscreen", True)

        # 對話顯示 建立
            # 在 root 建立 滾動條
        scrollbar = tk.Scrollbar(root)
            # 在 root 建立 list box，70 個字元寬，y 軸 滾動條的指定為 scrollbar
        list_box = tk.Listbox(root, font=('microsoft yahei', 18), width=70, yscrollcommand=scrollbar.set)
            # scrollbar 控制 list_box 的 y 軸
        scrollbar['command'] = list_box.yview
        list_box.pack(anchor=tk.NE, side=tk.RIGHT, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 建立子執行緒，開始 語音偵測
        t_a = Start_Audio_Detection(root)
        t_a.start()

        # 預載 qrcode
        qrcode_list = get_image()
        # 圖片顯示 建立
        display_fram = Display_img(master=root, qrcode_list=qrcode_list)

        root.mainloop()