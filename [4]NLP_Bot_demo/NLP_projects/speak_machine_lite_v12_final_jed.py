
import jieba
from gtts import gTTS
from pygame import mixer
import tkinter.ttk as ttk
import tempfile # 產生暫存檔案
import numpy as np
import tkinter as tk
import json, codecs
import random as rd
from PIL import Image, ImageFont, ImageDraw ,ImageTk
import time
import threading
import speech_recognition
from threading import Timer
import os
import glob
from datetime import datetime
import cv2

from nlp import *

def openCap(SAYHI, debug):
    cascadePath = "Cascades/haarcascade_frontalface_default.xml"
    faceCascade = cv2.CascadeClassifier(cascadePath)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # Show FPS
    FPS = False

    # Initialize and start realtime video capture
    cam = cv2.VideoCapture(0)
    cam.set(3, 640)  # set video widht
    cam.set(4, 480)  # set video height

    # Define min window size to be recognized as a face
    minW = 0.1 * cam.get(3)
    minH = 0.1 * cam.get(4)
    
    catch = 30
    
    while SAYHI:
        if FPS:
            start = time.time() # Start time

        _, img = cam.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(int(minW), int(minH)),
        )
        
        if debug:
            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                catch -= 1
                
            if FPS:
                end = time.time()
                seconds = end - start
                fps = int(1 / seconds)
                cv2.putText(img, str(fps), (25, 25), font, 1, (0, 0, 0), 2)

            cv2.imshow('camera', img)
            
        if catch == 0:
            break
            
        k = cv2.waitKey(10) & 0xff  # Press 'ESC' for exiting video
        if k == 27:
            break
            
    # Do a bit of cleanup
    print("\n [INFO] Exiting Program and cleanup stuff")
    cam.release()
    cv2.destroyAllWindows()

# 讀取 資料集
dim, word_vecs = load_WordVector()
word_feature = set_word_vector(word_vecs, dim)

def get_backstage_answer_list():
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
            
    return answer_list

def speak(sentence):
    with tempfile.NamedTemporaryFile(delete = True) as fp:
        tts = gTTS(text=sentence, lang="zh-tw")
        tts.save('{}.mp3'.format(fp.name))
        mixer.music.load('{}.mp3'.format(fp.name))
        mixer.music.play()

class Display_img(ttk.Frame):
    def __init__(self, master=None, qrcode_list=None):
        ttk.Frame.__init__(self, master)
        self.img_num = 10
        self.panel = tk.Label(master, image = qrcode_list[ self.img_num ], bg = 'white' )
        self.panel.pack( fill = tk.BOTH ,expan = True)

def windowTkinter():
    def predict(question, backstage_answer_list, display_answer_list, debug=False):
        # 向量化
        avg_dlg_emb = word_feature(question)

        if (debug):
            print('==='*30)
            print(clean_text(question))
            print()

        max_idx = len(display_answer_list)-1
        max_sim = -10
        # 在六個回答中，每個答句都取詞向量平均作為向量表示
        # 我們選出與 dialogue 句子向量表示 cosine similarity 最高的短句

        for idx, ans in enumerate(backstage_answer_list):
            print('ans:', ans)
            print()
            avg_ans_emb = word_feature(ans)


            sim = cosine_similarity(avg_dlg_emb, avg_ans_emb) 
            # clean_text(ans)
            if (debug):
                print("Ans #%d:%s:" %  (idx, clean_text(ans)))
                print("Similarity #%d: %f" % (idx, sim))
                print()
            if sim > max_sim:
                max_idx = idx
                max_sim = sim

        #更換圖片
        display_fram.img_num = max_idx
        load_image(qrcode_list[display_fram.img_num])

        if max_idx == 7:
            now_time = get_time()
            display_answer_list[max_idx][0] = now_time

    #     for idx, ans in enumerate(answers):
    #         print("idx: {}".format(Answer_listR[idx]))
    #         print("prob: {} ".format(sim))
    #         print()
    #         print("Answer(%d:prob=%f):%s" % (max_idx, max_sim, answers[max_idx]))

        return display_answer_list[max_idx][0] , max_idx
    
    
    def Get_Audio():
        # 進行錄音
        r = speech_recognition.Recognizer()

        with speech_recognition.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5) 
            audio = r.listen(source)
        try:
            dialogue = r.recognize_google(audio, language="zh-TW") # 透過 語音辨識 將 錄音資料 轉為 文字
            dialogue = dialogue.lower()

            listbox.insert(tk.END,"你說=>" + dialogue)
            listbox.see(tk.END) # 指定 Listbox 看最後一行

            dialogue = clean_text(dialogue) # 將問題進行前處理
            dialogue="".join(dialogue) # 將 List 轉成字串

            pre, max_idx = predict(dialogue, Backstage_Answer_list, Display_Answer_list, True) # 取 答案 和 index
            listbox.insert(tk.END,"我說=> ANS: " + str(max_idx)+" "+pre)
            listbox.see(tk.END)
            speak(pre) # 聲音播放

        # 錯誤處理
        except speech_recognition.UnknownValueError:
            # google 聽不懂
            listbox.insert(tk.END,"Google Speech Recognition could not understand audio")
            listbox.see(tk.END)
        except speech_recognition.RequestError as e:
            # google 沒有給予回應
            listbox.insert(tk.END,"No response from Google Speech Recognition service: {0}".format(e))
            listbox.see(tk.END)

        listbox.see(tk.END)
        button_recording_stop()

    def recording():
        button_recording.config(state=tk.DISABLED) # 停用錄音按鈕
        listbox.insert(tk.END, "您好，請問有甚麼需要服務嗎?")
        listbox.see(tk.END)

        speak("您好，請問有甚麼需要服務嗎?")
        
        T_Get_Audio = Timer(3.0, Get_Audio) # 將 CPU 分支出來處理 Get_Audio function 且延遲 3 秒執行
        T_Get_Audio.start() # 開始執行 T_Get_Audio function
    
    def get_image():
        image_list=glob.glob('./QRcode/*.jpg',recursive=True) #for recurisve 
        qrcode = []
        for f in image_list:
            img = Image.open(f)
            img = img.resize((200, 200), Image.ANTIALIAS) ## The (250, 250) is (height, width)
            img = ImageTk.PhotoImage(img)
            qrcode.append(img)
        print(image_list)
        return qrcode

        # 錄音按鈕 恢復正常
    def button_recording_stop():
        button_recording.config(state=tk.NORMAL)
    
    def load_image(img):
        display_fram.panel.configure(image=img)
    
    def Close_Window():
        window.destroy()
    
    # 抓時間
    def get_time():
        now_time="現在時間是 "+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return now_time
    
    # 建立視窗
    window = tk.Tk()
    # 設定全螢幕
    window.configure(bg='#00ff00')
    window.attributes("-fullscreen", True)
    # 對話框
    listbox = tk.Listbox(window, font=('microsoft yahei', 18), width=70)
    # bar
    scrollbar = tk.Scrollbar(window)
    listbox['yscrollcommand'] = scrollbar.set  # 指定 listbox 的 yscrollbar 回傳函數為 Scrollbar
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.pack(anchor=tk.NE, side=tk.RIGHT, fill=tk.BOTH)
    scrollbar['command'] = listbox.yview  # 指定 scrollbar command 回傳函數為 listbox 的 yview
    # 設定圖片檔變數
    voice_icon = tk.PhotoImage(file="01_GUI/voiceover_1.gif")
    # 錄音按鈕
    button_recording = tk.Button(window,
                                 image=voice_icon,
                                 command=recording,
                                 bg='white')
    
    # image 設定要替代按鈕圖片，command 按下按鈕時要執行的動作
    button_recording.pack(side=tk.TOP, fill=tk.BOTH, expan=True)
    #取得QRcode
    qrcode_list = get_image()
    #建立fram以切換qrcode
    display_fram = Display_img(master=window, qrcode_list=qrcode_list)
    # 關閉視窗安紐
    button_close = ttk.Button(window,
                              text="離開",
                              style="TButton",
                              command=Close_Window)
    
    button_close.pack(side=tk.BOTTOM, fill=tk.BOTH, expan=True)
    
    ttk.Style().configure("TButton",
                          padding=16,
                          relief="flat",
                          background="#000",
                          font=('microsoft yahei', 24, "bold"))
    
    window.mainloop()

Backstage_Answer_list = get_backstage_answer_list()
Display_Answer_list = get_display_answer_list()
mixer.init() 

# while True:
openCap(True, True)
# windowTkinter()
