import os
import configparser
from google.genai import types

CONFIG_FILE = "config.ini"

# List of supported clean light themes for the Settings Dropdown
LIGHT_THEMES = ["arc", "yaru", "breeze", "radiance", "plastik"]

# Mapping string values from config.ini to Google GenAI types
THRESHOLD_MAP = {
    "BLOCK_NONE": types.HarmBlockThreshold.BLOCK_NONE,
    "BLOCK_ONLY_HIGH": types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    "BLOCK_MEDIUM_AND_ABOVE": types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    "BLOCK_LOW_AND_ABOVE": types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}

# Default values if config.ini doesn't exist
DEFAULT_CONFIG = {
    'SETTINGS': {
        'MODEL_NAME': 'gemini-2.5-flash', #gemini-2.0-flash could be an option but 2.5 has 250 RPD compared to 200 RPD of 2.0
        'USER_NAME': 'User',
        'CHATBOT_NAME': 'Gemini',
        'INSTRUCTION': 'You are a helpful AI assistant.',
        'STANDARD_FONT_NAME': 'Arial',
        'STANDARD_FONT_SIZE': '11',
        'TEMPERATURE': '0.7',
        'THEME': 'arc'  # Default visual theme
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
        """Loads the config file or creates it if missing."""
        if not os.path.exists(CONFIG_FILE):
            # Create default config file
            for section, options in DEFAULT_CONFIG.items():
                self.parser[section] = options
            with open(CONFIG_FILE, 'w') as f:
                self.parser.write(f)
        else:
            self.parser.read(CONFIG_FILE)

    def get_settings(self):
        """Returns a dictionary of current application settings."""
        return {
            'model_name': self.parser.get('SETTINGS', 'MODEL_NAME', fallback='gemini-2.0-flash'),
            'user_name': self.parser.get('SETTINGS', 'USER_NAME', fallback='User'),
            'chatbot_name': self.parser.get('SETTINGS', 'CHATBOT_NAME', fallback='Gemini'),
            'instruction': self.parser.get('SETTINGS', 'INSTRUCTION', fallback=''),
            'font_name': self.parser.get('SETTINGS', 'STANDARD_FONT_NAME', fallback='Arial'),
            'font_size': self.parser.getint('SETTINGS', 'STANDARD_FONT_SIZE', fallback=11),
            'temperature': self.parser.getfloat('SETTINGS', 'TEMPERATURE', fallback=0.7),
            'theme': self.parser.get('SETTINGS', 'THEME', fallback='arc')
        }

    def set_setting(self, section, key, value):
        """Helper to save a single setting immediately."""
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, key, str(value))
        with open(CONFIG_FILE, 'w') as f:
            self.parser.write(f)

    def get_safety_settings(self):
        """Converts string config to Google GenAI safety objects."""
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'HARASSMENT_THRESHOLD'),
                                            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'HATE_SPEECH_THRESHOLD'),
                                            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'DANGEROUS_CONTENT_THRESHOLD'),
                                            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'SEXUALLY_EXPLICIT_THRESHOLD'),
                                            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=THRESHOLD_MAP.get(self.parser.get('SAFETY_SETTINGS', 'CIVIC_INTEGRITY_THRESHOLD'),
                                            types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            ),
        ]

    def get_parser(self):
        """Returns the raw parser object (needed for the Preferences Window)."""
        return self.parser
