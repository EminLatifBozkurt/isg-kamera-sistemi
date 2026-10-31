@echo off
chcp 65001 >nul
title ISG Kamera Sistemi Baslatici

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_project.ps1"

if errorlevel 1 (
  echo.
  echo Proje baslatilamadi. Yukaridaki hata mesajini kontrol et.
  pause
)
