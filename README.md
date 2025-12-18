# Gemini Python Client

A lightweight, desktop-based chat interface for Google's Gemini models built with Python and Tkinter with several features.

## Features

- Real-time chat interface

- Uses ttkthemes to allow you to use 5 select light visual themes for the interface (arc, yaru, breeze, radiance, plastik)

- Real time status display

- Chat history reset functionality

- Markdown support

- UI locking to prevent multiple requests

- Environment-based configuration

- Robust error-handling by displaying errors of critical issues

- Configuration is read with a config.ini

- Save/load chats with a JSON

- System instructions and persona

- Internationalization and Vietnamese support

- Uses OpenAI SDK to make request to Google instead

## Setup

### Get your API key

https://aistudio.google.com/api-keys

If there aren't any keys, create one for free.

### Create, then activate the Python virtual environment(based on your OS)

1. Create

- Linux/macOS: python3 -m venv venv

- Windows: python -m venv venv

2. Activation

- Linux/macOS: source venv/bin/activate

- Windows (Command Prompt): venv\Scripts\activate.bat

- Windows (PowerShell): .\venv\Scripts\Activate.ps1

### Install dependencies

1. pip install -r requirements.txt (or use an IDE to install them for you if possible)

2. Add your API Key to .env manually. (recommended, but you can add it in the dialog)

- Linux/macOS: touch /path/to/your/directory/.env

- Windows: type nul > C:\path\to\your\directory\.env

### Run the application:

- python main.py OR py main.py (in the current PATH to the directory)
