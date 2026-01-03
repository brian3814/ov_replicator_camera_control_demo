# Camera Management Extension

A camera capture tool for NVIDIA Omniverse that enables simultaneous multi-camera image and video capture from your scenes using Replicator.


## Features

- **Multi-Camera Capture** - Manage multiple cameras from your USD scene for capturing
- **Dual Capture Modes** - Export as image sequences (PNG) or video files (MP4)
- **Configurable Settings** - Two output formats: per-camera resolution (64-4096px) and frame rate (1-120 FPS)
- **Real-Time Preview** - Preview any camera directly in the viewport
- **Sample Scene Generator** - Create a demo scene with objects and cameras for testing
- **State Persistence** - Settings automatically save and restore between sessions
- **FPS Monitoring** - Warnings when capture FPS exceeds application performance

## Usage

1. Open the extension from: **Windows** -> **Camera Capture Tool** from the top left menu bar
2. Set an output folder for captured files
3. Click **Add Camera** and select cameras from your scene
4. Configure resolution, FPS, and capture mode for each camera
5. Use **Preview** to verify camera angles in the viewport
6. Click **Start Capture** to begin recording
7. Click **Stop Capture** when finished
8. UI states are automatically updated and saved locally.
9. On next startup, previous states are restored from store state file.

## Requirements

- NVIDIA Omniverse Kit
- omni.kit.uiframework
- omni.usd
- omni.replicator.core
- omni.kit.window.filepicker
- omni.kit.viewport.utility
