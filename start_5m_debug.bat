@echo off
cd /d C:\Users\yashw\MetaStackerBandit
call .venv\Scripts\activate.bat
set PYTHONPATH=C:\Users\yashw\MetaStackerBandit
python live_demo\main.py > bot_5m_output.log 2>&1
echo.
echo Bot stopped. Check bot_5m_output.log for details.
pause
