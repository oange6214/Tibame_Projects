import glob
import json
from linebot import LineBotApi
from linebot.models import RichMenu

# 載入安全設定檔
channel_access_token = "3Uf9I+axbRjbtGlAJsPlebp416XLLr8QSKM9ctFwng5QLQ973hyuqFT7n1gVOe7xf+h0puIeNBy+yGsJ/pLhYL6KnU9FNRcqn39dT/4h5k7OZ2zm7sF1helAYHh1z+gcL9mGaC1AI6gfmVWur1sHBgdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(channel_access_token)

# 讀取選單 json、jpg
json_path_list = glob.glob(r'.\menu\*.json')
jpg_path_list = glob.glob(r'.\menu\*.jpg')

# 檔案上傳順序確認
print(json_path_list)
print(jpg_path_list)

# 依序上傳
for index in range(len(json_path_list)):
    print(f'上傳第 {index + 1} 組')
    # 創建菜單，取得 menuId
    try:
        lineRichMenuId = line_bot_api.create_rich_menu(rich_menu=RichMenu.new_from_json_dict(json.load(open(json_path_list[index], 'r', encoding='utf8'))))
        print(lineRichMenuId)
    except:
        print('建立 json 失敗')

    # 上傳照片至該id
    try:
        with open(jpg_path_list[index], 'rb') as f:
            set_image_response = line_bot_api.set_rich_menu_image(lineRichMenuId, 'image/jpeg', f)
    except:
        print('上傳失敗')

print('上傳完成')