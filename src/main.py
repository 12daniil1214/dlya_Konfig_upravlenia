import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from functools import partial
from pathlib import Path
import shlex
import argparse
import csv
import json


VFS_NAME = "MyVFS"
WINDOW_SIZE = "1280x720"
FONT = ("Consolas", 11)
PROMPT = "$"
NOT_SET = "(не задан)"
LOG_HEADER = ["datetime", "command", "args", "status"]
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
COMMENT_PREFIX = "#"
SCRIPT_DELAY_MS = 100
STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_EXIT = "exit"
RM_RECURSIVE = "-r"
RM_FORBIDDEN = (".", "..", "/")


def build_window(root):
    """Создаёт поле вывода и строку ввода.

    Args:
        root (tk.Tk): Корневое окно.

    Returns:
        tuple[scrolledtext.ScrolledText, tk.Entry]: Вывод и ввод.
    """
    out = scrolledtext.ScrolledText(
        root, bg="black", fg="white", font=FONT, state=tk.DISABLED
    )
    out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    frame = tk.Frame(root)
    frame.pack(fill=tk.X, padx=5, pady=(0, 5))
    tk.Label(frame, text=PROMPT, font=FONT).pack(side=tk.LEFT)
    entry = tk.Entry(frame, font=FONT)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
    entry.focus_set()
    return out, entry


def parse_args(argv=None):
    """Разбирает параметры командной строки.

    Args:
        argv (list[str], optional): Аргументы. По умолчанию берутся
            аргументы процесса.

    Returns:
        dict[str, str | None]: Параметры эмулятора (ключ -> значение).
    """
    parser = argparse.ArgumentParser(description=f"{VFS_NAME}: эмулятор")
    parser.add_argument("--vfs-path", help="путь к физическому VFS")
    parser.add_argument("--log-file", help="путь к лог-файлу (CSV)")
    parser.add_argument("--script", help="путь к стартовому скрипту")
    args = parser.parse_args(argv)
    return {
        "vfs_path": args.vfs_path,
        "log_file": args.log_file,
        "script": args.script,
    }


def format_config(config):
    """Преобразует параметры в строки вида ключ=значение.

    Args:
        config (dict[str, str | None]): Параметры эмулятора.

    Returns:
        list[str]: Строки "ключ=значение".
    """
    return [
        f"{key}={NOT_SET if value is None else value}"
        for key, value in config.items()
    ]


def write_log(log_file, command, args, status, output):
    """Добавляет в CSV-лог событие вызова команды.

    Если файл новый, сначала пишется заголовок. Если лог-файл не задан,
    ничего не делает. При ошибке записи выводит предупреждение.

    Args:
        log_file (str | None): Путь к лог-файлу.
        command (str): Имя команды.
        args (list[str]): Аргументы команды.
        status (str): Результат ("ok" или "error").
        output (Callable[[str], None]): Функция вывода строки.
    """
    if not log_file:
        return
    path = Path(log_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not (path.exists() and path.stat().st_size)
        with path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if is_new:
                writer.writerow(LOG_HEADER)
            now = datetime.now().strftime(TIME_FORMAT)
            writer.writerow([now, command, shlex.join(args), status])
    except OSError as err:
        output(f"предупреждение: не удалось записать лог: {err}")


def print_line(out, text=""):
    """Добавляет строку в поле вывода и сразу обновляет окно.

    Args:
        out (scrolledtext.ScrolledText): Поле вывода.
        text (str, optional): Текст строки.
    """
    out.config(state=tk.NORMAL)
    out.insert(tk.END, text + "\n")
    out.see(tk.END)
    out.config(state=tk.DISABLED)
    out.update_idletasks()


def parse_line(line):
    """Делит строку на команду и аргументы.

    Args:
        line (str): Непустая строка.

    Returns:
        tuple[str, list[str]]: Команда и список аргументов.

    Raises:
        ValueError: Если строку не удалось разобрать.
    """
    try:
        parts = shlex.split(line)
    except ValueError as err:
        raise ValueError(f"ошибка разбора: {err}") from err
    return parts[0], parts[1:]


def cmd_ls(args, config, output):
    """Выводит содержимое каталога (каталоги помечаются '/')."""
    vfs = _need_vfs(config, output)
    if vfs is None:
        return STATUS_ERROR
    if args:
        target = args[0]
        try:
            node = vfs_node(vfs, target)
        except ValueError as err:
            output(f"ls: {err}")
            return STATUS_ERROR
    else:
        # текущий каталог
        node = vfs["root"]
        for p in vfs["cwd"]:
            node = node["children"][p]
    if node.get("type") != "dir":
        output(f"ls: не каталог")
        return STATUS_ERROR
    for name, child in sorted(node.get("children", {}).items()):
        output(name + ("/" if child.get("type") == "dir" else ""))
    return STATUS_OK


def cmd_cd(args, config, output):
    """Меняет текущий каталог. Поддерживает '.', '..' и абсолютные пути."""
    vfs = _need_vfs(config, output)
    if vfs is None:
        return STATUS_ERROR
    if len(args) != 1:
        output("cd: нужен один аргумент")
        return STATUS_ERROR
    target = args[0]
    try:
        node = vfs_node(vfs, target)
    except ValueError as err:
        output(f"cd: {err}")
        return STATUS_ERROR
    if node.get("type") != "dir":
        output(f"cd: {target}: не каталог")
        return STATUS_ERROR
    new_cwd = [] if target.startswith("/") else list(vfs["cwd"])
    for p in [x for x in target.split("/") if x]:
        if p == ".":
            continue
        if p == "..":
            if new_cwd:
                new_cwd.pop()
        else:
            new_cwd.append(p)
    vfs["cwd"] = new_cwd
    return STATUS_OK


def cmd_rm(args, config, output):
    """Удаляет файлы и, с ключом -r, каталоги из VFS в памяти.

    Args:
        args (list[str]): Пути и, возможно, ключ -r.
        config (dict): Параметры эмулятора.
        output (Callable[[str], None]): Функция вывода строки.

    Returns:
        str: STATUS_OK или STATUS_ERROR.
    """
    vfs = _need_vfs(config, output)
    if vfs is None:
        return STATUS_ERROR
    recursive = RM_RECURSIVE in args
    targets = [a for a in args if a != RM_RECURSIVE]
    if not targets:
        output("rm: нужен аргумент")
        return STATUS_ERROR
    status = STATUS_OK
    for target in targets:
        if not _rm_path(vfs, target, recursive, output):
            status = STATUS_ERROR
    return status


def _rm_path(vfs, target, recursive, output):
    """Удаляет один путь. Возвращает True при успехе.

    Args:
        vfs (dict): Виртуальная файловая система.
        target (str): Путь к удаляемому узлу.
        recursive (bool): Разрешить удаление каталога.
        output (Callable[[str], None]): Функция вывода строки.

    Returns:
        bool: True, если узел удалён, иначе False.
    """
    if target in RM_FORBIDDEN or target.endswith("/"):
        output(f"rm: {target}: нельзя удалить")
        return False
    parts = [p for p in target.split("/") if p]
    name = parts[-1]
    parent_path = "/".join(parts[:-1]) if len(parts) > 1 else "."
    if target.startswith("/"):
        parent_path = "/" + parent_path if parent_path != "." else "/"
    try:
        if parent_path in (".", "/"):
            parent = vfs["root"]
            for p in ([] if parent_path == "/" else vfs["cwd"]):
                parent = parent["children"][p]
        else:
            parent = vfs_node(vfs, parent_path)
    except ValueError as err:
        output(f"rm: {err}")
        return False
    if name not in parent.get("children", {}):
        output(f"rm: {target}: нет такого файла")
        return False
    node = parent["children"][name]
    if node.get("type") == "dir" and not recursive:
        output(f"rm: {target}: это каталог (используйте -r)")
        return False
    del parent["children"][name]
    return True


def cmd_who(args, config, output):
    """Показывает пользователей, работающих в системе."""
    output("user     salfetka")
    output("user     polzovatel123")
    return STATUS_OK


def cmd_whoami(args, config, output):
    """Печатает имя текущего пользователя."""
    output("user salfetka")
    return STATUS_OK


def cmd_conf_dump(args, config, output):
    """Выводит параметры эмулятора в формате ключ=значение."""
    for line in format_config(config):
        output(line)
    return STATUS_OK


def cmd_exit(args, config, output):
    """Сообщает, что нужно завершить работу эмулятора."""
    return STATUS_EXIT


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "rm": cmd_rm,
    "who": cmd_who,
    "whoami": cmd_whoami,
    "conf-dump": cmd_conf_dump,
    "exit": cmd_exit,
}


def execute(line, config, output):
    """Выполняет строку и записывает событие в лог.

    Args:
        line (str): Введенная строка.
        config (dict[str, str | None]): Параметры эмулятора.
        output (Callable[[str], None]): Функция вывода строки.

    Returns:
        str: STATUS_OK, STATUS_ERROR или STATUS_EXIT.
    """
    if not line.strip():
        return STATUS_OK
    words = line.split()
    command, args = words[0], words[1:]
    try:
        command, args = parse_line(line)
        handler = COMMANDS.get(command)
        if handler is None:
            raise ValueError(f"{command}: команда не найдена")
        status = handler(args, config, output)
    except ValueError as err:
        output(str(err))
        status = STATUS_ERROR
    logged = STATUS_ERROR if status == STATUS_ERROR else STATUS_OK
    write_log(config["log_file"], command, args, logged, output)
    return status


def handle_enter(root, entry, config, output):
    """Выполняет команду, введённую пользователем по нажатию Enter.

    Args:
        root (tk.Tk): Корневое окно (закрывается по команде exit).
        entry (tk.Entry): Строка ввода.
        config (dict[str, str | None]): Параметры эмулятора.
        output (Callable[[str], None]): Функция вывода строки.
    """
    line = entry.get()
    entry.delete(0, tk.END)
    output(f"{PROMPT} {line}")
    if execute(line, config, output) == STATUS_EXIT:
        root.destroy()


def read_script(path, output):
    """Читает строки скрипта.

    Args:
        path (str): Путь к скрипту.
        output (Callable[[str], None]): Функция вывода строки.

    Returns:
        list[str] | None: Строки файла или None при ошибке чтения.
    """
    try:
        return Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as err:
        output(f"ошибка: не удалось прочитать скрипт: {err}")
        return None


def run_script(path, config, output):
    """Выполняет скрипт, показывая ввод и вывод.

    Пустые строки и строки, начинающиеся с "#", пропускаются.
    Выполнение останавливается на первой ошибке.

    Args:
        path (str): Путь к скрипту.
        config (dict[str, str | None]): Параметры эмулятора.
        output (Callable[[str], None]): Функция вывода строки.

    Returns:
        str: STATUS_OK, STATUS_ERROR или STATUS_EXIT.
    """
    lines = read_script(path, output)
    if lines is None:
        return STATUS_ERROR
    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith(COMMENT_PREFIX):
            continue
        output(f"{PROMPT} {line}")
        status = execute(line, config, output)
        if status == STATUS_ERROR:
            output(f"скрипт остановлен: ошибка в строке {number}")
        if status != STATUS_OK:
            return status
    return STATUS_OK


def start_script(root, config, output):
    """Запускает стартовый скрипт, по exit закрывает окно.

    Args:
        root (tk.Tk): Корневое окно.
        config (dict[str, str | None]): Параметры эмулятора.
        output (Callable[[str], None]): Функция вывода строки.
    """
    if run_script(config["script"], config, output) == STATUS_EXIT:
        root.destroy()


def load_vfs(path, output):
    """Читает JSON-файл VFS в память.

    Загружает VFS из JSON-файла в оперативную память.
    Исходный файл только читается и не модифицируется.

    Args:
        path (str | None): Путь к JSON-файлу VFS. Если пусто/None —
            VFS не загружается, возвращается None.
        output (Callable[[str], None]): Функция вывода строки для
            сообщений об ошибках.

    Returns:
        dict | None: Словарь VFS при успехе, иначе None.
    """

    """Читает JSON-файл VFS в память. Возвращает словарь или None."""
    if not path:
        return None
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return {"name": doc.get("name", VFS_NAME),
                "root": doc["root"], "cwd": []}
    except (OSError, UnicodeDecodeError,
            json.JSONDecodeError, KeyError) as err:
        output(f"ошибка: не удалось загрузить VFS: {err}")
        return None

def vfs_node(vfs, arg):
    """Узел по пути относительно cwd. Кидает ValueError."""
    # Определяем стартовый узел и базовый cwd
    if arg.startswith("/"):
        node = vfs["root"]
        cwd = []
        parts = [x for x in arg.split("/") if x]
    else:
        node = vfs["root"]
        for p in vfs["cwd"]:
            node = node["children"][p]
        cwd = list(vfs["cwd"])
        parts = [x for x in arg.split("/") if x]

    for p in parts:
        if p == ".":
            continue
        if p == "..":
            if cwd:
                cwd.pop()
            # Пересчитываем node от корня по cwd
            node = vfs["root"]
            for q in cwd:
                node = node["children"][q]
            continue
        if node.get("type") != "dir" or p not in node.get("children", {}):
            raise ValueError(f"нет такого пути: {arg}")
        node = node["children"][p]
        cwd.append(p)
    return node


def _need_vfs(config, output):
    vfs = config.get("vfs")
    if vfs is None:
        output("ошибка: VFS не загружена (--vfs-path)")
    return vfs


def main():
    """Читает параметры, создаёт окно и запускает цикл событий."""
    config = parse_args()
    root = tk.Tk()
    root.title(VFS_NAME)
    root.geometry(WINDOW_SIZE)
    out, entry = build_window(root)
    output = partial(print_line, out)
    config["vfs"] = load_vfs(config["vfs_path"], output)
    output(f"{VFS_NAME}: эмулятор оболочки. Введите команду.")
    output("[debug] Параметры запуска:")
    for line in format_config(config):
        output(f"[debug]   {line}")
    output()
    entry.bind(
        "<Return>",
        lambda event: handle_enter(root, entry, config, output),
    )
    if config["script"]:
        root.after(SCRIPT_DELAY_MS, start_script, root, config, output)
    root.mainloop()


if __name__ == "__main__":
    main()