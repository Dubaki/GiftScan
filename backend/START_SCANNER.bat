@echo off
echo ============================================
echo   GiftScan Arbitrage Scanner
echo ============================================
echo.
echo Starting continuous price monitoring...
echo Scan interval: 60 seconds
echo Telegram notifications: ENABLED
echo.
echo Press Ctrl+C to stop
echo.

python start_scanner.py

pause
