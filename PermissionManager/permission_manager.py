import os
import sys
import json
import zipfile
import tempfile
import subprocess
import platform
import stat
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path


def get_permissions(path):
    """Получить права доступа для файла или каталога."""
    perms = {}
    st = os.stat(path)
    perms['mode'] = stat.filemode(st.st_mode)
    perms['mode_octal'] = oct(st.st_mode)[-4:]
    perms['uid'] = st.st_uid
    perms['gid'] = st.st_gid
    perms['is_dir'] = os.path.isdir(path)

    # ACL (только Unix)
    if platform.system() != 'Windows':
        try:
            acl = subprocess.check_output(['getfacl', '-p', path], text=True)
            perms['acl'] = acl
        except:
            perms['acl'] = ''
    else:
        perms['acl'] = ''

    return perms


def set_permissions(path, perms):
    """Восстановить права доступа."""
    # Восстанавливаем владельца (только если есть права root, иначе просто пытаемся)
    try:
        os.chown(path, perms['uid'], perms['gid'])
    except:
        pass  # Нет прав на смену владельца

    # Восстанавливаем режим доступа
    mode = int(perms['mode_octal'], 8)
    os.chmod(path, mode)

    # Восстанавливаем ACL
    if perms.get('acl') and platform.system() != 'Windows':
        try:
            proc = subprocess.Popen(['setfacl', '--restore=-'], stdin=subprocess.PIPE, text=True)
            proc.communicate(perms['acl'])
        except:
            pass


def serialize(src_path, output_path):
    """Упаковывает файл или каталог в ZIP + JSON."""
    src_path = Path(src_path)

    # Собираем все файлы и права
    data = {}

    if src_path.is_file():
        files = [src_path]
        data[src_path.name] = {
            'type': 'file',
            'perms': get_permissions(src_path)
        }
    else:
        files = list(src_path.rglob('*'))
        for f in files:
            rel_path = str(f.relative_to(src_path))
            data[rel_path] = {
                'type': 'file' if f.is_file() else 'dir',
                'perms': get_permissions(f)
            }

    # Создаём временную директорию для копирования содержимого
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        content_dir = tmpdir_path / 'content'
        content_dir.mkdir()

        # Копируем структуру
        for rel_path, info in data.items():
            full_dest = content_dir / rel_path
            if info['type'] == 'dir':
                full_dest.mkdir(parents=True, exist_ok=True)
            else:
                full_dest.parent.mkdir(parents=True, exist_ok=True)
                src_full = src_path / rel_path if src_path.is_dir() else src_path
                with open(src_full, 'rb') as f_in:
                    with open(full_dest, 'wb') as f_out:
                        f_out.write(f_in.read())

        # Упаковываем в zip + добавляем JSON с правами
        with zipfile.ZipFile(output_path, 'w') as zf:
            # Добавляем JSON с метаданными
            zf.writestr('metadata.json', json.dumps(data, indent=2))
            # Добавляем всё содержимое
            for root, _, files_in in os.walk(content_dir):
                for file in files_in:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, content_dir)
                    zf.write(full_path, arcname)


def deserialize(input_path, output_path):
    """Восстанавливает файл/каталог из архива."""
    output_path = Path(output_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Распаковываем zip
        with zipfile.ZipFile(input_path, 'r') as zf:
            zf.extractall(tmpdir_path)

        # Читаем метаданные
        with open(tmpdir_path / 'metadata.json', 'r') as f:
            data = json.load(f)

        # Восстанавливаем структуру и права
        for rel_path, info in data.items():
            full_dest = output_path / rel_path if rel_path != output_path.name else output_path

            # Копируем содержимое из временной папки
            src_content = tmpdir_path / 'content' / rel_path

            if info['type'] == 'dir':
                full_dest.mkdir(parents=True, exist_ok=True)
            else:
                full_dest.parent.mkdir(parents=True, exist_ok=True)
                with open(src_content, 'rb') as f_in:
                    with open(full_dest, 'wb') as f_out:
                        f_out.write(f_in.read())

            # Восстанавливаем права
            set_permissions(full_dest, info['perms'])




class PermissionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Permission Manager")
        self.root.geometry("500x300")

        self.mode = tk.StringVar(value="serialize")

        tk.Label(root, text="Режим:").pack(pady=5)
        tk.Radiobutton(root, text="Сохранить (сериализация)", variable=self.mode, value="serialize").pack()
        tk.Radiobutton(root, text="Восстановить (десериализация)", variable=self.mode, value="deserialize").pack()

        tk.Button(root, text="Выбрать входной путь", command=self.select_input).pack(pady=5)
        self.input_label = tk.Label(root, text="Вход: не выбран", fg="gray")
        self.input_label.pack()

        tk.Button(root, text="Выбрать выходной файл/путь", command=self.select_output).pack(pady=5)
        self.output_label = tk.Label(root, text="Выход: не выбран", fg="gray")
        self.output_label.pack()

        tk.Button(root, text="Выполнить", command=self.run, bg="green", fg="white").pack(pady=20)

        self.input_path = None
        self.output_path = None

    def select_input(self):
        if self.mode.get() == "serialize":
            path = filedialog.askopenfilename(title="Выберите файл для сохранения")
            if not path:
                path = filedialog.askdirectory(title="Или выберите каталог")
        else:
            path = filedialog.askopenfilename(title="Выберите архив .zip для восстановления")

        if path:
            self.input_path = path
            self.input_label.config(text=f"Вход: {path}", fg="black")

    def select_output(self):
        if self.mode.get() == "serialize":
            path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")])
        else:
            path = filedialog.askdirectory(title="Выберите папку для восстановления")

        if path:
            self.output_path = path
            self.output_label.config(text=f"Выход: {path}", fg="black")

    def run(self):
        if not self.input_path or not self.output_path:
            messagebox.showerror("Ошибка", "Выберите входной и выходной путь")
            return

        try:
            if self.mode.get() == "serialize":
                serialize(self.input_path, self.output_path)
                messagebox.showinfo("Готово", f"Сохранено в {self.output_path}")
            else:
                deserialize(self.input_path, self.output_path)
                messagebox.showinfo("Готово", f"Восстановлено в {self.output_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))



def main():
    parser = argparse.ArgumentParser(description="Permission Manager")
    parser.add_argument("--serialize", action="store_true", help="Режим сохранения")
    parser.add_argument("--deserialize", action="store_true", help="Режим восстановления")
    parser.add_argument("--input", help="Входной файл/каталог")
    parser.add_argument("--output", help="Выходной архив/каталог")
    parser.add_argument("--gui", action="store_true", help="Запустить GUI")

    args = parser.parse_args()

    if args.gui or (len(sys.argv) == 1):
        root = tk.Tk()
        app = PermissionApp(root)
        root.mainloop()
    elif args.serialize and args.input and args.output:
        serialize(args.input, args.output)
        print(f" Сохранено в {args.output}")
    elif args.deserialize and args.input and args.output:
        deserialize(args.input, args.output)
        print(f"Восстановлено в {args.output}")
    else:
        print("Использование:")
        print("  python permission_manager.py --serialize --input test.txt --output backup.zip")
        print("  python permission_manager.py --deserialize --input backup.zip --output restored/")
        print("  python permission_manager.py --gui")


if __name__ == "__main__":
    main()