from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    PostbackEvent, FollowEvent, MessageEvent,
    TextMessage, TextSendMessage, ImageMessage, VideoMessage,
    CameraAction, CameraRollAction,
    QuickReply, QuickReplyButton
)

from flask import Flask, request
import pymysql
import pymysql.cursors
import os, json, pytz, time, datetime
import efficientnet.tfkeras as efn

from tensorflow.keras.preprocessing import image
import tensorflow as tf
import numpy as np

model = tf.keras.models.load_model('catus_04.h5')

# 載入 line secret key
secretFileContentJson = json.load(open("./line_secret_key", "r", encoding="utf8"))

# 設定 Server 啟用細節
app = Flask(__name__, static_url_path="/images", static_folder="./images/")

# 生成實體物件
line_bot_api = LineBotApi(secretFileContentJson.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(secretFileContentJson.get("LINE_CHANNEL_SECRET"))

# 創建 QuickReplyButton
## 點擊後，開啟相機
cameraQuickReplyButton = QuickReplyButton(
    action=CameraAction(label="拍照")
)

## 點擊後，切換至照片相簿選擇
cameraRollQRB = QuickReplyButton(
    action=CameraRollAction(label="相簿")
)

## 設計 QuickReplyButton 的 List
quickReplyList = QuickReply(
    items = [cameraQuickReplyButton, cameraRollQRB]
)

## 將 quickReplyList 塞入 TextSendMessage 中
quickReplyTextSendMessage = TextSendMessage(text='請選擇功能', quick_reply=quickReplyList)

# 建立 quickReply 關鍵字字典
template_message_dict = {
    "@功能": quickReplyTextSendMessage
}

# 取得現在時間
def get_time():
    pacific = pytz.timezone('Asia/Taipei')
    d = datetime.datetime.now(pacific)

    return d.strftime('%Y-%m-%d %H:%M:%S')


# 傳送資料到資料庫
def sendtodatabase(params_tuple):
    connection = pymysql.connect(host='us-cdbr-east-02.cleardb.com',
                                 user='b26f228760f086',
                                 password='805c2a93',
                                 db='heroku_41905e5655dcfb6',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    # 查詢資料庫，檢查使用者是否已經儲存
    with connection.cursor() as cursor:
        # 讀取資料庫，確認使用者 是否關注過
        sql = "SELECT `user_id` FROM `users` WHERE `user_id`=%(user_id)s;"
        params = {
            "user_id": params_tuple[1],
        }
        cursor.execute(sql, params)
        result = cursor.fetchone()
        print(result)

    # 如果資料庫沒有使用者，則建立使用者資料
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

# 更新使用者操作時間
def update_time(params_tuple):
    connection = pymysql.connect(host='us-cdbr-east-02.cleardb.com',
                                 user='b26f228760f086',
                                 password='805c2a93',
                                 db='heroku_41905e5655dcfb6',
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

    # 選擇 連結 圖文選單
    with open("./menu/rich_menu.csv", "r", encoding="utf-8") as f:
        linkRichMenuId = f.read().split(',')[0]
        line_bot_api.link_rich_menu_to_user(event.source.user_id, linkRichMenuId)
        print(event.source.user_id, linkRichMenuId)

# 接收文字
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        [
            # TextSendMessage(text=text),
            template_message_dict.get(event.message.text)
        ]
    )

    # 根據 根據對話判斷使用者活動時間，並更新使用時間
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_dict = vars(user_profile)
    data_tuple = (
        user_dict["display_name"],
        user_dict["user_id"],
    )
    update_time(data_tuple)

def toArray(imgPath):
    IMAGE_SIZE = 224

    img = image.load_img(imgPath, target_size=(IMAGE_SIZE, IMAGE_SIZE))
    x = np.array(img)
    x = np.expand_dims(x, axis=0)
    x = x / 127.5 - 1

    return np.array(x)

# 接收圖片，傳送文字
@handler.add(MessageEvent, message=ImageMessage)
def handle_content_message(event):
    start = time.time()
    message_content = line_bot_api.get_message_content(event.message.id)

    # message content to jpg
    image_path = os.path.join('menu', f'{event.message.id}.jpg')
    with open(image_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    # load jpg path to array
    pre = toArray(image_path)
    # predict picture
    pred = np.argmax(model.predict(pre), axis=-1)[0]

    if pred < 10:
        to_str = '0' + str(pred)
    else:
        to_str = str(pred)

    type_name = {
        '00': '熊童子',
        '01': '心葉毬蘭',
        '02': '八千代',
        '03': '乙女心',
        '04': '不死鳥',
        '05': '月兔耳',
        '06': '火祭',
        '07': '白鳥帽子',
        '08': '金鯱',
        '09': '金晃丸',
        '10': '紅蘋果椒草',
        '11': '虹之玉',
        '12': '桃太郎',
        '13': '野玫瑰之精',
        '14': '紫太陽',
        '15': '超太白十二之卷',
        '16': '綠珊瑚',
        '17': '銀之鈴',
        '18': '銀月',
        '19': '朧月',
    }

    predict_message = '時間: {:.2f}, 類別: {:s}'.format(time.time() - start, type_name[to_str])

    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text= predict_message)
        ]
    )

    # 根據 根據對話判斷使用者活動時間，並更新使用時間
    user_profile = line_bot_api.get_profile(event.source.user_id)
    user_dict = vars(user_profile)
    data_tuple = (
        user_dict["display_name"],
        user_dict["user_id"],
    )
    update_time(data_tuple)

    os.remove(image_path)

if __name__ == "__main__":
    # app.run(host='0.0.0.0')  # 本機使用

    # Application 運行（heroku版）
    app.run(host= '0.0.0.0',
            debug=True,
            port= int(os.environ.get('PORT', 8000)))