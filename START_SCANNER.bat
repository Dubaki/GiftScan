@echo off
title GiftScan Arbitrage Scanner
cd /d "%~dp0backend"
echo.
echo ========================================
echo  GiftScan Arbitrage Scanner
echo ========================================
echo.
echo Starting scanner...
echo.
python start_scanner.py
pause
