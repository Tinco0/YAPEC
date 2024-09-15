import os
import json
import time
import win32gui

import tkinter as tk
from pathlib import Path
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

import src.globals as gb
import src.core as core

DEFAULT_FONT = ('Arial', 14)

# ask multiple choice question, similar to simpledialogs.
def _askmultiplechoice(options_values, options_labels = None, label = None, message = None, multiple = False, parent = None):
    
    # class to handle button press events
    class BttnPress:
        def __init__(self):
            self.ok = False
        def on_ok(self):
            root.destroy()
            self.ok = True
        def on_cancel(self):
            root.destroy()
            self.ok = False
    bttn = BttnPress()

    # options can have labels different than values
    if not options_labels:
        options_labels = options_values

    if len(options_labels) != len(options_values):
        raise ValueError('Labels and Values do not have the same size.')
    
    root = tk.Toplevel(parent)
    root.title(label)

    # if any text should be displayed before options
    if message:
        tk.Label(root, text = message).pack()

    box = tk.Frame(root)
    # multiple choice can have one or multiple answers
    # if one use radionbuttons if multiple use checkboxes
    if multiple:
        vars = []
        for i, option in enumerate(zip(options_labels, options_values)):
            var = tk.BooleanVar()
            vars.append(var)
            tk.Checkbutton(box, text = option[0], variable = var, onvalue = True, offvalue = False).pack(anchor = tk.W)
    else:
        var = tk.IntVar()
        for i, option in enumerate(zip(options_labels, options_values)):
            if i == 0:
                var.set(option[1])
            tk.Radiobutton(box, text = option[0], variable = var, value = option[1]).pack(anchor = tk.W)
    box.pack()

    # add confirm and cancel buttons
    box = tk.Frame(root)
    tk.Button(box, text = 'OK', width = 10, command = bttn.on_ok, default = tk.ACTIVE).pack(side = tk.LEFT, padx = 5, pady = 5)
    tk.Button(box, text = 'Cancel', width = 10, command = bttn.on_cancel).pack(side = tk.LEFT, padx = 5, pady = 5)
    root.bind('<Return>', bttn.on_ok)
    root.bind('<Escape>', bttn.on_cancel)
    box.pack()

    # make it behave like other messsageboxes
    # should be centered on parent
    if parent:
        root.transient(parent)
        root.geometry(f'+{parent.winfo_x()+50}+{parent.winfo_y()+50}')
    root.wait_visibility()
    root.grab_set()
    root.wait_window(root)

    if bttn.ok:    
        if multiple:
            vars_get = [var.get() for var in vars]
            return [value for value, var in zip(options_values, vars_get) if var]
        else:
            return var.get()
    else:
        return None
    

# widget that contains info of one entry on a column
# should contain pokemon sprite, encountered count and, if on, alpha and shiny count
class CountEntry(tk.Frame):
    def __init__(self, parent, id, qty, show_alpha_shiny = True):
        super().__init__(parent, pady = 0, borderwidth = 0)
        self.root_path = self.winfo_toplevel().root_path
        self.icon_path = os.path.join(self.root_path, 'icons', 'monstersprites', str(id) + '.png')
        if not os.path.isfile(self.icon_path):
            self.icon_path = os.path.join(self.root_path, 'icons', 'monstersprites', '0.png')
        self.img = tk.PhotoImage(file = self.icon_path).zoom(5, 5).subsample(4, 4)

        if show_alpha_shiny:
            tk.Label(self, image = self.img, borderwidth = 0)\
                .grid(row = 0, column = 0, rowspan = 2, padx = 0)

            tk.Label(self, text = str(qty['normal']), font = DEFAULT_FONT, borderwidth = 0)\
                .grid(row = 0, column = 1, pady = 0)

            tk.Label(self, text = f'A: {qty["alpha"]} | S: {qty["shiny"]}', borderwidth = 0)\
                .grid(row = 1, column = 1, pady = 0)
        else:
            tk.Label(self, image = self.img, text = str(qty['normal']), font = DEFAULT_FONT, borderwidth = 0, compound = tk.LEFT).pack()


# widget that contains all CountEntries in a column format
# it should also have a title on top 
class CountCol(tk.Frame):
    def __init__(self, parent, title, values, show_alpha_shiny = True):
        super().__init__(parent, padx = 14, borderwidth = 0, pady = 0)
        self.title = title
        self.values = values   
        tk.Label(self, text = title, font = DEFAULT_FONT, pady = 0, borderwidth = 0).grid(column = 0, row = 0)
        for i, (id, qty) in enumerate(list(values.items())):
            CountEntry(self, id, qty, show_alpha_shiny = show_alpha_shiny).grid(column = 0, row = i+1, sticky = tk.W)
        

# Menu with parent
class CustomMenu(tk.Menu):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent

    def winfo_toplevel(self):
        # Override winfo_toplevel to return the actual main window
        if isinstance(self.master, tk.Tk):
            return self.master
        else:
            return self.master.winfo_toplevel()


# widget that contains the size menu options, size controls how many entries per column
class SizeMenu(CustomMenu):

    SIZE_DICT = {'Mini': 0, 'Small': 1, 'Medium': 3, 'Large': 5}

    def __init__(self, parent, size):
        super().__init__(parent, tearoff = False)
        self.size_var = tk.IntVar()
        self.size_var.set(size)
        for k, v in self.SIZE_DICT.items():
            self.add_radiobutton(label = k, variable = self.size_var, value = v, command = self.on_size_change)

    def on_size_change(self):
        self.winfo_toplevel().event_generate('<<SizeChange>>')


# widget that contains buttons controlling if a column should be displayed
class ColMenu(CustomMenu):
    def __init__(self, parent, start_view = (True, True)):
        super().__init__(parent, tearoff = False)
        # only two columns for now, this could be more generic to handle variable number of column, but maybe not now
        self.col_var = [tk.BooleanVar(), tk.BooleanVar()]
        self.add_checkbutton(label = "Last", variable = self.col_var[0], onvalue = True, offvalue = False, command = self.on_col_change)
        self.add_checkbutton(label = "Top", variable = self.col_var[1], onvalue = True, offvalue = False, command = self.on_col_change)
        self.col_var[0].set(start_view[0])
        self.col_var[1].set(start_view[1])

    def on_col_change(self):
        self.winfo_toplevel().event_generate('<<ColChange>>')      
            

# base class for the profile and hunt menus
# it displays the availabe options and 3 operations buttons: create, rename and delete
# all operations delegate the actual db command to methods that should be specific of child classes
class ProfHuntMenu(CustomMenu):
    def __init__(self, parent):
        super().__init__(parent, tearoff = False)
        self.root = self.winfo_toplevel().root
        self.db_file = self.winfo_toplevel().db_file_path
        self.values = {}
        self.type = None

    def create_entry(self):
        name = simpledialog.askstring(f'Create {self.type}', f'Enter {self.type.lower()} name:', parent = self.root)
        if name in  self.values.values():
            messagebox.showinfo(title = 'Error', message = f'{self.type} already exists.')
            return 0
        elif name:
            with core.DBHandler(self.db_file) as db:
                result = self._create(db, name)
            if result:
                self.update_values()
                return 1
        return 0
    
    def _create(self, db, name):
        raise NotImplementedError('_create should be implemented on child classes.')
    
    def delete_entry(self):
        if len(self.values) == 1:
            messagebox.showinfo(title = 'Error', message = f'Cannot delete last {self.type.lower()}.')
            return 0
        entry_to_delete = _askmultiplechoice(list(self.values.keys()),
                                            list(self.values.values()),
                                            label = f'Delete {self.type}',
                                            message = f'Select {self.type.lower()} to delete:',
                                            multiple = False,
                                            parent = self.root)
        if entry_to_delete:
            confirm = messagebox.askokcancel(title = f'Delete {self.type}',
                                            message = f'Are you sure you want to delete {self.type.lower()} "{self.values[entry_to_delete]}"?\nThis action can never be undone!')
            if confirm:
                with core.DBHandler(self.db_file) as db:
                    result = self._delete(db, entry_to_delete)
                if result:
                    self.update_values()
                    return 1
        return 0
    
    def _delete(self, db, id):
        raise NotImplementedError('_delete should be implemented on child classes.')
    
    def rename_entry(self):
        entry_to_rename = _askmultiplechoice(list(self.values.keys()),
                                            list(self.values.values()),
                                            label = f'Rename {self.type}',
                                            message = f'Select {self.type.lower()} to rename:',
                                            multiple = False,
                                            parent = self.winfo_toplevel().root)
        if entry_to_rename:
            new_name = simpledialog.askstring(f'Rename {self.type}', f'Enter new {self.type.lower()} name:', parent = self.winfo_toplevel().root)
            if new_name in self.values.values():
                messagebox.showinfo(title = 'Error', message = f'{self.type} already exists.')
                return 0
            elif new_name:
                with core.DBHandler(self.db_file) as db:
                    result = self._rename(db, entry_to_rename, new_name)
                if result:
                    self.update_values()
                    return 1
                return 0
            
    def _rename(self, db, id, new_name):
        raise NotImplementedError('_rename should be implemented in child classes.')
    
    def update_values(self):
        raise NotImplementedError('update_values should be implemented in child classes.')


# profiles menu contains all available profiles
# each profile displays a submenu containing its hunts
class ProfileMenu(ProfHuntMenu):
    def __init__(self, parent, start_hunt):
        super().__init__(parent)
        self.type = 'Profile'
        self.active_hunt_var = tk.IntVar()
        self.active_profile_id = None
        self.values = None
        self.hunts_values = {}
        self.hunts_values_flat = {}
        self.update_values()
        # get the first hunt if no previous hunt selected
        if not start_hunt:
            first_hunt = list(self.hunts_values_flat)
            if first_hunt:
                first_hunt = first_hunt[0]
                self.active_hunt_var.set(first_hunt)
                # this is to get the profile id of the selected hunt
                self.active_profile_id = [hunt[0] for hunt in self.hunts_values.items() if first_hunt in list(hunt[1])][0]
        else:
            self.active_hunt_var.set(start_hunt)
            self.active_profile_id = [hunt[0] for hunt in self.hunts_values.items() if start_hunt in list(hunt[1])][0]

    def _create(self, db, name):
        return db.insert_profile(name)
    
    def _delete(self, db, id):
        return db.delete_profile(id)

    def _rename(self, db, id, new_name):
        return db.rename_profile(id, new_name)
    
    def update_values(self):
        self.delete(0, tk.END)
        self.hunts_values = {}
        with core.DBHandler(self.db_file) as db:
            self.values = db.get_profiles()
        for id, name in self.values.items():
            hunt_menu = HuntMenu(self, id, self.active_hunt_var)
            self.hunts_values = {**self.hunts_values, id: hunt_menu.values}
            self.hunts_values_flat = {**self.hunts_values_flat, **hunt_menu.values}
            self.add_cascade(label = name, menu = hunt_menu)
        self.add_separator()
        self.add_command(label = 'Create Profile', command = self.create_entry)
        self.add_command(label = 'Rename Profile', command = self.rename_entry)
        self.add_command(label = 'Delete Profile', command = self.delete_entry)


# hunts submenu displays all hunts available in a profile
class HuntMenu(ProfHuntMenu):
    def __init__(self, parent, profile, var):
        super().__init__(parent)
        self.type = 'Hunt'
        self.profile_id = profile
        self.active_hunt_var = var
        self.values = None
        self.update_values()

    def _create(self, db, name):
        return db.insert_hunt(name, self.profile_id)
    
    def _delete(self, db, id):
        return db.delete_hunt(id)

    def _rename(self, db, id, new_name):
        return db.rename_hunt(id, new_name)
    
    def update_values(self):
        self.delete(0, tk.END)
        with core.DBHandler(self.db_file) as db:
            self.values = db.get_hunts(self.profile_id)
        for id, name in self.values.items():
            self.add_radiobutton(label = name, var = self.active_hunt_var, value = id, command = self.update)
        self.add_separator()
        self.add_command(label = 'Create Hunt', command = self.create_entry)
        self.add_command(label = 'Rename Hunt', command = self.rename_entry)
        self.add_command(label = 'Delete Hunt', command = self.delete_entry)
    
    def update(self):
        self.parent.active_profile_id = self.profile_id
        self.winfo_toplevel().event_generate("<<HuntSelected>>")


# menu that handles all export data commands
class ExportMenu(CustomMenu):
    def __init__(self, parent):
        super().__init__(parent, tearoff = False)

        self.add_command(label = 'Hunt Data', command = lambda: self.on_export_data('hunt'))
        self.add_command(label = 'Profile Data', command = lambda: self.on_export_data('profile'))
        self.add_command(label = 'All Data', command = lambda: self.on_export_data('all'))
    
    def export_data(self, type = None, ids = None):
        with core.DBHandler(self.winfo_toplevel().db_file) as db:
            if type == 'hunt' and id:
                result = db.export_hunt_data(ids[0])
            elif type == 'profile' and id:
                result = db.export_profile_data(ids[1])
            elif type == 'all':
                result = db.export_all_data()
            if result:
                messagebox.showinfo(title = 'Success', message = f'Successfully extracted data to {db.data_exports_path}')
            else:
                messagebox.showerror(title = 'Error', message = 'Failed to extract data.')

    def on_export_data(self, type = None):
        self.winfo_toplevel().event_generate("<<ExportData>>", data = type)


class ViewMenu(CustomMenu):
    def __init__(self, parent, size, start_view, show_alpha_shiny):
        super().__init__(parent, tearoff = False)
        self.size = size
        self.size_menu = SizeMenu(self, size)
        self.add_cascade(label = 'Size', menu = self.size_menu)

        self.start_view = start_view
        self.col_menu = ColMenu(self, start_view)
        self.add_cascade(label = "Columns", menu = self.col_menu)

        self.show_alpha_shiny_var = tk.BooleanVar()
        self.show_alpha_shiny_var.set(show_alpha_shiny)
        self.add_checkbutton(label = "A|S Count", variable = self.show_alpha_shiny_var, onvalue = True, offvalue = False, command = self.on_as_change)

    def on_as_change(self):
        self.winfo_toplevel().event_generate('<<ASChange>>')


# Decided to not use this for now, using file logging
# # Extra toplevel window to appear when debugging
# # Can also be displayed if user wants to track the ocr engine results
# class LogWindow(tk.Toplevel):
#     def __init__(self, parent = None, mode = 1, **kwargs):
#         super().__init__(parent, **kwargs)
#         self.title(kwargs.get('title', 'Log'))
#         self.geometry(kwargs.get('geometry', '400x300'))

#         self.log_frame = tk.Frame(self)
#         self.log_frame.pack(fill = tk.BOTH, expand = True)

#         self.log_text = tk.Text(self.log_frame, wrap = tk.WORD, state = tk.DISABLED)
#         self.log_text.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)

#         self.scrollbar = tk.Scrollbar(self.log_frame, orient = tk.VERTICAL, command = self.log_text.yview)
#         self.scrollbar.pack(side = tk.RIGHT, fill = tk.Y)

#         self.log_text.config(yscrollcommand = self.scrollbar.set)

#     def log_action(self, action, data):
#         self.log_text.configure(state = tk.NORMAL)
#         self.log_text.insert(action + data + "\n")
#         self.log_text.configure(state = tk.DISABLED)

#     def update_mode(self, mode):
#         pass

class DebugMenu(CustomMenu):

    DEBUG_MODES = {'None': 0,
                   'Soft Log': 1,
                   'Full Log': 2,
                   'Soft Debug': 3,
                   'Full Debug': 4
                }

    def __init__(self, parent):
        super().__init__(parent, tearoff = False)
        self.debug_var = tk.IntVar()
        self.debug_var.set(0)
        self.debug_window = None
        for k, v in self.DEBUG_MODES.items():
            self.add_radiobutton(label = k, variable = self.debug_var, value = v, command = self.on_debug_change)

    def on_debug_change(self):
        debug_mode = self.debug_var.get()
        gb.globals.update_debug(debug_mode)
        # if not debug_mode:
        #     self.debug_window.destroy()
        #     self.debug_window = None
        # elif not self.debug_window:
        #     self.debug_window = LogWindow(self, mode = debug_mode)
        # else:
        #     self.debug_window.update_mode(debug_mode)


class OptionsMenu(CustomMenu):
    def __init__(self, parent, size, start_view, show_alpha_shiny):
        super().__init__(parent, tearoff = False)

        self.view_menu = ViewMenu(self, size, start_view, show_alpha_shiny)
        self.add_cascade(label = 'View', menu = self.view_menu)

        self.export_menu = ExportMenu(self)
        self.add_cascade(label = 'Export', menu = self.export_menu)

        self.debug_menu = DebugMenu(self)
        self.add_cascade(label = 'Debug', menu = self.debug_menu)

        self.add_command(label = 'Exit', command = self.on_exit)

    def on_exit(self):
        self.winfo_toplevel().event_generate('<<Exit>>')


# widget that contains all columns in a frame, side by side to form the gui body
# total count is also added here
class Body(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, pady = 0, borderwidth = 0)
        self.db_file = self.winfo_toplevel().db_file_path
        with core.DBHandler(self.db_file) as db:
            self.values = db.get_agg_data(self.winfo_toplevel().profiles_menu.active_hunt_var.get())

        size = self.winfo_toplevel().options_menu.view_menu.size_menu.size_var.get()
        if size:
            col_names = []
            col_values = []
            if self.winfo_toplevel().options_menu.view_menu.col_menu.col_var[0].get():
                col_names.append('Last')
                col_values.append(dict(list(self.values['last'].items())[:size]))
            if self.winfo_toplevel().options_menu.view_menu.col_menu.col_var[1].get():
                col_names.append('Top')
                col_values.append(dict(list(self.values['top'].items())[:size]))
            show_alpha_shiny = self.winfo_toplevel().options_menu.view_menu.show_alpha_shiny_var.get()
            for i, (name, values) in enumerate(zip(col_names, col_values)):
                CountCol(self, name, values, show_alpha_shiny = show_alpha_shiny).grid(row = 0, column = i)
            col_size = len(col_names) if len(col_names) > 0 else 1
            tk.Label(self, text = 'Total ' + str(self.values['total']), font = DEFAULT_FONT, pady = 5, borderwidth = 0, padx = 0)\
                .grid(sticky = tk.E, columnspan = col_size, row = 1, column = 0)
        else:
            tk.Label(self, text = 'Total ' + str(self.values['total']), font = DEFAULT_FONT, pady = 0, borderwidth = 0, padx = 0).pack(fill = tk.BOTH)

# root class
# app root should be centered (to allow children to be centered as well)
# should also be invisible
class Root(tk.Tk):
    def __init__(self, root_path):
        super().__init__()
        self.attributes('-alpha', 0.0)
        self.geometry(f'0x0+{int(self.winfo_screenwidth()/2)-50}+{int(self.winfo_screenheight()/2)-50}')
        self.title('YAPEC')
        self.root_path = root_path
        self.logo_path = os.path.join(self.root_path, 'icons')
        self.logo = os.path.join(self.logo_path, 'logo.ico')
        self.wm_iconbitmap(default = self.logo)
    

# main app class
# this top level contains all menus and widgets
# it gets and saves last selected options to allow starting from previous state
# and call the (re)creation of the menu and body
class MainWindow(tk.Toplevel):
    def __init__(self, root_path, db_file):
        self.root_path = root_path
        self.root = Root(root_path)
        super().__init__(self.root)
        self.overrideredirect(True)
        self.root.bind('<Unmap>', self._withdraw)
        self.root.bind('<Map>', self._deiconify)
        self.drag_data = {'x': 0, 'y': 0}
        self.bind('<ButtonPress-1>', self.start_drag)
        self.bind('<B1-Motion>', self.drag)
        self.minsize(125, 25)

        self.values = None
        self.db_path = os.path.join(self.root_path, 'data')
        self.db_file = db_file
        self.db_file_path = os.path.join(self.db_path, db_file)
        self.init_file = os.path.join(self.root_path, 'config', 'init.json')
        if not os.path.isfile(self.init_file):
            with open(self.init_file, "w") as f:
                f.write('{}')
        self.init_values = self.read_json()
        self.create_menu_bar(size = self.init_values.get('size', 3),
                             start_view = self.init_values.get('cols', (True, True)),
                             start_hunt = self.init_values.get('active_hunt_id', None),
                             show_alpha_shiny = self.init_values.get('as', True)
                            )
        self.body = None # need this since create_body checks for body in order to recreate it
        self.create_body()
        self.bind('<<HuntSelected>>', lambda event: self.create_body())
        self.bind('<<ColChange>>', lambda event: self.create_body())
        self.bind('<<SizeChange>>', lambda event: self.create_body())
        self.bind('<<ASChange>>', lambda event: self.create_body())
        cmd = self.register(lambda type: self.options_menu.export_menu.export_data(type, ids = [self.profiles_menu.active_hunt_var.get(), self.profiles_menu.active_profile_id]))
        self.tk.call('bind', self, '<<ExportData>>', cmd + ' %d')
        self.bind('<<Exit>>', lambda event: self.exit())

    # wrappers to pass to root
    # so that root and main do the same thing at the same time
    # this allows (min|max)izing main by clicking the icon (root)
    def _withdraw(self, event):
        self.withdraw()
    
    def _deiconify(self, event):
        self.deiconify()

    # allow dragging
    def start_drag(self, event):
        self.drag_data['x'] = event.x
        self.drag_data['y'] = event.y

    def drag(self, event):
        delta_x = event.x - self.drag_data['x']
        delta_y = event.y - self.drag_data['y']
        x = self.winfo_x() + delta_x
        y = self.winfo_y() + delta_y
        self.geometry(f'+{x}+{y}')

    # make sure main is on top of desired hwnd
    def put_on_top_of_window(self, target_hwnd = None):
        app_hwnd = win32gui.FindWindow(None, 'YAPEC')
        # need to check topmost like this
        # checking straight from .attributes behaves weirdly
        # seems that tkinter resets the topmost on check
        attr = iter(self.attributes())
        is_topmost = dict(zip(attr, attr))['-topmost']
        if win32gui.GetForegroundWindow() in [target_hwnd, app_hwnd]:
            if not is_topmost:
                self.attributes('-topmost', True)
        else:
            if is_topmost:
                self.attributes('-topmost', False)

    def create_menu_bar(self, size, start_hunt, start_view, show_alpha_shiny):
        self.menu_bar = CustomMenu(self)

        self.options_menu = OptionsMenu(self.menu_bar, size, start_view, show_alpha_shiny)
        self.menu_bar.add_cascade(label = 'Options', menu = self.options_menu)

        self.profiles_menu = ProfileMenu(self.menu_bar, start_hunt = start_hunt)
        self.menu_bar.add_cascade(label = 'Profile', menu = self.profiles_menu)

        # wanted to add a close button to custom menu bar but wasn't successful with positioning :(
        # need to find a way to get this to the right side
        # self.menu_bar.add_command(label = '×', command = self.root.destroy)

        self.config(menu = self.menu_bar)

    def create_body(self):
        new_body = Body(self)
        new_body.grid(row = 0, column = 0)
        if self.body:
            self.body.forget()
            self.body.destroy()
        self.body = new_body
        self.save_json()

    # save last state of variables
    def save_json(self):
        self.init_values = {
            'size': self.options_menu.view_menu.size_menu.size_var.get(),
            'cols': [col.get() for col in self.options_menu.view_menu.col_menu.col_var],
            'as': self.options_menu.view_menu.show_alpha_shiny_var.get(),
            'active_hunt_id': self.profiles_menu.active_hunt_var.get()
        }
        max_retries = 3
        tries = 0
        while tries < max_retries:
            try:
                with open(self.init_file, 'w') as f:
                    json.dump(self.init_values, f)
            except Exception:
                tries += 1
                time.sleep(1)
            else:
                return 1
        else:
            messagebox.showerror(title = 'Error', message = f'Failed to save JSON file after {max_retries} retries.')
            return 0
    
    # read last state
    def read_json(self):
        max_retries = 3
        tries = 0
        while tries < max_retries:
            try:
                with open(self.init_file, 'r') as f:
                    init_values = json.load(f)
            except Exception:
                tries += 1
                time.sleep(1)
            else:
                return init_values
        else:
            messagebox.showerror(title = 'Error', message = f'Failed to read JSON file after {max_retries} retries.')
            return {}

    def exit(self):
        self.save_json()
        self.root.destroy()

if __name__ == '__main__':
    db_file = 'yapec.sqlite3'
    app = MainWindow(db_file)
    app.mainloop()