from config import Config
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,    
    MessagingApiBlob,
    ReplyMessageRequest,
    URIAction,
    MessageAction,
    PostbackAction,
    RichMenuSwitchAction,
    QuickReply,
    QuickReplyItem,
    RichMenuRequest,
    ShowLoadingAnimationRequest
)
import random
import json
import re

config = Config()
configuration = config.configuration
firebaseService = config.firebaseService

class LineBotHelper:
    @staticmethod
    def get_user_info(user_id: str):
        """Returns 使用者資訊
        list: [使用者名稱, 使用者大頭貼]
        """
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            user_info = line_bot_api.get_profile(user_id)
            return [user_id, user_info.display_name, user_info.picture_url, user_info.status_message, user_info.language]
        
    @staticmethod
    def reply_message(event, messages: list):
        """
        回覆多則訊息
        """
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=messages
                )
            )

    @staticmethod
    def generate_id(k: int=20):
        """
        生成ID
        """
        CHARS='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        return ''.join(random.choices(CHARS, k=k))
    
    @staticmethod
    def show_loading_animation(event):
        """
        顯示載入動畫
        """
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.show_loading_animation(ShowLoadingAnimationRequest(chatId=event.source.user_id))
        
    @staticmethod
    def replace_variable(text: str, variable_dict: dict):
        """Returns 取代變數後的文字 e.g. {{semester}} -> 代表semester是一個變數，取代成variable_dict中key為semester的值
        str: 取代變數後的文字
        """
        def replace(match):
            key = match.group(1)
            return str(variable_dict.get(key, match.group(0)))

        # 匹配 {{variable}} 的正規表達式
        pattern = r'\{\{([a-zA-Z0-9_]*)\}\}'
        replaced_text = re.sub(pattern, replace, text)
        return replaced_text
    
    @staticmethod
    def create_action(action: dict):
        """Returns
        Action: action 物件
        """
        if action['type'] == 'uri':
            return URIAction(uri=action.get('uri'))
        elif action['type'] == 'message':
            return MessageAction(text=action.get('text'), label=action.get('label'))
        elif action['type'] == 'postback':
            return PostbackAction(data=action.get('data'), label=action.get('label'), display_text=action.get('displayText'))
        elif action['type'] == 'richmenuswitch':
            return RichMenuSwitchAction(
                rich_menu_alias_id=action.get('richMenuAliasId'),
                data=action.get('data')
            )
        else:
            raise ValueError('Invalid action type')

class QuickReplyHelper:
    @staticmethod
    def create_quick_reply(quick_reply_data: list[dict]):
        """Returns
        QuickReply: 快速回覆選項
        """
        return QuickReply(
            items=[QuickReplyItem(action=LineBotHelper.create_action(json.loads(item))) for item in quick_reply_data]
        )

class RichmenuHelper:
    @staticmethod
    def create_richmenu_():
        """創建圖文選單"""
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_blob_api = MessagingApiBlob(api_client)

            # Step 1. 創建圖文選單(圖文選單的大小、名稱、聊天室的文字、按鈕的區域)
            rich_menu_str = firebaseService.get_data('rich_menu', 'main').get('richmenu')
            # 創建的時候會回傳 rich_menu_id
            rich_menu_id = line_bot_api.create_rich_menu(
                rich_menu_request=RichMenuRequest.from_json(rich_menu_str)
            ).rich_menu_id

            # Step 2. 設定 Rich Menu 的圖片
            # 方式一: 使用 URL
            # rich_menu_url = "https://example.com/richmenu.png"
            # response = requests.get(rich_menu_url)
            # line_bot_blob_api.set_rich_menu_image(
            #     rich_menu_id=rich_menu_id,
            #     body=response.content,
            #     _headers={'Content-Type': 'image/png'}
            # )

            # 方式二: 使用本地端的圖片
            with open('static/images/richmenu.png', 'rb') as image:
                line_bot_blob_api.set_rich_menu_image(
                    rich_menu_id=rich_menu_id,
                    body=bytearray(image.read()),
                    _headers={'Content-Type': 'image/png'}
                )

            # Step3. 設定預設的圖文選單
            line_bot_api.set_default_rich_menu(rich_menu_id)
    
    @staticmethod
    def delete_all_richmenu():
        """刪除圖文選單"""
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            richmenu_list = line_bot_api.get_rich_menu_list()
            for richmenu in richmenu_list.richmenus:
                line_bot_api.delete_rich_menu(richmenu.rich_menu_id)
                print(richmenu.rich_menu_id)