from config import Config
import task
from api.linebot_helper import LineBotHelper, QuickReplyHelper, RichmenuHelper
from flask import Flask, request, abort
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    FollowEvent,
    UnfollowEvent,
    MessageEvent,
    TextMessageContent,
    PostbackEvent
)
from linebot.v3.messaging import (
    TextMessage,
    ImageMessage,
    FlexMessage,
    FlexContainer,
)
import random

UPLOAD_FOLDER = 'static'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

config = Config()
configuration = config.configuration
line_handler = config.handler
spreadsheetService = config.spreadsheetService
firebaseService = config.firebaseService

# 第一次沒有音檔，先生成音檔
# task.generate_speech()

# 處理Richmenu
# RichmenuHelper.delete_all_richmenu()
# RichmenuHelper.create_richmenu_()

# domain root
@app.route('/')
def home():
    return 'Learning Bot!'

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# 處理加入好友事件
@line_handler.add(FollowEvent)
def handle_follow(event):
    LineBotHelper.show_loading_animation(event)
    LineBotHelper.reply_message(event, [TextMessage(text='歡迎使用此服務！\n請輸入功能文字或點擊下方功能選單！')])
    user_info = LineBotHelper.get_user_info(event.source.user_id)
    spreadsheetService.add_record('user_info', user_info)

@line_handler.add(UnfollowEvent)
def handle_unfollow(event):
    user_id = event.source.user_id
    # 刪除使用者資訊
    wks = spreadsheetService.sh.worksheet_by_title('user_info')
    user_ids = wks.get_col(1)
    row_index =  user_ids.index(user_id) + 1
    spreadsheetService.delete_row('user_info', row_index)

@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """
    Handle文字訊息事件
    """
    try:
        # 取得使用者文字訊息
        user_msg = event.message.text
        user_id = event.source.user_id
        temp = firebaseService.get_data('temp', user_id)

        if user_msg == '文章':
            LineBotHelper.show_loading_animation(event)
            task.show_articles(event)
            return
        elif temp:
            if temp.get('action') == '2':
                LineBotHelper.show_loading_animation(event)
                # 查詢單字
                task.lookup_word(event, temp.get('article_id'))
                return
    except Exception as e:
        print(e)
        LineBotHelper.reply_message(event, [TextMessage(text='發生錯誤，請聯繫管理員！')])
    
    
@line_handler.add(PostbackEvent)
def handle_postback(event):
    """
    Handle Postback事件
    """
    try:
        LineBotHelper.show_loading_animation(event)
        postback_data = event.postback.data
        # 如果有datetimpicker的參數，才會有postback_params
        postback_params = event.postback.params
        params = postback_params if postback_params else {}
        if '=' in postback_data:
            # 重新拆解Postback Data的參數
            for param in postback_data.split('&'):
                key, value = param.split('=')
                params[key] = value
        
        user_id = event.source.user_id
        # 文章ID
        article_id = params.get('article_id')
        # 哪一個功能
        action = params.get('action')
        # 根網址
        root_url = request.url_root.replace('http', 'https')
        # 使用者暫存資料
        temp = firebaseService.get_data('temp', user_id)
        article_id = article_id if article_id else (temp.get('article_id') if temp else None)
        # if temp and (action == '1' or action == '3'):
        #     # 刪除暫存資料
        #     firebaseService.delete_data('temp', user_id)

        # 如果沒有文章ID，則顯示文章清單
        # if not (article_id or (temp and temp.get('article_id'))):
        if not article_id:
            task.show_articles(event)
            return

        if action == '1':
            firebaseService.add_data('temp', user_id, {'article_id': article_id, 'action': '1'})
            paragraph = params.get('paragraph')
            if paragraph:
                # 朗讀段落
                task.read_paragraph(event, root_url, article_id, int(paragraph))
                spreadsheetService.add_record('log', [user_id, "AA", article_id, int(paragraph), event.timestamp])
                return
            else:
                # 選擇段落
                paragraph_amount = len(firebaseService.get_data('articles', f"article_{article_id}").get('paragraphs'))
                quick_reply_data = firebaseService.get_data('quick_reply', 'article').get('paragraph')
                for i, text in enumerate(quick_reply_data.get('actions')[:paragraph_amount]):
                    quick_reply_data.get('actions')[i] = LineBotHelper.replace_variable(text, {'article_id': article_id})
                LineBotHelper.reply_message(event, [TextMessage(text=quick_reply_data.get('text'), quickReply=QuickReplyHelper.create_quick_reply(quick_reply_data.get('actions')[:paragraph_amount]))])
                return
        elif action == '2':
            # 單字查詢
            firebaseService.add_data('temp', user_id, {'article_id': article_id, 'action': '2'})
            LineBotHelper.reply_message(event, [TextMessage(text='請輸入要查詢的單字！若要停止查詢，請選擇其他功能！')])
            return
        elif action == '3':
            firebaseService.add_data('temp', user_id, {'article_id': article_id, 'action': '3'})
            phrase_id = params.get('phrase_id')
            if phrase_id:
                # 顯示片語解釋
                phrase = firebaseService.get_data('articles', f"article_{article_id}").get('phrases')[int(phrase_id)-1]
                explanation_url = phrase.get('explanation_url')
                LineBotHelper.reply_message(event, [ImageMessage(original_content_url=explanation_url, preview_image_url=explanation_url)])
                spreadsheetService.add_record('log', [user_id, "IP", article_id, phrase.get('phrase'), event.timestamp])
                return
            else:
                # 顯示片語清單
                task.show_phrases(event, article_id)
                return
        elif action == '4':
            question_no = params.get('no')
            if question_no:
                question_no = int(question_no)
                # 使用者的答案
                answer = params.get('answer').lower()

                # 從temp取得題目
                temp_data = firebaseService.get_data('temp', user_id)
                quiz_questions = temp_data.get('questions')
                if not quiz_questions:
                    LineBotHelper.reply_message(event, [TextMessage(text='若要進行測驗，請重新點選閱讀測驗！')])
                    return

                # 判斷答案是否正確
                last_quiz_question = quiz_questions[question_no - 1]
                is_correct = answer == last_quiz_question.get('answer').lower()
                answer_line_flex_str = task.generate_answer_line_flex(last_quiz_question, is_correct)

                # 記錄該題作答(選擇的答案人數+1)
                last_quiz_question_type = last_quiz_question.get('type')
                task.create_answer_record(user_id, temp_data.get('quiz_id'), last_quiz_question, answer)
                if is_correct:
                    temp_data['correct_amount'][last_quiz_question_type] += 1
                    temp_data['correct_amount']['total'] += 1

                if question_no < temp_data.get('qustion_amount').get('total'):
                    question_line_flex_str = task.generate_question_line_flex(quiz_questions[question_no], question_no)
                    firebaseService.update_data('temp', user_id, {'no': question_no + 1, 'correct_amount': temp_data.get('correct_amount')})
                    LineBotHelper.reply_message(event, [
                        FlexMessage(alt_text='測驗解答', contents=FlexContainer.from_json(answer_line_flex_str)),
                        FlexMessage(alt_text='測驗題目', contents=FlexContainer.from_json(question_line_flex_str))
                    ])
                    return
                else:
                    # 生成測驗結果
                    result_line_flex_str = task.generate_quiz_result({
                        'article_id': last_quiz_question.get('article_id'),
                        'total_correct_amount': temp_data.get('correct_amount').get('total'),
                        'word_correct_amount': temp_data.get('correct_amount').get('word'),
                        'phrase_correct_amount': temp_data.get('correct_amount').get('phrase'),
                        'comprehension_correct_amount': temp_data.get('correct_amount').get('comprehension'),
                        'total_amount': temp_data.get('qustion_amount').get('total'),
                        'word_amount': temp_data.get('qustion_amount').get('word'),
                        'phrase_amount': temp_data.get('qustion_amount').get('phrase'),
                        'comprehension_amount': temp_data.get('qustion_amount').get('comprehension')
                    })
                    firebaseService.delete_data('temp', user_id)
                    LineBotHelper.reply_message(event, [
                        FlexMessage(alt_text='測驗解答', contents=FlexContainer.from_json(answer_line_flex_str)),
                        FlexMessage(alt_text='測驗結果', contents=FlexContainer.from_json(result_line_flex_str))
                    ])
                    spreadsheetService.add_record('log', [user_id, "RE", last_quiz_question.get('article_id'), temp_data.get('quiz_id'), event.timestamp])
                    return
            else:
                # 閱讀測驗
                QUESTION_AMOUNT = {
                    'total': 5,
                    'word': 3,
                    'phrase': 1,
                    'comprehension': 1
                }
                questions = spreadsheetService.get_worksheet_data('quiz')
                questions = [qustion for qustion in questions if qustion.get('article_id') == int(article_id)]
                quiz_questions = []
                for question_type, amount in QUESTION_AMOUNT.items():
                    if question_type == 'total':
                        continue
                    quiz_questions.extend(random.sample([question for question in questions if question.get('type') == question_type], amount))
                data = {
                    'action': '4',
                    'article_id': article_id,
                    'no': 1,
                    'questions': quiz_questions,
                    'qustion_amount': QUESTION_AMOUNT,
                    'correct_amount': {
                        'total': 0,
                        'word': 0,
                        'phrase': 0,
                        'comprehension': 0
                    },
                    'quiz_id': LineBotHelper.generate_id()
                }
                firebaseService.add_data('temp', user_id, data)
                line_flex_str = task.generate_question_line_flex(quiz_questions[0], 0)
                LineBotHelper.reply_message(event, [FlexMessage(alt_text='測驗題目', contents=FlexContainer.from_json(line_flex_str))])
                return
        else:
            # 選擇文章後，顯示文章功能選單
            if article_id:
                firebaseService.add_data('temp', user_id, {'article_id': article_id})
                line_flex_str = firebaseService.get_data('line_flex', 'article').get('select')
                article_title = firebaseService.get_data('articles', f"article_{article_id}").get('title')
                line_flex_str = LineBotHelper.replace_variable(line_flex_str, {'article_id': article_id, 'article_title': article_title})
                LineBotHelper.reply_message(event, [FlexMessage(alt_text='功能選單', contents=FlexContainer.from_json(line_flex_str))])
                return
    except Exception as e:
        app.logger.error(e)
        LineBotHelper.reply_message(event, [TextMessage(text='發生錯誤，請聯繫管理員！')])

if __name__ == "__main__":
    app.run()