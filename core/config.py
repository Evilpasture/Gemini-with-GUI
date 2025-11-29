import os
import configparser
from google.genai import types

CONFIG_FILE = "config.ini"

COMMENT_HEADER = """
# ---NOTE FOR SAFETY SETTINGS---
# VALUES: BLOCK_NONE, BLOCK_ONLY_HIGH, BLOCK_MEDIUM_AND_ABOVE, BLOCK_LOW_AND_ABOVE
"""

THRESHOLD_MAP = {
    "BLOCK_NONE": types.HarmBlockThreshold.BLOCK_NONE,
    "BLOCK_ONLY_HIGH": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "BLOCK_MEDIUM_AND_ABOVE": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_LOW_AND_ABOVE": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}

DEFAULT_CONFIG = {
    'SETTINGS': {
        'MODEL_NAME': 'gemini-2.5-flash',
        'USER_NAME': 'User',
        'CHATBOT_NAME': 'Gemini',
        'INSTRUCTION': 'You are a helpful AI assistant.',
        'STANDARD_FONT_NAME': 'Arial',
        'STANDARD_FONT_SIZE': '12',
        'TEMPERATURE': '0.7'
    },
    'SAFETY_SETTINGS': {
        'HARASSMENT_THRESHOLD': 'BLOCK_MEDIUM_AND_ABOVE',
        'HATE_SPEECH_THRESHOLD': 'BLOCK_MEDIUM_AND_ABOVE',
        'DANGEROUS_CONTENT_THRESHOLD': 'BLOCK_MEDIUM_AND_ABOVE',
        'SEXUALLY_EXPLICIT_THRESHOLD': 'BLOCK_MEDIUM_AND_ABOVE',
        'CIVIC_INTEGRITY_THRESHOLD': 'BLOCK_MEDIUM_AND_ABOVE',
    }
}

class ConfigManager:
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            # Create default
            for section, options in DEFAULT_CONFIG.items():
                self.parser[section] = options
            with open(CONFIG_FILE, 'w') as f:
                f.write(COMMENT_HEADER + '\n')
                self.parser.write(f)
        else:
            self.parser.read(CONFIG_FILE)

    def get_settings(self):
        return {
            'model_name': self.parser.get('SETTINGS', 'MODEL_NAME', fallback='gemini-2.5-flash'),
            'user_name': self.parser.get('SETTINGS', 'USER_NAME', fallback='User'),
            'chatbot_name': self.parser.get('SETTINGS', 'CHATBOT_NAME', fallback='Gemini'),
            'instruction': self.parser.get('SETTINGS', 'INSTRUCTION', fallback=''),
            'font_name': self.parser.get('SETTINGS', 'STANDARD_FONT_NAME', fallback='Arial'),
            'font_size': self.parser.getint('SETTINGS', 'STANDARD_FONT_SIZE', fallback=10),
            'temperature': self.parser.getfloat('SETTINGS', 'TEMPERATURE', fallback=0.7),
        }

    def get_safety_settings(self):
        """Converts string config to Google GenAI types"""
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'HARASSMENT_THRESHOLD'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            # Add other categories here...
             types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'HATE_SPEECH_THRESHOLD'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'DANGEROUS_CONTENT_THRESHOLD'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
        ]

    def get_parser(self):
        """Returns the raw parser object (needed for the Preferences Window)"""
        return self.parser
