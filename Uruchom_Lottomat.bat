@echo off
title Lottomat - Uruchamianie...
echo Uruchamianie aplikacji Lottomat...
.venv\Scripts\python.exe lottomat_flet.py
if errorlevel 1 (
    echo.
    echo Wystapil blad podczas uruchamiania aplikacji.
    echo Upewnij sie, ze Python jest zainstalowany i dodany do PATH.
    echo.
    pause
)
