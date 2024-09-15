import os
import time
import tkinter as tk
from pathlib import Path
from src import gui, core, manager, globals as gb

def create_paths(root):
    paths = [
        os.path.join(root, 'data'),
        os.path.join(root, 'data_exports')
    ]
    for path in paths:
        Path(path).mkdir(parents = True, exist_ok = True)
    return 1

def check_paths_and_files(root):

    def messagebox(title, message):
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror(title, message)
        root.destroy()

    paths = [
            'config',
            os.path.join('config', 'monster_names.json'),
            'data',
            'data_exports',
            'icons',
            os.path.join('icons', 'monstersprites'),
            os.path.join('icons', 'monstersprites', '0.png'),
            os.path.join('icons', 'logo.ico')
            ]
    for path in paths:
        if not os.path.exists(os.path.join(root, path)):
            messagebox(title = 'Error', message = f'File or Path not found: {path}')
            return 0
    return 1

if __name__ == '__main__':

    root_path = str(Path(__file__).parent)
    _ = create_paths(root_path)
    result = check_paths_and_files(root_path)
    if result != 1:
        exit()

    db_file = 'yapec.sqlite3'
    gb.globals.update_session_id(str(int(time.time())))
    core.DBHandler.setup_db(os.path.join(root_path, 'data', db_file))

    app = gui.MainWindow(root_path, db_file)
    pokemmo = core.PokeMMOHandler.from_title()
    tm = manager.TaskManager(pokemmo, app)
    tm.start()

    app.mainloop()

    tm.stop()
