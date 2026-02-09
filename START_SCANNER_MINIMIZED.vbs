Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\GiftScan\backend && python start_scanner.py", 7, false
