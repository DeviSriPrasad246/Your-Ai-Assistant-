# Matrix Root AI Assistant

A safe, honest AI chatbot that runs fully on your own computer. No API keys and no internet needed after setup.

## Features
- ChatGPT-style chat with streaming answers and memory
- Honesty rules: admits when it does not know, avoids inventing facts
- Safety filter on both user messages and AI answers
- Care-first reply for self-harm messages, with a helpline
- Saved chat history, New chat, and delete options
- Project Builder mode to help beginners build software
- Matrix Root branding with a dark theme

## Requirements
- Windows with Python 3.13
- Ollama (https://ollama.com)
- At least 4 GB RAM (8 GB or more recommended)

## How to run
1. Install Python 3.13 (tick "Add Python to PATH") and install Ollama.
2. Download the model: open Command Prompt and run `ollama pull llama3.2:1b`
3. Double-click `setup.bat` once and wait for "Setup finished!".
4. Double-click `start.bat`. The chatbot opens in your browser.

## Project files
- `app.py` - chat page and main logic
- `prompts.py` - the assistant's rules and modes
- `safety.py` - safety filter
- `logo.png` - company logo
- `.streamlit/config.toml` - dark theme

## Limitations
- Built on a small open-source model (Llama 3.2 1B). It can still make mistakes, so important information should be verified.
- The safety filter is rule-based (version 2) and cannot catch everything.
- It has no live internet access, so it cannot answer about today's news or weather.
