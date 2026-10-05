echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\tests\vfs_minimal.json --log-file logs/minimal.csv --script .\scripts\startup_minimal.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\tests\vfs_multi.json --log-file logs/multi.csv --script .\scripts\fail.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\tests\vfs_deep.json --log-file logs/deep.csv --script .\scripts\ok.txt