from pathlib import Path
from ctypes import windll
import win32ui
import win32gui
import re
import os
import time
import cv2
import pytesseract
import sqlite3
import numpy as np


class Pokemmo:

    def __init__(self, hwnd):
        self.hwnd = hwnd
    
    @classmethod
    def from_title(cls, title = 'pokemmo'):
        hwnd = cls._find_pokemmo(title)
        if not hwnd:
            user_answer = input('PokeMMO was not found, would you like to launch it? (y/n)')
            if user_answer.lower() == 'y':
                pokemmo_path = Path(__file__).resolve().parents[2]
                os.system(os.path.join(str(pokemmo_path), 'PokeMMO.exe'))
                time.sleep(10)
                hwnd = cls._find_pokemmo(title)
            if not hwnd:
                raise Exception('PokeMMO was not found.')      
        return cls(hwnd)

    @classmethod
    def _find_pokemmo(cls, title):
        cy_to_lat = {'Р': 'P', 'О': 'O', 'К': 'K', 'М': 'M', 'Е': 'E',
                     'р': 'p', 'о': 'o', 'к': 'k', 'м': 'm', 'е': 'e'}
        cy_to_lat = str.maketrans(cy_to_lat)

        list_of_windows = []
        def emu_windows_callback(hwnd, extra):
            list_of_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(emu_windows_callback, None)

        pokemmo_hwnd = [hwnd for hwnd, ttl in list_of_windows if title in ttl.lower().translate(cy_to_lat)]
        if pokemmo_hwnd:
            return pokemmo_hwnd[0]
        return None

    def take_screenshot(self, save_path = None):
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
        bitmap_bits = bitmap.GetBitmapBits()
        bitmap_np = np.asarray(bitmap_bits, dtype=np.uint8)
        screenshot = np.reshape(bitmap_np, (bitmap_info['bmHeight'], bitmap_info['bmWidth'], 4))

        win32gui.DeleteObject(bitmap.GetHandle())
        copy_dc.DeleteDC()
        bitmap_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)

        if result == 1 and save_path:
            cv2.imwrite(save_path, screenshot)
            
        return CV2ImageHandler(screenshot)


class CV2ImageHandler:
    
    SPECIAL_PERCENTAGES = {
        'battle': [0.6, 0.75, 0.15, 0.45],
        'horde': [0.05, 0.2, 0.3, 0.70],
        'pokemon': [0.1, 0.2, 0.15, 0.3]
    }
    
    def __init__(self, img):
        self.img = img
        
    def crop_by_size(self, crop_size):
        h, w, _ = self.img.shape

        if len(crop_size) != 4:
            raise ValueError('crop_size must have 4 values: [top, bottom, left, right].')

        if crop_size[0] < 0 or crop_size[1] > h or crop_size[2] < 0 or crop_size[3] > w:
            raise ValueError('Crop size exceeds image dimensions.')

        return self.__class__(self.img[crop_size[0]:crop_size[1], crop_size[2]:crop_size[3]])
    
    def crop_by_percentage(self, percentages):
        h, w, _ = self.img.shape

        if len(percentages) != 4:
            raise ValueError('percentages must have 4 values: [top, bottom, left, right].')
 
        if any([p > 1 or p < 0 for p in percentages]):
            raise ValueError('Percentages out of range, must be between 0 and 1.')

        crop_size = [int(wh*perc) for wh, perc in zip([h, h, w, w], percentages)]
        
        return self.__class__(self.img[crop_size[0]:crop_size[1], crop_size[2]:crop_size[3]])
    
    def transform_image_for_ocr(self):
        img_copy = self.img
        hls_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HLS)
        S_channel = hls_img[:, :, 2]
        inv_img = cv2.bitwise_not(S_channel)
        to_black_mask = cv2.inRange(inv_img, 0, 254*0.999)
        black_img = inv_img
        black_img[to_black_mask > 0] = 0
        img_copy[:, :, 3] = black_img
        img_copy[img_copy[:, :, 3] == 0] = [0, 0, 0, 0]
        
        return self.__class__(img_copy[:, :, :3])
    
    def perform_ocr(self):
        return OCRResultHandler(pytesseract.image_to_string(self.img))
    
    def process_image(self, battle_type):
        img = self.crop_by_percentage(self.SPECIAL_PERCENTAGES[battle_type])
        img = img.transform_image_for_ocr()
        ocr_result = img.perform_ocr()
        return ocr_result


class OCRResultHandler:
    DEFAULT_PATTERN = '^a wild .+ appeared'
    
    def __init__(self, result):
        self.result = result

    def battle_started(self, pattern = None):
        pattern = pattern or self.DEFAULT_PATTERN
        return re.search(pattern, self.result.lower())
    
    def battle_type(self, pattern = None):
        pattern = pattern or self.DEFAULT_PATTERN
        return 'horde' if 'horde' in self.result else 'pokemon'
    
    def extract_pokemon_from_battle(self):
        pattern = r'((?:shiny\s+)?(?:alpha\s+)?(?:mr\.?\s+)?[^\s]*(?:\s+jr\.?)?)\s+(?:lv\.?)\s+([0-9]*)'
        matches = re.findall(pattern, self.result.lower())
        pokemon_list = []
        for name, lvl in matches:
            name = name.lower()
            shiny = 0
            alpha = 0
            if 'shiny' in name:
                shiny = 1
                name = re.sub('shiny\s*', '', name)
            if 'alpha' in name:
                alpha = 1
                name = re.sub('alpha\s*', '', name)
            try:
                lvl = int(lvl)
            except Exception:
                lvl = None
            pokemon_list.append((time.time(), name, lvl, shiny, alpha))

        return pokemon_list


class DBHandler:
    MAX_RETRIES = 3

    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    @classmethod
    def setup_db(cls, db_file):
        with cls(db_file) as db:
            query = '''
                CREATE TABLE IF NOT EXISTS encounters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    name TEXT,
                    level INTEGER,
                    shiny INTEGER,
                    alpha INTEGER
                )
            '''
            tries = 0
            while tries < db.MAX_RETRIES:
                try:
                    db.cursor.execute(query)
                    db.connection.commit()
                except Exception:
                    tries += 1
                    time.sleep(1)
                else:
                    return 1
            else:
                print(f'Failed to setup database after {db.MAX_RETRIES} retries.')
                return 0

    def store_data(self, data):
        query = '''
            INSERT INTO encounters (timestamp, name, level, shiny, alpha)
            VALUES (?, ?, ?, ?, ?)
        '''
        tries = 0
        while tries < self.MAX_RETRIES:
            try:
                self.cursor.executemany(query, data)
                self.connection.commit()
            except Exception:
                tries += 1
                time.sleep(1)
            else:
                return 1
        else:
            print(f'Failed to store data after {self.MAX_RETRIES} retries.')
            return 0

    def close_connection(self):
        self.cursor.close()
        self.connection.close()


if __name__ == '__main__':
    total = []
    i = 0
    db_file = os.path.join(str(Path(__file__)), 'data', 'encounters.sqlite3')
    pokemmo = Pokemmo.from_title()
    DBHandler.setup_db(db_file)
    while True:
        tries = 0
        time.sleep(1)
        img = pokemmo.take_screenshot()
        ocr_result = img.process_image('battle')
        battle_started = ocr_result.battle_started()
        battle_type = ocr_result.battle_type()
        while battle_started and tries < 3:
            time.sleep(1)
            img = pokemmo.take_screenshot()
            ocr_result = img.process_image(battle_type)
            pokemon_found = ocr_result.extract_pokemon_from_battle()
            if pokemon_found:
                print(pokemon_found)
                with DBHandler(db_file) as db:
                    db.store_data(pokemon_found)
                i += 1
                break
            else:
                tries += 1