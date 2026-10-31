@echo off
chcp 65001 >nul
title ISG Kamera Sistemi Durdurucu

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_project.ps1"

if errorlevel 1 (
  echo.
  echo Proje tamamen durdurulamadi. Yukaridaki hata mesajini kontrol et.
  pause
)
