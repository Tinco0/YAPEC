import threading
import queue
import time
import os

import src.core as core
import src.globals as gb

class TaskManager:
    def __init__(self, pokemmo, app):
        self.pokemmo = pokemmo
        self.app = app
        self.db_file = self.app.db_file_path
        self.task_queue = queue.Queue()
        self.threads = None

    def _worker(self):
        while True:
            task = self.task_queue.get()
            if task is None:
                break
            elif not isinstance(task, tuple) or len(task) == 0:
                pass # wrong task type ignore
            elif task[0] == 'battle':
                self._process_battle()
            elif len(task) >= 2: # we need the right amount of params
                self._process_pokemon(task[0], task[1])
            self.task_queue.task_done()

    def _process_pokemon(self, battle_type, tries):
        if tries < 3:
            img = self.pokemmo.take_screenshot()
            ocr_result = img.process_image(battle_type)
            pokemon_found = ocr_result.extract_pokemon_from_battle()
            if gb.globals.DEBUG_MODE:
                if gb.globals.DEBUG_MODE >= 3:
                    img.log_images()
                self.log_action('ocr_result', ocr_result.result)
                self.log_action('pokemon found', pokemon_found)
            if pokemon_found:
                hunt_id = self.app.profiles_menu.active_hunt_var.get()
                pokemon_found = [pokemon_data + (hunt_id,) for pokemon_data in pokemon_found]
                with core.DBHandler(self.db_file) as db:
                    db.insert_data(pokemon_found)
                # update GUI after insert
                self.app.create_body()
                time.sleep(1)
                self.task_queue.put(('battle',))
            else:
                time.sleep(1)
                self.task_queue.put(('pokemon', tries + 1))
        else:
            self.task_queue.put(('battle',))
                

    def _process_battle(self):
        tries = 0
        self.app.put_on_top_of_window(self.pokemmo.hwnd)
        img = self.pokemmo.take_screenshot()
        ocr_result = img.process_image('battle')
        battle_started = ocr_result.battle_started()
        battle_type = ocr_result.battle_type()
        if gb.globals.DEBUG_MODE in [2, 4]: # if full log/debug
            self.log_action('battle check', (battle_started, battle_type))
        if battle_started:
            time.sleep(1)
            self.task_queue.put((battle_type, 0))
        else:
            time.sleep(1)
            self.task_queue.put(('battle',))

    def start(self):
        self.thread = threading.Thread(target=self._worker)
        self.thread.start()
        self.task_queue.put(('battle',))

    def stop(self):
        self.task_queue.put(None)
        self.thread.join()

    def log_action(self, action, data):
        log_file_path = os.path.join(gb.globals.get_debug_path(), '0_0_session.log')

        # Prepare the log entry
        log_entry = (
            f"{time.strftime('%Y%m%d_%H%M%S', time.localtime())} - ACTION: {action}\n"
            f"DATA: {str(data)}\n"
            "------------------------------------\n"
        )

        # Write the log entry to the file
        with open(log_file_path, 'a') as log_file:
            log_file.write(log_entry)

