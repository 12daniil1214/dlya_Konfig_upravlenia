echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path vfs_minimal.json --log-file logs/minimal.csv --script .\scripts\startup.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path vfs_multi.json --log-file logs/multi.csv --script .\scripts\startup.txt

echo off
python C:\Users\79295\PycharmProjects\dlya_Konfig_upravlenia\src\main.py --vfs-path vfs_deep.json --log-file logs/deep.csv --script .\scripts\startup.txt