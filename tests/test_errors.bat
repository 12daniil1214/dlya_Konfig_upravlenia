echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --log-file logs\fail.csv --script .\scripts\fail.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --script .\scripts\no_such_script.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --log-file logs\new_dir\log.csv --script .\scripts\ok.txt