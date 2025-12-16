# Building and Releasing J3D Executables

This document explains how the automated build and release process works for J3D game executables.

## How It Works

The project uses GitHub Actions to automatically build executables for Windows, Linux, and macOS. The workflow is defined in `.github/workflows/build-release.yml`.

## Triggering a Release

There are two ways to trigger a build and release:

### Method 1: Manual Dispatch (Recommended for Pre-releases)

1. Go to the repository on GitHub
2. Click on "Actions" tab
3. Select "Build and Release Executables" workflow
4. Click "Run workflow"
5. Enter a version number (e.g., `v1.0.0-pre`, `v1.1.0-alpha`)
6. Click "Run workflow"

The workflow will:
- Build executables for Windows, Linux, and macOS
- Create a GitHub release with the specified version
- Mark it as a pre-release
- Attach all three executables to the release
- Add detailed instructions in the release notes

### Method 2: Git Tag Push

1. Create and push a git tag:
```bash
git tag v1.0.0-pre
git push origin v1.0.0-pre
```

This will automatically trigger the same build and release process.

## What Gets Built

The workflow creates three executables:

1. **J3D-Windows.exe** - Windows executable
2. **J3D-Linux** - Linux executable  
3. **J3D-macOS** - macOS executable

Each executable includes:
- The game code (`Five_Nights_At_Chatelet.py` and `Menu.py`)
- All dependencies (ursina, pygame, and their dependencies)
- Resource files (`ressources/` directory)
- Model files (`models_compressed/` directory)

## Build Process

For each platform, the workflow:

1. Sets up Python 3.11
2. Installs dependencies from `requirements.txt`
3. Installs PyInstaller
4. Runs PyInstaller with:
   - `--onefile` - Creates a single executable file
   - `--windowed` - No console window (GUI only)
   - `--add-data` - Includes resource and model directories
5. Renames the output to platform-specific names
6. Uploads as build artifacts

## Testing the Workflow

To test the workflow without creating a release:

1. Comment out the `release` job in the workflow file
2. Manually dispatch the workflow
3. Download the artifacts from the workflow run
4. Test each executable locally

## Troubleshooting

### Build Fails on a Specific Platform

- Check the workflow logs for that platform's job
- Common issues:
  - Missing dependencies: Update `requirements.txt`
  - Import errors: Add hidden imports to PyInstaller command
  - Resource files not found: Check paths in `--add-data`

### Executable Won't Run

- **Windows**: Check if antivirus is blocking it
- **macOS**: Check Gatekeeper settings in System Preferences > Security & Privacy
- **Linux**: Ensure the file has execute permissions (`chmod +x`)

### Missing Resources

- Verify resource files are in the correct directories
- Check PyInstaller data includes in the workflow
- Test with `--debug all` flag in PyInstaller for detailed logging

## Requirements

The build process requires:

- Python 3.11+
- ursina
- pygame
- PyInstaller

All dependencies are specified in `requirements.txt`.
