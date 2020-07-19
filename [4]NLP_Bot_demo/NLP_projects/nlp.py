import jieba
import os
from bs4 import BeautifulSoup
import numpy as np

# from gensim.models import word2vec


# 載入檔案
def file_read(file,mode):
    try:
        with open(file,mode,encoding="utf8") as f: 
            text=f.read()
            return text
    except IOError:
        print('Error: cannot open file')

# 載入 去贅詞 的資料庫
stop_words = file_read('stop_words.txt', 'r')

# 分詞
def sentence_list(text):
    jieba.load_userdict('special_word.txt')
    sg_list = jieba.cut(text, cut_all=False)
    return list(sg_list)

# 去除 標點符號
def tokenize(text):
    out = "?。」「，.! /;:\n\'\"、@#%^&*"
    token_free_words = [word for word in text if word not in out]
    return token_free_words

# 去除 贅詞
def remove_noise(tokens):
    noise_free_words = [word for word in tokens if word not in stop_words]
    return noise_free_words

# 工作內容：分詞、去標點、去贅詞
def clean_text(text):
    word_list = sentence_list(text)      # 分詞
    word_list = tokenize(word_list)      # 去除 標點符號
    word_list = remove_noise(word_list)  # 去除 贅詞
    return word_list

# 從 corpus_json 資料夾，抓取 s1.json 、s2.json 、s3.json  檔案，進行組合。以下介紹檔案放置類型：
# s1.json ：動詞詞彙
# s2.json ：分類詞彙
# s3.json ：名稱詞彙
# 執行後建立：copurs_text.json 

def merge_corups():
    def file_read(file, mode):
        try:
            with open(file, mode, encoding="utf-8") as f:
                text = f.read()
                return text
        except IOError:
            print('Error: cannot open file')

    def add_corups(s):
        # 產生模型
        model = word2vec.Word2Vec(s, sg=1, size=70, iter=10, min_count=1, negative=10) 
        # 將模型存成 txt
        model.wv.save_word2vec_format('word2vec2_1.txt', binary = False) 
    
    view = file_read(r'00_Corpus_merge\corpus_json\s1.json', 'r').split('\n')
    eat = file_read(r'00_Corpus_merge\corpus_json2\s1.json', 'r').split('\n')
    live = file_read(r'00_Corpus_merge\corpus_json3\s1.json', 'r').split('\n')
    traffic = file_read(r'00_Corpus_merge\corpus_json4\s1.json', 'r').split('\n')
    
    s_lst = view + eat + live + traffic
    add_corups([s_lst])
    
# 載入 word_To_Vector 檔案，傳回：維度，向量資料
def load_WordVector():
    dim = 0
    word_vecs = {}
    
    with open('word2vec2_1.txt', encoding="utf-8") as f:
        for line in f:
        # 詞向量有512維,由word以及向量中的元素共513個
        # 以空格分隔組成詞向量檔案中一行
            tokens = line.strip().split()

            # txt中的第一列是兩個整數，分別代表有多少個詞以及詞向量維度
            if len(tokens) == 2:
                dim = int(tokens[1])
                continue
            #詞向量從第2列開始
            word = tokens[0] 
            vec = np.array([ float(t) for t in tokens[1:] ])
            word_vecs[word] = vec

    
    return dim,word_vecs

# 抓取 單字 的 向量值，回傳 平均向量值
def set_word_vector(word_vecs, dim):
    def word_feature(text, wv=word_vecs, dim=dim):
        # 初始化
        emb_cnt = 0
        avg_emb = np.zeros((dim,))
        for word in clean_text(text):
            if word in wv.keys():
                avg_emb += wv[word]
                emb_cnt += 1
        avg_emb /= emb_cnt
        
        return avg_emb
    
    return word_feature

# 計算問題 與 答案 間的 向量關係
def cosine_similarity(x, y):
    return np.dot(x, y) / (np.sqrt(np.dot(x, x)) * np.sqrt(np.dot(y, y)))
