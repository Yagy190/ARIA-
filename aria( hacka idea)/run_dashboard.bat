@echo off
title ARIA - Interactive Visual Hub & Map
cd /d "%~dp0"
echo ===============================================================
echo Launching ARIA Web Visualizer & Map
echo ===============================================================
python -m streamlit run web_dashboard.py
pause
