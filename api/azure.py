import os
#Azure Translation
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

# Azure Speech
import azure.cognitiveservices.speech as speechsdk

class AzureService:
    def __init__(self):
        # Azure Translation Settings
        self.azureKeyCredential = AzureKeyCredential(os.getenv("AZURE_TRANSLATE_API_KEY"))
        self.textTranslationClient = TextTranslationClient(
            credential=self.azureKeyCredential,
            endpoint=os.getenv("AZURE_TRANSLATE_API_ENDPOINT"),
            region=os.getenv("AZURE_TRANSLATE_API_REGION")
        )
        # Azure Speech Settings
        self.speechConfig = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_API_KEY"), 
            region=os.getenv("AZURE_SPEECH_API_REGION")
        )
        self.audioOutputConfig = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    # 處理Azure翻譯
    def azure_translate(self, words, to_language):
        if to_language == None:
            return "Please select a language"
        else:
            try:
                response = self.textTranslationClient.translate(body=[words], to_language=[to_language])
                print(response)
                translation = response[0] if response else None
                if translation:
                    detected_language = translation.detected_language
                    result = ''
                    if detected_language.language == 'en':
                        print(f"偵測到輸入的語言: {detected_language.language} 信心分數: {detected_language.score}")
                        for translated_text in translation.translations:
                            result += f"單字: {words}\n翻譯: {translated_text.text}"
                    else:
                        result = "無法翻譯，請輸入英文單字"
                    return result

            except HttpResponseError as exception:
                if exception.error is not None:
                    print(f"Error Code: {exception.error.code}")
                    print(f"Message: {exception.error.message}")

    
    def azure_text_to_speech(self, filename, translated_text):
        # The language of the voice that speaks.
        self.speechConfig.speech_synthesis_voice_name='en-US-AndrewMultilingualNeural'

        file_config = speechsdk.audio.AudioOutputConfig(filename=f'static/{filename}.wav')
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speechConfig, audio_config=file_config)

        # Receives a text from console input and synthesizes it to wave file.
        result = speech_synthesizer.speak_text_async(translated_text).get()

        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Speech synthesized for text [{}], and the audio was saved to [{}]".format(translated_text, filename))
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))