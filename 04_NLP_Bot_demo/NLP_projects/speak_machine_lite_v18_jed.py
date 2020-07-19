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

from multiprocessing import Process, Queue
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
class Create_wait_cam(threading.Thread):
    def __init__(self, root, stage=0, debug=False):
        threading.Thread.__init__(self)
        
        self.root = root
        self.stage = stage
        self.debug = debug
        self.wait_cam_queue = Queue()

    def run(self):
        fd = Face_detection(self.wait_cam_queue, self.stage, self.debug)
        fd.start()

        self.update()

    def update(self):
        if not self.wait_cam_queue.empty():
            self.root.destroy()
        
        self.root.after(100, self.update)
        
class Face_detection(Process):
    def __init__(self, face_detect_queue, stage, debug):
        Process.__init__(self)
        
        self.face_detect_queue = face_detect_queue

        self.over_time = 10      # 超逾時間
        self.catch = 3           # 捕捉次數
        self.stage = stage       # 0: 解鎖, 1: 待機
        self.debug = debug       # 顯示 影像
        
    def run(self):
        recognizer = cv2.face.LBPHFaceRecognizer_create()               # 建立 臉部 辨識器
        recognizer.read('trainer/trainer.yml')                          # 辨識器 資料檔
        cascadePath = "Cascades/haarcascade_frontalface_default.xml"    # 分類器 資料檔
        faceCascade = cv2.CascadeClassifier(cascadePath)           # 設置 臉部分類器

        cam = cv2.VideoCapture(0)       # 抓取 攝影機
        cam.set(3, 640)                 # 影像 寬度
        cam.set(4, 480)                 # 影像 高度
        minW = 0.1 * cam.get(3)    # 根據影像寬度 設置 偵測最小寬度
        minH = 0.1 * cam.get(4)    # 根據影像高度 設置 偵測最小高度

        self.time = time.time()  # 時間 紀錄

        # 畫面更新
        while True:
            _, img = cam.read()                        # 攝影機 影像讀取 一次 一張圖片
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)    # 轉換 成 灰階，用於 臉部偵測

            # 臉部 偵測
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(int( minW ), int( minH ))
            )

            # 偵測到的訊息 處理預判
            for (x, y, w, h) in faces:
                _, confidence = recognizer.predict(gray[y:y + h, x:x + w])    # 臉部 識別
                
                if confidence > 10:     # 臉部識別機率，用於控制解鎖
                    if self.stage:
                        # 使用者 正常使用的話，紀錄時間
                        self.time = time.time()
                    else:
                        self.catch -= 1

                if self.debug:          # 開啟 畫方框，用於檢查 偵測效果
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if self.debug: # 將 影片 顯示
                cv2.imshow('camera', img)
            
            print((time.time() - self.time))

            # 判斷 現在狀況，並做出對應的動作
            if self.stage:
                # 偵測不到 使用者 超過時間 進行待機
                if (time.time() - self.time) > self.over_time:
                    cam.release()
                    cv2.destroyAllWindows()
                    self.face_detect_queue.put(1)
            else:
                # 偵測 到 使用者 進行解鎖
                if self.catch <= 0:
                    cam.release()
                    cv2.destroyAllWindows()
                    self.face_detect_queue.put(1)
            
            if cv2.waitKey(25) & 0xFF == 27:
                cam.release()
                cv2.destroyAllWindows()
                self.face_detect_queue.put(1)
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

        if sim > max_sim:
            max_idx = idx
            max_sim = sim
            
        if (debug):
            print(idx, '-' * 30)
            print('用於判斷回應的詞:', ans)
            print("回應的分詞   %s:" % clean_text(ans))
            print("計算的機率   %f" % sim)
            
    if (debug):
        print('=' * 30)
        print(clean_text(question))
        print('回應的分詞：', data.dp_ans_list[max_idx][0])
        print('計算的機率：', max_sim)
        print()

    if max_idx == 13:
        data.dp_ans_list[max_idx][0] = get_time()     # 將 回應 設置 時間資料

    return data.dp_ans_list[max_idx][0], max_idx      # 傳回 對應回應、最大索引值

# List box
def insert_text(sentence):
    list_box.insert(tk.END, sentence)     # 在最底下 新增 一筆資訊
    list_box.see(tk.END)                  # 顯示最後一筆

def Get_Audio_Text_Predict():
    insert_text("您好，請問有甚麼需要服務嗎?")
    speak_activate('您好，請問有甚麼需要服務嗎?')

    # 麥克風 讀取 語音訊息
    insert_text("請開啟麥克風...")
    try:
        r = speech_recognition.Recognizer()
        with speech_recognition.Microphone() as source:
            insert_text("調整環境...")
            r.adjust_for_ambient_noise(source, duration=0.5)  # 修正 音訊 0.5 秒長度的雜訊
            
            insert_text("開始收音...")
            audio = r.listen(source)

    except speech_recognition.UnknownValueError as e:
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
    
    insert_text('我說=> ' + pre_sentence)
    speak_activate(pre_sentence)
    
    # 更換 圖片
    display_fram.img_num = max_idx
    display_fram.panel.configure(image = qrcode_list[ max_idx ])
    
    ansspeak = str(max_idx) + " " + pre_sentence
    save_data(dialogue , ansspeak)
    
    Get_Audio_Text_Predict()

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
    face_window.configure(background='black')      # 框架背景
    face_window.attributes("-fullscreen", True)    # 全螢幕
    
    thread_1 = Create_wait_cam(face_window, debug=False)
    thread_1.start()
    
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

    # 預載 qrcode
    qrcode_list = get_image()
    # 圖片顯示 建立
    display_fram = Display_img(master=root, qrcode_list=qrcode_list)

    thread_2 = Create_wait_cam(root, stage=1, debug=False)
    thread_2.start()

    # 建立一個子執行緒
    t = threading.Thread(target = Get_Audio_Text_Predict)
    t.start()

    root.mainloop()
