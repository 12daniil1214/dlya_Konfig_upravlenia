echo off
python C:\Users\79295\PycharmProjects\pythonProject1\emulator.py --log-file logs\fail.csv --script tests\scripts\fail.txt

echo off
python C:\Users\79295\PycharmProjects\pythonProject1\emulator.py --script tests\scripts\no_such_script.txt

echo off
python C:\Users\79295\PycharmProjects\pythonProject1\emulator.py --log-file logs\new_dir\log.csv --script tests\scripts\ok.txt