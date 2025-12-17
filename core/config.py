import os
import configparser

CONFIG_FILE = "config.ini"

# Default values if config.ini doesn't exist
DEFAULT_CONFIG = {
    'SETTINGS': {
        'MODEL_NAME': 'gemini-2.5-flash', # Would love to use 2.0 but free RPD is so low.
        'USER_NAME': 'User',
        'CHATBOT_NAME': 'Gemini',
        'INSTRUCTION': 'You are a helpful AI assistant.',
        'FONT_SIZE': '11',
        'TEMPERATURE': '0.7',
        'THEME': 'arc',  # Default visual theme
        'LANGUAGE': 'en',
    },
    'SAFETY': {
        'HARASSMENT': 'BLOCK_MEDIUM_AND_ABOVE',
        'HATE_SPEECH': 'BLOCK_MEDIUM_AND_ABOVE',
        'DANGEROUS': 'BLOCK_MEDIUM_AND_ABOVE',
        'SEXUAL': 'BLOCK_MEDIUM_AND_ABOVE',
    }
}

class ConfigManager:
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        """Loads the config file or creates it if missing."""
        if not os.path.exists(CONFIG_FILE):
            self.parser.read_dict(DEFAULT_CONFIG)
            with open(CONFIG_FILE, 'w') as f:
                self.parser.write(f)
        else:
            self.parser.read(CONFIG_FILE)

    def get_settings(self):
        """Returns the dictionary from config file."""
        return {
            'model_name': self.parser.get('SETTINGS', 'MODEL_NAME', fallback='gemini-2.5-flash'),
            'user_name': self.parser.get('SETTINGS', 'USER_NAME', fallback='User'),
            'chatbot_name': self.parser.get('SETTINGS', 'CHATBOT_NAME', fallback='Gemini'),
            'instruction': self.parser.get('SETTINGS', 'INSTRUCTION', fallback=''),
            'font_size': self.parser.getint('SETTINGS', 'FONT_SIZE', fallback=11),
            'temperature': self.parser.getfloat('SETTINGS', 'TEMPERATURE', fallback=0.7),
            'theme': self.parser.get('SETTINGS', 'THEME', fallback='arc'),
            'language': self.parser.get('SETTINGS', 'LANGUAGE', fallback='en'),
        }

    def get_safety_settings(self):
        s = self.parser['SAFETY']
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=THRESHOLD_MAP.get(s.get('HARASSMENT'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=THRESHOLD_MAP.get(s.get('HATE_SPEECH'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=THRESHOLD_MAP.get(s.get('DANGEROUS'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=THRESHOLD_MAP.get(s.get('SEXUAL'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=THRESHOLD_MAP.get(s.get('CIVIC'), types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
            ),
        ]

    def get_parser(self):
        """Returns the raw parser object (needed for the Preferences Window)."""
        return self.parser
