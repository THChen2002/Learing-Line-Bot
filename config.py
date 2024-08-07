import sys
import os
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.messaging import (
    Configuration
)
import pygsheets
import json
from api.spreadsheet import SpreadsheetService
from api.firebase import FireBaseService
from api.azure import AzureService

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    
class Config(metaclass=Singleton):
    def __init__(self):
        self.CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
        self.CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
        self.SPREADSHEET_URL = os.getenv('SPREADSHEET_URL')
        self.FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS')
        self.check_env()
        self.line_bot_init()

    def check_env(self):
        if self.CHANNEL_SECRET is None or self.CHANNEL_ACCESS_TOKEN is None:
            print("Please set LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN environment variables.")
            sys.exit(1)
        
        if self.SPREADSHEET_URL is None:
            print("Please set SPREADSHEET_URL environment variable.")
            sys.exit(1)

        if self.FIREBASE_CREDENTIALS is None:
            print("Please set FIREBASE_CREDENTIALS environment variable.")
            sys.exit(1)
        
    def line_bot_init(self):
        self.handler = WebhookHandler(self.CHANNEL_SECRET)
        self.configuration = Configuration(access_token=self.CHANNEL_ACCESS_TOKEN)
        self.spreadsheetService = SpreadsheetService(pygsheets.authorize(service_account_env_var='GDRIVE_API_CREDENTIALS'), self.SPREADSHEET_URL)
        self.firebaseService = FireBaseService(json.loads(self.FIREBASE_CREDENTIALS))
        self.azureService = AzureService()