@echo off
cd C:\Users\nick\source\repos\BitCrack
del checkpoint.txt 2>nul
del results.txt 2>nul

echo Starting key monitor in background...
start "Key Monitor" python scripts\puzzle_monitor.py --watch results.txt --email ngflower@gmail.com

echo Starting BitCrack Puzzle #71...
echo Target: 1NKkKMbLAeMTRCz2o6wRwNJBPFoMqyCalp (7.1 BTC)
echo.
x64\Release\clBitCrack.exe -o results.txt --continue checkpoint.txt -b 32 -t 256 -p 256 --keyspace 598DB7F1825EF67AB3:598E7A590F31127AB3 1NKkKMbLAeMTRCz2o6wRwNJBPFoMqyCalp
pause
