# Camera Management Extension

A camera capture tool for NVIDIA Omniverse that enables simultaneous multi-camera image and video capture from your scenes using Replicator.

## Features

- **Multi-Camera Capture** - Manage multiple cameras from your USD scene for capturing
- **Dual Capture Modes** - Export as image sequences (PNG) or video files (MP4)
- **Configurable Settings** - Per-camera resolution (64-4096px) and frame rate (1-120 FPS)
- **Real-Time Preview** - Preview any camera directly in the viewport
- **Sample Scene Generator** - Create a demo scene with objects and cameras for testing
- **State Persistence** - Settings automatically save and restore between sessions
- **FPS Monitoring** - Warnings when capture FPS exceeds application performance

## Requirements

- NVIDIA Isaac Sim 2023.1.0 or later (or Omniverse Kit with Replicator)
- omni.replicator.core
- omni.kit.uiapp
- omni.usd
- omni.kit.window.filepicker
- omni.kit.viewport.utility

## Installation

### Option 1: Add Extension Path in Isaac Sim

1. Clone or download this repository
2. Open Isaac Sim
3. Go to **Window > Extensions**
4. Click the gear icon (Settings)
5. Under "Extension Search Paths", add the path to this repository folder
6. Search for "Camera Management" and enable it

### Option 2: Copy to Isaac Sim Extensions Folder

Copy this entire folder to your Isaac Sim extensions directory:
- Windows: `%LOCALAPPDATA%\ov\pkg\isaac-sim-<version>\exts\`
- Linux: `~/.local/share/ov/pkg/isaac-sim-<version>/exts/`

## Usage

1. Open the extension from: **Window > Camera Capture Tool**
2. Set an output folder for captured files
3. Click **Add Camera** and select cameras from your scene
4. Configure resolution, FPS, and capture mode for each camera
5. Use **Preview** to verify camera angles in the viewport
6. Click **Start Capture** to begin recording
7. Click **Stop Capture** when finished
8. UI states are automatically saved and restored between sessions

## Extension Structure

```
brian.camera_management/
├── config/
│   └── extension.toml    # Extension metadata and dependencies
├── brian/
│   └── camera_management/
│       ├── extension.py  # Extension entry point
│       ├── window.py     # Main UI window
│       ├── controllers/  # Business logic
│       └── widgets/      # UI components
├── data/                 # Icons and assets
└── docs/                 # Documentation
```

## License

See [LICENSE](LICENSE) file.
