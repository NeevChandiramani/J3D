# J3D - Five Nights at Chatelet

A 3D horror game inspired by Five Nights at Freddy's, built with Python and Ursina Engine.

## Quick Start - Download and Play

### Pre-built Executables (Recommended for Players)

Download the latest pre-release from the [Releases page](https://github.com/NeevChandiramani/J3D/releases) to play the game without setting up a development environment.

#### Windows
1. Download `J3D-Windows.exe` from the latest release
2. Double-click to run
3. If Windows SmartScreen appears, click "More info" then "Run anyway"

#### Linux
1. Download `J3D-Linux` from the latest release
2. Make it executable: `chmod +x J3D-Linux`
3. Run: `./J3D-Linux`

#### macOS
1. Download `J3D-macOS` from the latest release
2. Make it executable: `chmod +x J3D-macOS`
3. Run: `./J3D-macOS`
4. If macOS blocks it, go to System Preferences > Security & Privacy and allow it

### Game Controls
- **WASD**: Move
- **Shift**: Sprint (uses stamina)
- **Mouse**: Look around
- **ESC**: Exit game

## Development Setup

If you want to run from source or contribute to development:

### Prerequisites
- Python 3.11 or higher
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/NeevChandiramani/J3D.git
cd J3D
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the game:
```bash
python Five_Nights_At_Chatelet.py
```

## Building Executables

To build executables yourself:

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Build the executable:

**Windows:**
```bash
pyinstaller --onefile --windowed --name J3D --add-data "ressources;ressources" --add-data "models_compressed;models_compressed" Five_Nights_At_Chatelet.py
```

**Linux/macOS:**
```bash
pyinstaller --onefile --windowed --name J3D --add-data "ressources:ressources" --add-data "models_compressed:models_compressed" Five_Nights_At_Chatelet.py
```

The executable will be in the `dist/` folder.

## License

See [LICENSE](LICENSE) for details.