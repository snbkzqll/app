@echo off
cd /d %~dp0
echo 正在启动元器件管理系统...
streamlit run inventory_app.py
pause