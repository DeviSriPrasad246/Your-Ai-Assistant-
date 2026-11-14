@echo off
py -3.13 -m venv venv
call venv\Scripts\activate
pip install streamlit ollama better-profanity
echo.
echo Setup finished! You can close this window.
pause