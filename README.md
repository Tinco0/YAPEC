# YAPEC (Yet Another PokeMMO Encounter Counter)

YAPEC is a Python application designed to track and count Pokémon encounters in the popular game PokeMMO. It uses OCR (Optical Character Recognition) and image processing techniques to extract information from in-game screenshots and store encounter data in a SQLite database.

## Features

- Automatically detects and captures game screenshots.
- Processes the captured screenshots using image processing techniques to optimize OCR accuracy.
- Extracts relevant information such as Pokémon names, levels, and shiny/alpha status from screenshots using OCR.
- Stores encounter data in a SQLite database for future analysis.

## Dependencies

- **Python 3.9.6**: Install Python from the official Python website: [python.org](https://www.python.org)
  - While other versions of Python might work, they have not been tested.
- **Tesseract OCR Engine**: Install Tesseract from the official repository: [Tesseract Installation](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- **Windows 10**: The application relies heavily on the Win32 Python API. Contributions to support other platforms are welcome.
  - It may work on different versions of Windows, but this has not been tested.

## Installation

1. Install the Tesseract OCR Engine following the instructions from the official repository.
2. Add Tesseract to your PATH variable and reboot your system.
3. Install the required Python version.
4. Clone (or download) the YAPEC repository to the `mods` folder inside your PokeMMO installation directory.
5. Install the required Python dependencies by running: `pip install -r requirements.txt` in the command line.
  - If you already have Python installed or need another specific version, consider using a virtual environment, such as [pyenv](https://github.com/pyenv/pyenv) with [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv).

## Usage

1. Launch PokeMMO and position the game window appropriately (playing without maximizing the screen may cause issues with reading content from the window).
2. Run the `yapec.pyw` script with Python to start the YAPEC application.
3. YAPEC will continuously monitor the game window, capture screenshots at regular intervals, and process them to extract encounter data.
4. Encounter data will be stored in the SQLite database and displayed in the UI.
5. Use the UI to view and analyze the stored encounter data, or export it at different levels.

## Features

- **Automatic PokeMMO Launch**: Opens PokeMMO for you if it’s not already running, ensuring seamless integration.

- **Encounter Tracking**:
  - **Profile and Hunt Separation**: Organizes encounter data by profile and hunt, allowing you to track specific details based on your preferences.
  - **Total Encounters**: Displays the total number of encounters for each hunt.
  - **Customizable Pokémon Counts Display**: Choose how encounter counts are displayed:
    - **Latest Seen Pokémon**: Order Pokémon by the most recent encounter.
    - **Top Overall Pokémon**: Order Pokémon by the total number encountered.

- **Data Exporting**:
  - **Full Export**: Export all encounter data for comprehensive analysis.
  - **Profile-Specific Export**: Export encounter data specific to individual profiles.
  - **Hunt-Specific Export**: Export encounter data related to specific hunts.

- **Customization Options**:
  - **Select Counts Display**: Choose wheter to display counting by Latest Seen, Top Overall or **Both**
  - **Window Resizing**: Resize the window to show only total encounters, or display details for 1, 3 or 5 Pokémon, as desired.
  - **Show/Hide Alpha and Shiny Counts**: Toggle the visibility of alpha and shiny Pokémon counts in the UI.

- **Debugging Options**:
  - **Soft Log**: Log only main actions for a concise overview of the application’s activity.
  - **Full Log**: Log all actions for a comprehensive record of all application activities.
  - **Soft Debug**: Log main actions and images, excluding data-saving operations, to help diagnose issues.
  - **Full Debug**: Log all actions and images, excluding data-saving operations, for detailed debugging.

## Roadmap

- ~~Implement a user interface (UI) for better interaction and visualization of encounter data.~~
- ~~Improve code documentation and provide detailed instructions on using the application.~~
- Add additional features such as encounter statistics, filters~~, and export functionality~~.
- Add support for multiple languages and custom strings.
- Create a dashboard to display statistics and insights from the stored encounter data.
- Extend support to other operating systems to make the application more accessible.

**Note: I am not actively working on this project at the moment. The roadmap above outlines potential future directions but does not guarantee that these features will be implemented. Contributions from the community are welcome and encouraged to help achieve any or all of the goals mentioned.**

## Contributing

Contributions to YAPEC are welcome! If you have ideas, bug reports, or feature requests, please open an issue on the GitHub repository or contact me on the PokeMMO Forum [here](https://forums.pokemmo.com/index.php?/profile/472246-tinquinho/).

## Acknowledgements

- This project is inspired by the Pokémon and PokeMMO games, a desire to learn more about OCR and image processing techniques, and the available community tools for encounter counting.
- The OCR functionality is powered by the [pytesseract](https://github.com/madmaze/pytesseract) library, which utilizes the [Tesseract OCR engine](https://github.com/tesseract-ocr/tesseract).
- Image processing operations are implemented using the [OpenCV](https://opencv.org/) Python library.
- SQLite database interaction is facilitated by the [sqlite3](https://docs.python.org/3/library/sqlite3.html) module in Python's standard library.

**Note: This project is not affiliated with PokeMMO or the Pokémon franchise in any way.**
