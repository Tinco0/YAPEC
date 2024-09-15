import re
import os
import csv
import cv2
import time
import sqlite3
import win32ui
import win32gui
import subprocess
import pytesseract
import numpy as np
import difflib as dl
import tkinter as tk
from pathlib import Path
from ctypes import windll

import src.monster_names as monsters
import src.globals as gb

# not sure where this should really go to resolve the path
mn = monsters.MonsterNames.from_json(os.path.join(Path(__file__).resolve().parents[1], 'config', 'monster_names.json'))

class _ImgSaveCounter:
    def __init__(self):
        self.counter = 0

    def increase(self):
        self.counter += 1
    
    def to_str(self):
        return str(self.counter)

_counter = _ImgSaveCounter()

class PokeMMOHandler:

    def __init__(self, hwnd):
        # save pokemmo window handle
        self.hwnd = hwnd
    
    # class method to search a window handle from a title
    @classmethod
    def from_title(cls, title = 'pokemmo'):
        # get find pokemmo's window handle
        hwnd = cls._find_pokemmo(title)
        # if not found then ask if user wants to launch it
        # this effectivle allow user to launch both apps together
        if not hwnd:
            temp_root = tk.Tk()
            temp_root.withdraw()
            user_answer = tk.messagebox.askyesno(title = 'PokeMMO not found', message = 'PokeMMO was not found, would you like to launch it?')
            temp_root.destroy()
            if user_answer:
                # pokemmo exe should be 4 dirs up since yapec should be in mods folder
                pokemmo_path = Path(__file__).resolve().parents[4]
                try: 
                    subprocess.Popen(os.path.join(str(pokemmo_path), 'PokeMMO.exe'), shell = True, stdout = subprocess.DEVNULL)
                except Exception:
                    raise Exception('PokeMMO.exe was not found.')
                # wait for pokemmo to start. 20s should be enough even on a slow machine
                # could be improved to actually check either subprocess result or that pokemmo is open
                time.sleep(20)
                # try to find it again
                hwnd = cls._find_pokemmo(title)
            # if not found again throw error
            if not hwnd:
                raise Exception('PokeMMO was not found.')
        return cls(hwnd)

    # internal class method to look for the window handle
    @classmethod
    def _find_pokemmo(cls, title):
        # pokemmo is sneaky and sometimes uses cyrillic letters in its title
        # so we overcome this by "translating" them back to latin
        cy_to_lat = {'Р': 'P', 'О': 'O', 'К': 'K', 'М': 'M', 'Е': 'E',
                     'р': 'p', 'о': 'o', 'к': 'k', 'м': 'm', 'е': 'e'}
        cy_to_lat = str.maketrans(cy_to_lat)

        # get al open windows handles and titles
        list_of_windows = []
        def emu_windows_callback(hwnd, extra):
            list_of_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(emu_windows_callback, None)

        # see if any matches title
        pokemmo_hwnd = [hwnd for hwnd, ttl in list_of_windows if title == ttl.lower().translate(cy_to_lat)]
        # if found return first match
        if pokemmo_hwnd:
            return pokemmo_hwnd[0]
        return None

    # this method takes a screenshot of a hwnd ignoring other windows on top of it
    # in simple terms it creates a new window, copies the current one, draws on the new window and screenshots that
    # then retrieves the screenshots bits to a numpy array in opencv format
    def take_screenshot(self):
        left, top, right, bot = win32gui.GetClientRect(self.hwnd)
        width = right - left
        height = bot - top

        hwnd_dc = win32gui.GetWindowDC(self.hwnd)
        copy_dc  = win32ui.CreateDCFromHandle(hwnd_dc)

        bitmap_dc = copy_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(copy_dc, width, height)

        bitmap_dc.SelectObject(bitmap)

        result = windll.user32.PrintWindow(self.hwnd, bitmap_dc.GetSafeHdc(), 1)

        bitmap_info = bitmap.GetInfo()
        bitmap_bits = bitmap.GetBitmapBits(True)
        bitmap_np = np.fromstring(bitmap_bits, dtype = np.uint8)
        
        screenshot = np.reshape(bitmap_np, (bitmap_info['bmHeight'], bitmap_info['bmWidth'], 4))

        win32gui.DeleteObject(bitmap.GetHandle())
        copy_dc.DeleteDC()
        bitmap_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)
        
        # return custom class image handler
        return CV2ImageHandler(screenshot)


# class to handle an image
class CV2ImageHandler:
    
    # percentages to only look for strings on a section of the screen
    # optimizes OCR usage
    # [height_start (from top), height_end, width_start (from left), width_end]
    SPECIAL_PERCENTAGES = {
        'battle': [0.6, 0.75, 0.15, 0.45],
        'horde': {
            'pokemon': [0.05, 0.2, 0.3, 0.70],
            'status': [], # depend on pokemon
            'hpbar': [[0.3, 0.43, 0, 1], [0.55, 0.7, 0, 1]], # depend on pokemon
        },
        'single': {
            'pokemon': [0.1, 0.2, 0.15, 0.3],
            'status': [[0.25, 0.45, 0.1, 0.15]], # depend on pokemon
            'hpbar': [[0.45, 0.65, 0, 1]] # depend on pokemon
        }
    }
    
    def __init__(self, img):
        self.img = img
    
    @classmethod
    def from_file(cls, file_path):
        image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        
        if image is None:
            raise FileNotFoundError(f"Unable to open image file: {file_path}")

        return cls(image)

    # crop by image size
    # cropping on opencv image is just getting a specific section of the underlying array
    # currently not used for anything, since it is better to use percentages due to different size windows
    def crop_by_size(self, crop_size):
        h, w, _ = self.img.shape

        if len(crop_size) != 4:
            raise ValueError('crop_size must have 4 values: [top, bottom, left, right].')

        if crop_size[0] < 0 or crop_size[1] > h or crop_size[2] < 0 or crop_size[3] > w:
            raise ValueError('Crop size exceeds image dimensions.')

        return self.__class__(self.img[crop_size[0]:crop_size[1], crop_size[2]:crop_size[3]])
    
    # crop image by percentage of size
    def crop_by_percentage(self, percentages):
        h, w, _ = self.img.shape

        if len(percentages) != 4:
            raise ValueError('percentages must have 4 values: [top, bottom, left, right].')
 
        if any([p > 1 or p < 0 for p in percentages]):
            raise ValueError('Percentages out of range, must be between 0 and 1.')

        crop_size = [int(wh*perc) for wh, perc in zip([h, h, w, w], percentages)]
        
        return self.__class__(self.img[crop_size[0]:crop_size[1], crop_size[2]:crop_size[3]])
    
    def insert_black_rectangle(self, percentages):
        h, w, _ = self.img.shape

        if len(percentages) != 4:
            raise ValueError('percentages must have 4 values: [top, bottom, left, right].')
 
        if any([p > 1 or p < 0 for p in percentages]):
            raise ValueError('Percentages out of range, must be between 0 and 1.')
        
        coords = [int(wh*perc) for wh, perc in zip([h, h, w, w], percentages)]

        return self.__class__(cv2.rectangle(self.img, (coords[2], coords[0]), (coords[3], coords[1]), (255, 0, 0), -1))

    # apply some opencv image transformations to make it easier
    # for tesseract to get strings
    def transform_image_for_ocr(self):
        img_copy = self.img
        # change to hls
        hls_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HLS)
        # get S channel only
        S_channel = hls_img[:, :, 2]
        # invert image
        inv_img = cv2.bitwise_not(S_channel)
        # make most of image black, except for white areas
        to_black_mask = cv2.inRange(inv_img, 0, 254*0.999)
        black_img = inv_img
        black_img[to_black_mask > 0] = 0
        # set black image as alpha channel
        img_copy[:, :, 3] = black_img
        # apply new alpha channel to image
        img_copy[img_copy[:, :, 3] == 0] = [0, 0, 0, 0]
        
        return self.__class__(img_copy[:, :, :3])
    
    # perform ocr on image using tesseract
    def perform_ocr(self):
        # this is the current bottleneck, since pytesseract uses I/O to pass the images to tesseract.
        # apparently there is a way to use stdin/out but I haven't gotten around writing own code to do it
        # for now pytesseract stays
        # https://github.com/madmaze/pytesseract/issues/172
        return OCRResultHandler(pytesseract.image_to_string(self.img))
    
    # wrapper to apply all steps to get ocr
    def process_image(self, battle_type):
        if battle_type == 'battle':
            self.img_crop = self.crop_by_percentage(self.SPECIAL_PERCENTAGES[battle_type])
        else:
            self.img_crop = self.crop_by_percentage(self.SPECIAL_PERCENTAGES[battle_type]['pokemon'])
            for perc in self.SPECIAL_PERCENTAGES[battle_type]['status']:
                self.img_crop = self.img_crop.insert_black_rectangle(perc)
            for perc in self.SPECIAL_PERCENTAGES[battle_type]['hpbar']:
                self.img_crop = self.img_crop.insert_black_rectangle(perc)
        self.img_ocr = self.img_crop.transform_image_for_ocr()
        ocr_result = self.img_ocr.perform_ocr()
        return ocr_result

    def log_images(self):
        cnt = _counter.to_str()
        cv2.imwrite(os.path.join(gb.globals.get_debug_path(), f'{cnt}_1_ss.png'), self.img)
        if hasattr(self, 'img_crop'):
            cv2.imwrite(os.path.join(gb.globals.get_debug_path(), f'{cnt}_2_crop.png'), self.img_crop.img)
        if hasattr(self, 'img_ocr'):
            cv2.imwrite(os.path.join(gb.globals.get_debug_path(), f'{cnt}_3_ocr.png'), self.img_ocr.img)
        _counter.increase()
            


# class to handle tesseract return object
class OCRResultHandler:
    
    # default battle start string
    # this could be customizable in the future
    DEFAULT_PATTERN = '^a wild .+ appeared'
    
    def __init__(self, result):
        self.result = result

    # check for battle start patter
    def battle_started(self, pattern = None):
        pattern = pattern or self.DEFAULT_PATTERN

        return re.search(pattern, self.result.lower())
    
    # chek if horde or single pokemon
    def battle_type(self, pattern = None):
        pattern = pattern or self.DEFAULT_PATTERN
        return 'horde' if 'horde' in self.result else 'single'
    
    # get pokemon id from its name
    def get_id_from_name(self, name):
        if name in list(mn.INV_MONSTER_NAMES_DICT):
            return mn.INV_MONSTER_NAMES_DICT[name]
        # if name not exact then try to get closest match
        closest_name = dl.get_close_matches(name, list(mn.INV_MONSTER_NAMES_DICT), n = 1, cutoff = 0.8)
        if closest_name and closest_name in list(mn.INV_MONSTER_NAMES_DICT):
            return mn.INV_MONSTER_NAMES_DICT[closest_name]
        return 0

    # extract all pokemon info
    def extract_pokemon_from_battle(self):
        # look for strings 'shiny', 'alpha', pokemon name and level
        # mime jr and mr mime were some exceptions to the regex
        pattern = r'((?:shiny\s+)?(?:alpha\s+)?(?:mr\.?\s+)?[^\s]*(?:\s+jr\.?)?)\s+(?:lv\.?)\s+([0-9]*)'
        matches = re.findall(pattern, self.result.lower())
        pokemon_list = []
        # for each pokemon info found
        # check if shiny, if alpha, if level is readable and if name produces id
        # only id is truly necessary. Also saves encounter time
        for name, lvl in matches:
            shiny = 0
            alpha = 0
            if 'shiny' in name:
                shiny = 1
                name = re.sub('shiny\s*', '', name)
            if 'alpha' in name:
                alpha = 1
                name = re.sub('alpha\s*', '', name)
            id = self.get_id_from_name(name.lower())
            try:
                lvl = int(lvl)
            except Exception:
                lvl = None
            if id:
                pokemon_list.append((time.time(), id, lvl, shiny, alpha))
        return pokemon_list


# class to handle db commands
class DBHandler:

    # max retries for commands
    MAX_RETRIES = 3
        
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        # where to put data exports, "hardcoded" to one dir up from db_file for now
        self.data_exports_path = os.path.join(self.db_file, 'data_exports')

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()
    
    def close_connection(self):
        self.cursor.close()
        self.connection.close()

    # class method to setup a db that contains all necessary tables
    @classmethod
    def setup_db(cls, db_file):
        with cls(db_file) as db:
            # tables should be:
            # profiles
            # hunts (every hunt belongs to a profiles)
            # encounters to save pokemon encounter data (every encounter is linked to a hunt)
            # manual encounters to allow user to add encounter count manually (not used yet)
            # there is a trigger that creates a default hunt once a profile is created (every profile should have at least one hunt)
            # insert initial default profile
            # create a monster names table so that mon names are available in db (not used yet)
            queries = [
            '''
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            ''',
            '''
                CREATE TABLE IF NOT EXISTS hunts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    profile_id INTEGER,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                    CONSTRAINT hunts_unique_constraint UNIQUE (name, profile_id)
                )
            ''',
            '''
                CREATE TABLE IF NOT EXISTS encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    monster_id INTEGER NOT NULL,
                    level INTEGER,
                    shiny INTEGER NOT NULL,
                    alpha INTEGER NOT NULL,
                    hunt_id INTEGER NOT NULL,
                    FOREIGN KEY(hunt_id) REFERENCES hunts(id) ON DELETE CASCADE
                )
            ''',
            '''
                CREATE TABLE IF NOT EXISTS manual_encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    monster_id TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    shiny INTEGER NOT NULL,
                    alpha INTEGER NOT NULL,
                    hunt_id INTEGER NOT NULL,
                    FOREIGN KEY(hunt_id) REFERENCES hunts(id) ON DELETE CASCADE
                )
            ''',
            '''
                CREATE TRIGGER IF NOT EXISTS insert_default_hunt 
                AFTER INSERT ON profiles
                BEGIN
                    INSERT INTO hunts (name, profile_id)
                    SELECT 'Hunt 1', MAX(id)
                    FROM profiles;
                END
            ''',
            '''
                INSERT INTO profiles (name)
                SELECT 'Profile 1'
                WHERE NOT EXISTS (SELECT 1 FROM profiles)
            ''',
            '''
                CREATE TABLE IF NOT EXISTS monster_names (
                    monster_id INTEGER PRIMARY KEY,
                    monster_name TEXT NOT NULL
                )
            '''
            ]
            monster_query = '''
                INSERT OR IGNORE INTO monster_names (monster_id, monster_name)
                VALUES (?, ?)
            '''
            # try to execute all queries and monster query
            tries = 0
            while tries < db.MAX_RETRIES:
                try:
                    for query in queries:
                        db.cursor.execute(query)
                    db.cursor.executemany(monster_query, list(mn.MONSTER_NAMES_DICT.items()))
                    db.connection.commit()
                except Exception:
                    tries += 1
                    time.sleep(1)
                else:
                    return 1
            else:
                tk.messagebox.showerror(title = 'Error', message = f'Failed to setup database after {db.MAX_RETRIES} retries.')
                return 0

    # base method to execute a dml (no fetching) query
    def _execute_query(self, query, data = None, action = 'execute query'):
        tries = 0
        if gb.globals.DEBUG_MODE in [2, 4]:
            self.log_action(action, query, data)
        if gb.globals.DEBUG_MODE >= 3:
            return 1
        while tries < self.MAX_RETRIES:
            try:
                if data:
                    self.cursor.executemany(query, data)
                else:
                    self.cursor.execute(query)
                self.connection.commit()
            except Exception:
                tries += 1
                time.sleep(1)
            else:
                return 1
        else:
            tk.messagebox.showerror(title = 'Error', message = f'Failed to {action} after {self.MAX_RETRIES} retries.')
            return 0
    
    # base method to execute queries whose results should be fetched
    def _fetch_query(self, query, data = None, action = 'fetch query', log = True):
        tries = 0
        if gb.globals.DEBUG_MODE in [2, 4] and log:
            self.log_action(action, query, data)
        while tries < self.MAX_RETRIES:
            try:
                if data:
                    result = self.cursor.execute(query, data)
                else:
                    result = self.cursor.execute(query)
                return result.fetchall()
            except Exception:
                tries += 1
                time.sleep(1)
        else:
            tk.messagebox.showerror(title = 'Error', message = f'Failed to {action} after {self.MAX_RETRIES} retries.')
            return []

    # insert wrapper for encounter data
    def insert_data(self, data):
        query = '''
            INSERT INTO encounters (timestamp, monster_id, level, shiny, alpha, hunt_id)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        return self._execute_query(query, data, 'insert data')

    # wrappers for insert, rename, delete and get ops for profiles and hunts tables 
    def insert_profile(self, name):
        query = '''
            INSERT INTO profiles (name)
            VALUES (?)
        '''
        return self._execute_query(query, [(name,)], 'insert profile')
    
    def delete_profile(self, id):
        query = '''
            DELETE FROM profiles
            WHERE id = ?;
        '''
        return self._execute_query(query, [(id,)], 'delete profile')
    
    def rename_profile(self, id, new_name):
        query = '''
            UPDATE profiles
            SET name = ?
            WHERE id = ?
        '''
        return self._execute_query(query, [(new_name, id)], 'rename profile')
    
    def get_profiles(self):
        query = '''
            SELECT id, name FROM profiles
        '''
        result = self._fetch_query(query, action = 'get profiles')
        return {row[0]: row[1] for row in result}

    def insert_hunt(self, name, profile):
        query = '''
                INSERT INTO hunts (name, profile_id)
                VALUES (?, ?)
            '''
        return self._execute_query(query, [(name, profile)], 'insert hunt')
    
    def delete_hunt(self, id):
        query = '''
            DELETE FROM hunts
            WHERE id = ?;
        '''
        return self._execute_query(query, [(id,)], 'delete hunt')
    
    def rename_hunt(self, id, new_name):
        query = '''
            UPDATE hunts
            SET name = ?
            WHERE id = ?
        '''
        return self._execute_query(query, [(new_name, id)], 'rename hunt')
    
    def get_hunts(self, profile):
        query = '''
            SELECT id, name FROM hunts
            WHERE profile_id = ?
        '''
        result = self._fetch_query(query, (profile,), 'get hunts')
        return {row[0]: row[1] for row in result}
    
    # method to get agg data to display in gui
    def get_agg_data(self, id):
        # we display up to last 5 encountered mons, top 5 and also total
        queries = [
        '''
            SELECT
                monster_id,
                COUNT(monster_id) AS qty,
                SUM(alpha) AS qty_a,
                SUM(shiny) AS qty_s
            FROM encounters
            WHERE hunt_id = ?1
            GROUP BY monster_id
            ORDER BY MAX(timestamp) DESC
            LIMIT 5
        ''',
        '''
            SELECT
                monster_id,
                COUNT(monster_id) AS qty,
                SUM(alpha) AS qty_a,
                SUM(shiny) AS qty_s
            FROM encounters
            WHERE hunt_id = ?1
            GROUP BY monster_id
            ORDER BY qty DESC
            LIMIT 5
        ''',
        '''
            SELECT
                COUNT(*) AS qty
            FROM encounters
            WHERE hunt_id = ?1
        '''
        ]
        results = [self._fetch_query(query, (id,), 'get aggregated data') for query in queries]
        last = {row[0]: {'normal': row[1], 'alpha': row[2], 'shiny': row[3]} for row in results[0]}
        top = {row[0]: {'normal': row[1], 'alpha': row[2], 'shiny': row[3]} for row in results[1]}
        total = [row[0] for row in results[2]][0]

        return {'last': last, 'top': top, 'total': total}
    
    # base method to extract data for export op
    def _export_data(self, type, id):
        if type == 'hunt':
            where = f'e.hunt_id = {id}'
            suffix = f'hunt_id_{id}'
        elif type == 'profile':
            where = f'h.profile_id = {id}'
            suffix = f'profile_id_{id}'
        elif type == 'all':
            where = '1 = 1'
            suffix = 'all'
        else:
            raise ValueError('type should be one of "hunt", "profile" or "all".')
        query = f'''
            SELECT
                DATETIME(e.timestamp, "unixepoch", "localtime") AS datetime,
                e.monster_id AS pokedex_entry,
                m.monster_name AS pokemon,
                e.level,
                e.shiny,
                e.alpha,
                h.id AS hunt_id,
                h.name AS hunt_name,
                h.profile_id AS profile_id,
                p.name AS profile_name
            FROM encounters AS e
                LEFT JOIN monster_names AS m
                    ON e.monster_id = m.monster_id
                LEFT JOIN hunts AS h
                    ON e.hunt_id = h.id
                LEFT JOIN profiles AS p
                    ON h.profile_id = p.id
            WHERE {where}
        '''
        result = self._fetch_query(query, action = 'get data')
        file_name = time.strftime(f"%Y_%m_%d__%H_%M_%S__{suffix}_data.csv", time.localtime())
        file_path = os.path.join(self.data_exports_path, file_name)
        Path(self.data_exports_path).mkdir(parents=True, exist_ok=True)
        try:
            with open(file_path, 'w', newline = '') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([d[0] for d in self.cursor.description])
                writer.writerows(result)
        except Exception:
            return 0
        else:
            return 1

    # can export hunt, profile or all data
    def export_hunt_data(self, id):
        return self._export_data(type = 'hunt', id = id)
        
    def export_profile_data(self, id):
        return self._export_data(type = 'profile', id = id)

    def export_all_data(self):
        return self._export_data(type = 'all', id = id)
    
    def log_action(self, action, query, data):
        log_file_path = os.path.join(gb.globals.get_debug_path(), '0_0_session.log')

        # Prepare the log entry
        log_entry = (
            f"{time.strftime('%Y%m%d_%H%M%S', time.localtime())} - ACTION: {action}\n"
            f"QUERY: {query}\n"
            f"DATA: {str(data)}\n"
            "------------------------------------\n"
        )

        # Write the log entry to the file
        with open(log_file_path, 'a') as log_file:
            log_file.write(log_entry)

if __name__ == '__main__':
    pass