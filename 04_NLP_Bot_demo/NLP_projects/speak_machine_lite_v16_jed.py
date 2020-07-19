#!/usr/bin/env python
# coding: utf-8

import tkinter as tk             # Tkinter GUI 主套件
import tkinter.ttk as ttk        # Tkinter Style
import tempfile                  # 產生暫存檔案
from gtts import gTTS
from pygame import mixer

from nlp import *
import cv2

from PIL import Image, ImageFont, ImageDraw ,ImageTk
import speech_recognition
from datetime import datetime

from threading import Timer
import threading
from queue import Queue
import glob

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

class Create_wait_cap:
    # 閒置的臉部辨識
    def __init__(self, root, catch = 3, index = 0, debug = False):
        self.root = root
        self.catch = catch
        self.delay = 10
        self.debug = debug
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read('trainer/trainer.yml')
        self.cascadePath = "Cascades/haarcascade_frontalface_default.xml"
        self.faceCascade = cv2.CascadeClassifier(self.cascadePath)
        self.cam = cv2.VideoCapture(index)
        self.cam.set(3, 640)
        self.cam.set(4, 480)
        self.minW = 0.1 * self.cam.get(3)
        self.minH = 0.1 * self.cam.get(4)
        
        root.configure(background='black')
        root.attributes("-fullscreen", True)
        
    def update(self):
        _, img = self.cam.read()
        img = cv2.flip(img, 1)  # Flip vertically
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = self.faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(int( self.minW ), int( self.minH ))
        )
        
        for (x, y, w, h) in faces:
            _, confidence = self.recognizer.predict(gray[y:y + h, x:x + w])
            if confidence > 10:
                self.catch -= 1
            if self.debug:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
        if self.debug:
            cv2.imshow('camera', img)
            
        if self.catch <= 0:
            self.cam.release()
            cv2.destroyAllWindows()
            self.root.destroy()
        
        self.root.after(self.delay, self.update)

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
        data.dp_ans_list[max_idx][0] = get_time()

    return data.dp_ans_list[max_idx][0], max_idx

# List box
def insert_text(sentence):
    list_box.insert(tk.END, sentence)
    list_box.see(tk.END)

# 按鈕 相關功能
def btn_recording():
    insert_text("您好，請問有甚麼需要服務嗎?")
    speak_activate('您好，請問有甚麼需要服務嗎?')
    
    
#     Get_Audio_Text_Predict()
    T_Get_Audio = Timer(3, Get_Audio_Text_Predict) # 將 CPU 分支出來處理 Get_Audio function 且延遲 3 秒執行
    T_Get_Audio.start() # 開始執行 T_Get_Audio function
    
def Get_Audio_Text_Predict():
    # 麥克風 讀取 語音訊息
    r = speech_recognition.Recognizer()
    with speech_recognition.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)  # 修正 音訊 0.5 秒長度的雜訊
        insert_text("收音中")
        audio = r.listen(source)
    try:
        dialogue = r.recognize_google(audio, language="zh-TW") # 透過 語音辨識 將 錄音資料 轉為 文字
        dialogue = dialogue.lower()
    except speech_recognition.UnknownValueError:
        error = '聽不懂'
    except speech_recognition.RequestError as e:
        error = '無法連線'
    
    insert_text('你說 => ' + dialogue)
    # 預測 前處理
    dialogue = ''.join( clean_text(dialogue) )
    # 預測 回應結果
    pre_sentence, max_idx = predict_text(dialogue, debug=True)
    
    insert_text('我說=> ' + pre_sentence)
    speak_activate(pre_sentence)
    
    # 更換 圖片
    display_fram.img_num = max_idx
    display_fram.panel.configure(image = qrcode_list[ max_idx ])
    
    ansspeak = str(max_idx) + " " + pre_sentence
    save_data(dialogue , ansspeak)
    
    Get_Audio_Text_Predict()

class Display_img(ttk.Frame):
    def __init__(self, master=None, qrcode_list=None):
        ttk.Frame.__init__(self, master)
        self.img_num = 20
        self.panel = tk.Label(master, image = qrcode_list[ self.img_num ], bg = 'white' )
        self.panel.pack( fill = tk.BOTH ,expan = True)

def save_data(dialogue , ansspeak):
    with open("data.txt", "a", encoding="utf8") as f: 
        f.write("Q: " + dialogue +"  " + "A: " + ansspeak + "\n")


if __name__ == '__main__':
# while 1:
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
    
    # 預載 qrcode
    qrcode_list = get_image()
    # 圖片顯示 建立
    display_fram = Display_img(master=root, qrcode_list=qrcode_list)
    
    # 離開按鈕 建立
    ttk.Button(root, text="離開", style="TButton", command=root.destroy
              ).pack( side=tk.BOTTOM, fill=tk.BOTH, expan=True)
    ttk.Style().configure("TButton", padding=16, relief="flat", font=('microsoft yahei', 48, "bold"))
    
    # 建立一個子執行緒
    t = threading.Thread(target = btn_recording)
    t.start()

    root.mainloop()