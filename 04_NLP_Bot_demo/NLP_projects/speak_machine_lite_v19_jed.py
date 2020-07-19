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
import speech_recognition                                # 語音辨識 轉 文字
from datetime import datetime                            # 顯示時間

from threading import Timer                              # 定時多執行緒
import threading                                         # 多執行緒
import glob                                              # 檔案搜尋

from queue import Queue
from multiprocessing import Process
from pyaudio import PyAudio, paInt16
import numpy as np
import time

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

# 初始化: 資料庫預載
class Create_database:
    def __init__(self):
        self.dim, self.word_vecs = load_WordVector()                         # 語料庫
        self.wd_feature = set_word_vector(self.word_vecs, self.dim)          # 建立 句子向量機率

        self.bk_ans_list = get_backstage_answer_list()                       # 答案 比對資料庫
        self.dp_ans_list = get_display_answer_list()                         # 答案 顯示資料庫
        
data = Create_database()

# 閒置時 臉部辨識
class Create_wait_cap:
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

class Sound_detection(threading.Thread):
    def __init__(self, root, time_queue):
        threading.Thread.__init__(self)

        self.root = root
        self.NUM_SAMPLES = 2000  # pyaudio 緩衝大小
        self.SAMPLING_RATE = 8000  # 取樣頻率
        self.LEVEL = 500  # 聲音保存的閥值
        self.VOLUME = 1500 # 聲音音量
        self.time = time.time()
        self.time_queue = time_queue

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
            # 時間佇列，將時間取出來。 與 Get_Audio_Text_Predict() 搭配
            if not self.time_queue.empty():
                self.time = self.time_queue.get()
            
            # 讀取 NUM_SAMPLES 個取樣
            string_audio_data = stream.read(self.NUM_SAMPLES)
            # 將 讀取 的 數據 轉換為 數組
            audio_data = np.fromstring(string_audio_data, dtype=np.short)
            # 計算大於 LEVEL 的 取樣 的個數
            large_sample_count = np.sum(audio_data > self.LEVEL)

            print(np.max(audio_data))

            if np.max(audio_data) > self.VOLUME:
                # 聲量 大於 VOLUME 則表示 有人使用中
                self.time = time.time()
            
            if (time.time() - self.time) > 20:
                self.root.destroy()
                break

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
        
        if (debug): # 比對 各個資料庫的機率
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


def Get_Audio_Text_Predict(time_queue):
    insert_text("您好，請問有甚麼需要服務嗎?")
    speak_activate('您好，請問有甚麼需要服務嗎?')

    # 麥克風 讀取 語音訊息
    insert_text("請開啟麥克風...")
    try:
        r = speech_recognition.Recognizer()
        with speech_recognition.Microphone() as source:
            insert_text("調整環境...")
            r.adjust_for_ambient_noise(source, duration=0.5)  # 修正 音訊 0.5 秒長度的雜訊

            time_queue.put( time.time() ) # 時間佇列，與 sound_detection class 搭配，判斷是否閒置
            insert_text("開始收音...")
            audio = r.listen(source)

    except speech_recognition.UnknownValueError:
        error = '聽不懂'
    except speech_recognition.RequestError as e:
        error = '無法連線'
    
    dialogue = r.recognize_google(audio, language="zh-TW") # 透過 語音辨識 將 錄音資料 轉為 文字
    dialogue = dialogue.lower()    # 轉小寫
    
    insert_text('你說 => ' + dialogue)
    
    # 使用者的話，進行 前處理
    dialogue = ''.join( clean_text(dialogue) )
    
    insert_text("讓我找找...")
    # 預測 回應結果
    pre_sentence, max_idx = predict_text(dialogue, debug=False)

    # 更換 圖片
    display_fram.img_num = max_idx
    display_fram.panel.configure(image = qrcode_list[ max_idx ])
    
    insert_text('我說=> ' + pre_sentence)
    speak_activate(pre_sentence)
    
    ansspeak = str(max_idx) + " " + pre_sentence
    save_data(dialogue , ansspeak)
    
    Get_Audio_Text_Predict(time_queue)

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
#     while 1:
#     Face_Unlock
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

    time_queue = Queue() # 時間佇列

    # 建立子執行緒，用於 語音對話
    t_r = threading.Thread(target = Get_Audio_Text_Predict, args=(time_queue, ))
    t_r.start()

    # 建立子執行緒，用於 聲音偵測
    t_a = Sound_detection(root, time_queue)
    t_a.start()

    # 預載 qrcode
    qrcode_list = get_image()
    # 圖片顯示 建立
    display_fram = Display_img(master=root, qrcode_list=qrcode_list)

    root.mainloop()