# YAPEC (Yet Another PokeMMO Encounter Counter)

**Note: This project is a work in progress and is primarily for learning purposes.**

YAPEC is a Python application designed to track and count Pokemon encounters in the popular game PokeMMO. It utilizes OCR (Optical Character Recognition) and image processing techniques to extract information from in-game screenshots and store the encounter data in a SQLite database.

## Features

- Automatically detects and captures game screenshots.
- Processes the captured screenshots using image processing techniques for optimal OCR accuracy.
- Extracts relevant information such as Pokemon names, levels and shiny/alpha information from the screenshots using OCR.
- Stores the encounter data in a SQLite database for future analysis.

## Dependencies

- Python 3.9.6 or higher: Install Python from the official Python website: [python.org](https://www.python.org)
  - While it may work with older versions of Python, no testing was conducted on those.
- Tesseract OCR Engine: Install Tesseract from the official repository: [Tesseract Installation](https://tesseract-ocr.github.io/tessdoc/Installation.html)

## Installation

1. Install Tesseract OCR Engine following the instructions from the official repository.
2. Add Tesseract to your PATH variable and reboot.
3. Install the required Python version.
4. Clone the YAPEC repository to the mods folder inside your PokeMMO installation folder.
5. Install the required Python dependencies by running: `pip install -r requirements.txt`.

## Usage

1. Launch the PokeMMO game and position the game window appropriately.
2. Run the `yapec.py` script to start the YAPEC application.
3. YAPEC will continuously monitor the game window and capture screenshots at regular intervals.
4. It will process the captured screenshots, extract encounter data using OCR, and store it in the SQLite database.
5. You can view the stored encounter data and perform further analysis using the database.

## Roadmap

- Implement a user interface (UI) for better user interaction and visualization of encounter data.
- Improve code documentation and provide detailed instructions on using the application.
- Add additional features such as encounter statistics, filters, and export functionality.
- Create a dashboard for displaying statistics and insights from the stored encounter data.
- Add support for different operating systems to make the application more accessible.

## Contributing

Contributions to YAPEC are welcome! If you have any ideas, bug reports, or feature requests, please open an issue on the GitHub repository or contact me on the PokeMMO Forum [here](https://forums.pokemmo.com/index.php?/profile/472246-tinquinho/).

## Acknowledgements

- This project is inspired by the Pokemon and PokeMMO games, the desire to learn more about OCR and image processing techniques and the available community tools for encounter counting.
- The OCR functionality is powered by the [pytesseract](https://github.com/madmaze/pytesseract) library, which utilizes the [Tesseract OCR engine](https://github.com/tesseract-ocr/tesseract).
- The image processing operations are implemented using the [OpenCV](https://opencv.org/) Python library.
- The SQLite database interaction is facilitated by the [sqlite3](https://docs.python.org/3/library/sqlite3.html) module in Python's standard library.

**Note: This project is not affiliated with PokeMMO or the Pokemon franchise in any way.**
