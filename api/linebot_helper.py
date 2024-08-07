from config import Config
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    URIAction,
    MessageAction,
    PostbackAction,
    RichMenuSwitchAction,
    QuickReply,
    QuickReplyItem,
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