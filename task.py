from config import Config
from api.linebot_helper import LineBotHelper
from linebot.v3.messaging import (
    TextMessage,
    ImageMessage,
    AudioMessage,
    TemplateMessage,
    FlexMessage,
    FlexContainer,
    PostbackAction,
    ImageCarouselColumn,
    ImageCarouselTemplate
)
import librosa

config = Config()
spreadsheetService = config.spreadsheetService
firebaseService = config.firebaseService
azureService = config.azureService

# 顯示文章清單
def show_articles(event):
    line_flex_str = firebaseService.get_data('line_flex', 'article').get('main')
    LineBotHelper.reply_message(event, [FlexMessage(alt_text='請選擇文章', contents=FlexContainer.from_json(line_flex_str))])

# 朗讀文章
def read_paragraph(event, root_url, article_id, paragraph_id):
    paragraphs = firebaseService.get_data('articles', f"article_{article_id}").get('paragraphs')
    paragraph = paragraphs[paragraph_id-1]
    audio_url = f"{root_url}static/article_{article_id}/p{paragraph_id}.wav"
    audio_duration = paragraph.get('audio_duration')
    if not audio_duration:
        audio_duration = round(librosa.get_duration(path=f"static/article_{article_id}/p{paragraph_id}.wav")*1000)
        paragraphs[paragraph_id-1]['audio_duration'] = audio_duration
        firebaseService.update_data('articles', f"article_{article_id}", {'paragraphs': paragraphs})
    LineBotHelper.reply_message(event, [
        ImageMessage(original_content_url=paragraph.get('image_url'), preview_image_url=paragraph.get('image_url')),
        AudioMessage(original_content_url=audio_url, duration=audio_duration)
    ])

# 查詢單字
def lookup_word(event, article_id):
    user_id = event.source.user_id
    user_msg = event.message.text.strip().lower()
    words = firebaseService.get_data('articles', f"article_{article_id}").get('words')
    if user_msg in words:
        translation_urls = words.get(user_msg)
        LineBotHelper.reply_message(event, [ImageMessage(original_content_url=url, preview_image_url=url) for url in translation_urls])
        spreadsheetService.add_record('log', [user_id, "VS", article_id, ','.join(['1', user_msg]), event.timestamp])
    else:
        translation_text = azureService.azure_translate(user_msg, 'zh-Hant')
        LineBotHelper.reply_message(event, [TextMessage(text=translation_text)])
        spreadsheetService.add_record('log', [user_id, "VS", article_id, ','.join(['0', user_msg]), event.timestamp])

# 顯示片語清單
def show_phrases(event, article_id):
    phrases = firebaseService.get_data('articles', f"article_{article_id}").get('phrases')
    image_carousel_template = ImageCarouselTemplate(
        columns=[
            ImageCarouselColumn(
                image_url=phrase.get('cover_url'),
                action=PostbackAction(
                    label='查看解釋',
                    data=f"article_id={article_id}&action=3&phrase_id={i+1}",
                    display_text=phrase.get('phrase')
                )
            ) for i, phrase in enumerate(phrases)
        ]
    )
    LineBotHelper.reply_message(event, [TemplateMessage(alt_text='片語清單', template=image_carousel_template)])

# 生成問題卡片
def generate_question_line_flex(question: dict, question_no: int):
    TYPE_MAP = {
        'word': '單字',
        'phrase': '片語',
        'comprehension': '閱讀理解'
    }
    question.update({
        'no': question_no + 1,
        'type': TYPE_MAP.get(question.get('type'))
    })

    line_flex_str = firebaseService.get_data('line_flex', 'quiz').get('question')
    line_flex_str = LineBotHelper.replace_variable(line_flex_str, question)
    return line_flex_str

# 生成答案卡片
def generate_answer_line_flex(question: dict, is_correct: bool):
    line_flex_quiz = firebaseService.get_data('line_flex', 'quiz')
    line_flex_str = line_flex_quiz.get('correct') if is_correct else line_flex_quiz.get('wrong')
    line_flex_str = LineBotHelper.replace_variable(line_flex_str, question)
    # 詳解有些有\n
    line_flex_str = line_flex_str.replace('\n', '\\n')
    return line_flex_str

# 記錄該題作答(選擇的答案人數+1) + 紀錄該題答題人數
def create_answer_record(user_id: str, quiz_id: str, question: dict, answer: str):
    # 紀錄該題的答案人數
    culumn_map = {
        'a': 'A_vote_count',
        'b': 'B_vote_count',
        'c': 'C_vote_count',
        'd': 'D_vote_count'
    }
    column_name = culumn_map.get(answer)
    wks = spreadsheetService.sh.worksheet_by_title('quiz')
    col_index = spreadsheetService.get_column_index(wks, column_name)
    row_index = int(question.get('id')) + 1
    spreadsheetService.update_cell_value('quiz', (row_index, col_index), int(question.get(column_name)) + 1)

    # 紀錄該題作答
    question_id = question.get('id')
    wks = spreadsheetService.sh.worksheet_by_title('quiz_record')
    wks.append_table(values=[quiz_id, user_id, question_id, answer])



# 生成測驗結果
def generate_quiz_result(params: dict):
    line_flex_str = firebaseService.get_data('line_flex', 'quiz').get('result')
    line_flex_str = LineBotHelper.replace_variable(line_flex_str, params)
    return line_flex_str

# 生成文章段落語音檔
def generate_speech():
    articles = firebaseService.get_collection_data('articles')
    for article in articles:
        folder = article.get('_id')
        paragraphs = article.get('paragraphs')
        for i, paragraph in enumerate(paragraphs):
            filename = f"article_{folder}/p{i+1}"
            azureService.azure_text_to_speech(filename, paragraph.get('text'))