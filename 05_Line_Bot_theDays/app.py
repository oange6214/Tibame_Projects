from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    PostbackEvent, FollowEvent, MessageEvent,
    TextMessage, TextSendMessage, ImageMessage, VideoMessage, AudioMessage, AudioSendMessage, FlexSendMessage,
    ImagemapSendMessage,
    MessageAction, URIAction, PostbackAction, DatetimePickerAction, CameraAction, CameraRollAction, LocationAction,
    QuickReply, QuickReplyButton,
    BubbleContainer, CarouselContainer
)

import pymysql
import pymysql.cursors

from googletrans import Translator
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
from urllib.parse import parse_qs
import tempfile, os, json
import datetime
import pytz

try:
    from theDays import crawler  # heroku
except:
    import crawler

# 載入 line secret key
secretFileContentJson = json.load(open("./line_secret_key", "r", encoding="utf8"))

# 設定 Server 啟用細節
app = Flask(__name__, static_url_path="/images", static_folder="./images/")

# 生成實體物件
line_bot_api = LineBotApi(secretFileContentJson.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(secretFileContentJson.get("LINE_CHANNEL_SECRET"))

total_function = {
    '翻譯': False,
    '天氣': False,
    '樂透': False,
    '發票': False,
    '油價': False,
    '介紹': False
}

# 翻譯用 快速按鈕
en_postback = QuickReplyButton(action=PostbackAction(label="英文", data="langs=en"))
fr_postback = QuickReplyButton(action=PostbackAction(label="法文", data="langs=fr"))
ja_postback = QuickReplyButton(action=PostbackAction(label="日文", data="langs=ja"))
ko_postback = QuickReplyButton(action=PostbackAction(label="韓文", data="langs=ko"))
th_postback = QuickReplyButton(action=PostbackAction(label="泰文", data="langs=th"))
vi_postback = QuickReplyButton(action=PostbackAction(label="越文", data="langs=vi"))

## 設計 QuickReplyButton 的 List
quickReplyList = QuickReply(items=[en_postback, fr_postback, ja_postback, ko_postback, th_postback, vi_postback])

def get_time():
    pacific = pytz.timezone('Asia/Taipei')
    d = datetime.datetime.now(pacific)

    return d.strftime('%Y-%m-%d %H:%M:%S')

## 發票 中獎號碼，當期前三個月資訊
def flex_invoice():
    inv = crawler.invoice()
    old = inv.show(3)

    invoice_flex_container_json = json.load(open("container/invoice.json", 'r', encoding="utf-8"))

    for i in range(3):
        invoice_flex_container_json["contents"][i]["header"]["contents"][0]["text"] = old[i][0]
        invoice_flex_container_json["contents"][i]["body"]["contents"][0]["contents"][1]["text"] = old[i][1][0]
        invoice_flex_container_json["contents"][i]["body"]["contents"][2]["contents"][1]["text"] = old[i][1][1]
        invoice_flex_container_json["contents"][i]["body"]["contents"][4]["contents"][1]["text"] = old[i][1][2]
        invoice_flex_container_json["contents"][i]["body"]["contents"][5]["contents"][1]["text"] = old[i][1][3]
        invoice_flex_container_json["contents"][i]["body"]["contents"][6]["contents"][1]["text"] = old[i][1][4]
        invoice_flex_container_json["contents"][i]["body"]["contents"][8]["contents"][1]["text"] = ' '.join(
            old[i][1][5:])

    invoice_carousel_content = CarouselContainer.new_from_json_dict(invoice_flex_container_json)
    flex_bubble_send_message = FlexSendMessage(alt_text="invoice", contents=invoice_carousel_content)

    return flex_bubble_send_message


## 彩券藉由爬蟲所得資料，資料放入對應 bubble 模板中
def flex_lotto(type):
    lo = crawler.lotto()
    lotto_dict = lo.result_all(type)

    lotto_flex_container_json = json.load(open("container/lotto.json", 'r', encoding="utf-8"))

    lotto_flex_container_json["header"]["contents"][0]["text"] = lotto_dict["遊戲"]
    lotto_flex_container_json["body"]["contents"][0]["contents"][1]["text"] = lotto_dict["期別"]
    if type == 0 or type == 1:
        pass
        lotto_flex_container_json["body"]["contents"][2]["contents"][1]["text"] = ' '.join(lotto_dict['本期中獎號碼'][:-1])
        lotto_flex_container_json["body"]["contents"][2]["contents"][2]["text"] = lotto_dict['本期中獎號碼'][-1]
    else:
        lotto_flex_container_json["body"]["contents"][2]["contents"][1]["text"] = ' '.join(lotto_dict['本期中獎號碼'])
        lotto_flex_container_json["body"]["contents"][2]["contents"][2]["text"] = ' '

    lotto_flex_container_json["body"]["contents"][4]["contents"][1]["text"] = lotto_dict["開獎日期"]
    lotto_flex_container_json["body"]["contents"][5]["contents"][1]["text"] = lotto_dict["兌獎日期"]

    lotto_bubble_container = BubbleContainer.new_from_json_dict(lotto_flex_container_json)
    flex_bubble_send_message = FlexSendMessage(alt_text="Weather", contents=lotto_bubble_container)

    return flex_bubble_send_message


## 天氣藉由爬蟲所得資料，資料放入對應 bubble 模板中
def flex_weather(city):
    cw = crawler.Weather(city)
    cw.setData()
    weather_data = cw.getData()

    weather_flex_container_json = json.load(open("container/weather.json", 'r', encoding="utf-8"))
    weather_flex_container_json["header"]["contents"][0]["text"] = weather_data[0]
    weather_flex_container_json["body"]["contents"][0]["text"] = weather_data[1]
    weather_flex_container_json["body"]["contents"][1]["text"] = str((int(weather_data[2]) + int(weather_data[3])) // 2)
    weather_flex_container_json["body"]["contents"][2]["contents"][0]["text"] = '↑' + weather_data[2]
    weather_flex_container_json["body"]["contents"][2]["contents"][1]["text"] = '↓' + weather_data[3]
    weather_flex_container_json["body"]["contents"][3]["text"] = '降雨機率: ' + weather_data[3]
    weather_flex_container_json["footer"]["contents"][0]["text"] = weather_data[4]

    weather_bubble_container = BubbleContainer.new_from_json_dict(weather_flex_container_json)
    flex_bubble_send_message = FlexSendMessage(alt_text="Weather", contents=weather_bubble_container)

    return flex_bubble_send_message


## 油價藉由爬蟲所得資料，資料放入對應 bubble 模板中
def flex_oil():
    oil_obj = crawler.oil()
    oil_data = oil_obj.getData()

    oil_flex_container_json = json.load(open("container/oil.json", 'r', encoding="utf-8"))
    for i in range(2):
        oil_flex_container_json["contents"][i]["header"]["contents"][0]["text"] = oil_data[i][0]
        oil_flex_container_json["contents"][i]["body"]["contents"][0]["contents"][1]["text"] = str(oil_data[i][1])
        oil_flex_container_json["contents"][i]["body"]["contents"][2]["contents"][1]["text"] = str(oil_data[i][2])
        oil_flex_container_json["contents"][i]["body"]["contents"][4]["contents"][1]["text"] = str(oil_data[i][3])
        oil_flex_container_json["contents"][i]["body"]["contents"][6]["contents"][1]["text"] = str(oil_data[i][4])
        oil_flex_container_json["contents"][i]["footer"]["contents"][0]["text"] = oil_data[i][6] + '    ' + oil_data[i][
            5]

    oil_carousel_content = CarouselContainer.new_from_json_dict(oil_flex_container_json)
    flex_bubble_send_message = FlexSendMessage(alt_text="oil", contents=oil_carousel_content)

    return flex_bubble_send_message


# 選擇 連結 圖文選單
def choose_image_map(event, type):
    with open("./menu/rich_menu.csv", "r", encoding="utf-8") as f:
        linkRichMenuId = f.read().split(',')[type]

    line_bot_api.link_rich_menu_to_user(event.source.user_id, linkRichMenuId)


def sendtodatabase(params_tuple):
    connection = pymysql.connect(host=os.environ.get('CLEARDB_DATABASE_HOST'),
                                 user=os.environ.get('CLEARDB_DATABASE_USER'),
                                 password=os.environ.get('CLEARDB_DATABASE_PASSWORD'),
                                 db=os.environ.get('CLEARDB_DATABASE_DB'),
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection.cursor() as cursor:
        # 讀取資料庫，確認使用者 是否關注過
        sql = "SELECT `user_id` FROM `users` WHERE `user_id`=%(user_id)s;"
        params = {
            "user_id": params_tuple[1],
        }
        cursor.execute(sql, params)
        result = cursor.fetchone()
        print(result)
    if result == None:
        with connection.cursor() as cursor:
            # 新增 新使用者的 ID
            sql = "INSERT INTO `users` (`display_name`, `user_id`, `create_time`) VALUES (%(display_name)s, %(user_id)s, %(create_time)s);"
            params = {
                "display_name": params_tuple[0],
                "user_id": params_tuple[1],
                "create_time": get_time()
            }
            cursor.execute(sql, params)
        print('增加使用者', params)

    connection.commit()

def update_time(params_tuple):
    connection = pymysql.connect(host=os.environ.get('CLEARDB_DATABASE_HOST'),
                                 user=os.environ.get('CLEARDB_DATABASE_USER'),
                                 password=os.environ.get('CLEARDB_DATABASE_PASSWORD'),
                                 db=os.environ.get('CLEARDB_DATABASE_DB'),
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection.cursor() as cursor:
        # 更新 使用者 登入時間
        sql = "UPDATE `users` SET `display_name`=%(display_name)s, `last_interation` = %(last_interation)s WHERE `user_id`=%(user_id)s;"
        params = {
            "display_name": params_tuple[0],
            "user_id": params_tuple[1],
            "last_interation": get_time()
        }
        cursor.execute(sql, params)
    connection.commit()

def get_dest_langs(user_id):
    connection = pymysql.connect(host=os.environ.get('CLEARDB_DATABASE_HOST'),
                                 user=os.environ.get('CLEARDB_DATABASE_USER'),
                                 password=os.environ.get('CLEARDB_DATABASE_PASSWORD'),
                                 db=os.environ.get('CLEARDB_DATABASE_DB'),
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        # 讀取資料庫，確認使用者 是否關注過
        sql = "SELECT `dest_langs` FROM `users` WHERE `user_id`=%(user_id)s;"
        params = {
            "user_id": user_id,
        }
        cursor.execute(sql, params)
        result = cursor.fetchone()
        connection.commit()
        return result["dest_langs"]

def set_dest_langs(user_id, dest_langs):
    connection = pymysql.connect(host=os.environ.get('CLEARDB_DATABASE_HOST'),
                                 user=os.environ.get('CLEARDB_DATABASE_USER'),
                                 password=os.environ.get('CLEARDB_DATABASE_PASSWORD'),
                                 db=os.environ.get('CLEARDB_DATABASE_DB'),
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    with connection.cursor() as cursor:
        # 更新 使用者 登入時間
        sql = "UPDATE `users` SET `dest_langs` = %(dest_langs)s WHERE `user_id`=%(user_id)s;"
        params = {
            "user_id": user_id,
            "dest_langs": dest_langs
        }
        cursor.execute(sql, params)
    connection.commit()

# 啟動 server 對外接口，使 Line 能丟消息進來
@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# 關注時候
@handler.add(FollowEvent)
def process_follow_event(event):
    # 擷取關注者的資料
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_dict = vars(user_profile)
    data_tuple = (
        user_dict["display_name"],
        user_dict["user_id"],
    )
    # 儲存 到 資料庫
    sendtodatabase(data_tuple)

    choose_image_map(event, 0)


# 文字消息接收
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    dest_langs = get_dest_langs(event.source.user_id)

    # 根據 根據對話判斷使用者活動時間，並更新使用時間
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_dict = vars(user_profile)
    data_tuple = (
        user_dict["display_name"],
        user_dict["user_id"],
    )
    update_time(data_tuple)

    text = event.message.text

    if text[0] not in '@#:':
        # 主圖文選單開頭都為 @
        trans = Translator()
        trans_text = trans.translate(event.message.text, src='zh-TW', dest=dest_langs).extra_data['translation'][0][0]

        tts = gTTS(trans_text, lang=dest_langs)
        tts_url = tts.get_urls()[0]

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=trans_text),
                AudioSendMessage(
                    original_content_url=tts_url,
                    duration=100000
                )
            ]
        )
    elif text == "@作者":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='不要認識的好')
        )
    elif text == "@樂透":
        choose_image_map(event, 1),
    elif text == '#回主選單':
        choose_image_map(event, 0)
    else:
        if text == '@語言':
            flex_container = TextSendMessage(text='請選擇目標語言', quick_reply=quickReplyList)
        elif text == "@天氣":
            flex_container = ImagemapSendMessage.new_from_json_dict(
                json.load(open("./container/weather_map.json", 'r', encoding='utf8')))
        elif text == "@油價":
            flex_container = flex_oil()
        elif text == "@發票":
            flex_container = flex_invoice()
        elif text == '#威力彩':
            flex_container = flex_lotto(0)
        elif text == '#大樂透':
            flex_container = flex_lotto(1)
        elif text == '#今彩539':
            flex_container = flex_lotto(2)
        elif text == '#雙贏彩':
            flex_container = flex_lotto(3)
        elif text == '#3星彩':
            flex_container = flex_lotto(4)
        elif text == '#4星彩':
            flex_container = flex_lotto(5)
        elif text == '#38樂合彩':
            flex_container = flex_lotto(6)
        elif text == '#49樂合彩':
            flex_container = flex_lotto(7)
        elif text == '#39樂合彩':
            flex_container = flex_lotto(8)
        elif text[:2] == '::':
            flex_container = flex_weather(text[2:])

        try:
            line_bot_api.reply_message(
                event.reply_token,
                flex_container
            )
        except:
            print('沒此功能')




#  [語音接收]，流程: 接收語音 >>> 轉檔 >>> 語音轉文字 >>> 文字翻譯 >>> 文字轉語音 >>> 傳送語音
@handler.add(MessageEvent, message=AudioMessage)
def handle_content_message(event):
    dest_langs = get_dest_langs(event.source.user_id)

    # 接收使用者語音
    r = sr.Recognizer()
    message_content = line_bot_api.get_message_content(event.message.id)
    try:
        # 將 line 語音轉 SR 可用格式 (m4a 轉 wav)
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            for chunk in message_content.iter_content():
                tf.write(chunk)
            tempfile_path = tf.name
        try:
            # 利用 ffmpeg 轉檔
            AudioSegment.converter = '../../ffmpeg.exe'  # 本機使用
            sound = AudioSegment.from_file_using_temporary_files(tempfile_path)
        except:
            AudioSegment.converter = '/app/vendor/ffmpeg/ffmpeg'  # (Heruku版)
            sound = AudioSegment.from_file_using_temporary_files(tempfile_path)
        path = os.path.splitext(tempfile_path)[0] + '.wav'
        sound.export(path, format="wav")
        with sr.AudioFile(path) as source:
            audio = r.record(source)

    except Exception as e:
        t = '音訊有問題'
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=t))
    os.remove(path)
    # 語音 轉 文字
    text = r.recognize_google(audio, language='zh-TW')

    # 翻譯處理
    trans = Translator()
    trans_text = trans.translate(text, dest=dest_langs).extra_data['translation'][0][0]
    # 文字 轉 語音
    tts = gTTS(trans_text, lang=dest_langs)
    tts_url = tts.get_urls()[0]

    # 回覆語音訊息
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text=trans_text),
            AudioSendMessage(
                original_content_url=tts_url,
                duration=100000
            )
        ]
    )


# 切換翻譯語言
@handler.add(PostbackEvent)
def process_postback_event(event):

    query_string_dict = parse_qs(event.postback.data)
    dest_langs = query_string_dict['langs'][0]

    set_dest_langs(event.source.user_id, dest_langs)    # 紀錄個別使用者切換的語言

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='切換至' + query_string_dict['langs'][0]),
    )


if __name__ == "__main__":
    # app.run(host='0.0.0.0')  # 本機使用

    # Application 運行（heroku版）
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
