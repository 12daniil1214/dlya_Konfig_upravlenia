import tkinter as tk
from tkinter import scrolledtext
import shlex

VFS_NAME = "MyVFS"


def run_command(cmd, args, output, root):
    """Выполняет разбор и обработку введённой команды.

    В зависимости от имени команды: выводит информацию об аргументах для ls/cd,
    завершает работу приложения для exit, либо сообщает о том, что команда не найдена.

    Args:
        cmd (str): Имя команды.
        args (list[str]): Список аргументов команды.
        output (Callable[[str], None]): Функция для вывода текста в текстовое поле консоли.
        root (tk.Tk): Корневое окно приложения, используется для корректного завершения работы по команде exit.

    Returns:
        None
    """
    if cmd == "ls":
        output(f"ls: аргументы = {args}")
    elif cmd == "cd":
        output(f"cd: аргументы = {args}")
    elif cmd == "exit":
        root.destroy()
    else:
        output(f"{cmd}: команда не найдена")

def print_line(text=""):
    """Добавляет строку текста в поле вывода консоли.

    Временно переводит текстовое поле в редактируемое состояние, вставляет строку с переводом на новую строку,
    прокручивает вывод к последней строке и возвращает поле в состояние "только для чтения".

    Args:
        text (str, optional): Текст для вывода. По умолчанию пустая строка.

    Returns:
        None
    """
    out.config(state=tk.NORMAL)
    out.insert(tk.END, text + "\n")
    out.see(tk.END)
    out.config(state=tk.DISABLED)


def on_enter(event):
    """Обрабатывает нажатие клавиши Enter в поле ввода команды.

    Считывает введённую пользователем строку, очищает поле ввода, выводит команду в консоль с префиксом "$",
    разбирает строку с учётом кавычек (shlex) и передаёт результат на выполнение в run_command.
    При ошибке разбора выводит сообщение об ошибке и прерывает обработку.

    Args:
        event (tk.Event): Событие нажатия клавиши.

    Returns:
        None
    """
    line = entry.get()
    entry.delete(0, tk.END)
    print_line(f"$ {line}")

    if not line.strip():
        return

    # парсим с учётом кавычек
    try:
        parts = shlex.split(line)
    except ValueError as e:
        print_line(f"ошибка разбора: {e}")
        return

    if not parts:
        return

    cmd, args = parts[0], parts[1:]
    run_command(cmd, args, print_line, root)


root = tk.Tk()
root.title(VFS_NAME)
root.geometry("1280x720")

# поле вывода
out = scrolledtext.ScrolledText(
    root, bg="black", fg="white",
    font=("Consolas", 11), state=tk.DISABLED
)
out.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# поле ввода
frame = tk.Frame(root)
frame.pack(fill=tk.X, padx=5, pady=(0, 5))
tk.Label(frame, text="$", font=("Consolas", 12, "bold")).pack(side=tk.LEFT)
entry = tk.Entry(frame, font=("Consolas", 11))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
entry.focus_set()

entry.bind("<Return>", on_enter)

print_line(f"{VFS_NAME}: эмулятор оболочки. Введите команду.")
print_line()

root.mainloop()