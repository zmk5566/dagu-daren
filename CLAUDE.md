# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

大鼓达人 (Da Gu Da Ren) is a web-based rhythm game inspired by "Taiko no Tatsujin" and the philosophical concept of authentic creation versus imitation from Han Byung-chul's "The Burnout Society". The goal is to automatically generate beatmaps from audio files using machine learning and provide professional-grade DAW-style annotation tools for manual refinement.

## High-level Code Architecture

The project's structure is organized as follows:

- `songs/`: Contains the original audio and video source files.
- `data/`: Holds data files for processing and gameplay.
  - `beatmap_format_guide.md`: Documentation for the JSON beatmap format.
  - `*/`: Subdirectories (e.g., `xwx-backtrack-n-drum/`) containing separated audio tracks (.wav files).
- `scripts/`: Contains utility scripts for automating tasks.
  - `create_backing_tracks.sh`: A script to automatically generate backing tracks and a clean drum track from separated .wav files.
  - `README.md`: Documentation for the scripts.

## Common Development Workflow

### 1. Adding a New Song

1.  **Obtain Source Audio**: Get the source audio/video for the new song and place it in the `songs/` directory.
2.  **Separate Audio Tracks**: Use an audio separation tool (e.g., Stemroller, Demucs) to split the source audio into individual tracks (bass, drums, vocals, other). Place these `.wav` files into a new subdirectory within `data/`, following the naming convention `<song-name> - <track-type>.wav`.
3.  **Generate Backing Tracks**: Run the provided script to automate the creation of necessary audio assets.
    ```bash
    bash scripts/create_backing_tracks.sh data/<new-song-directory>
    ```
    This will create a `generated_audio` folder containing the backing tracks and a clean `drums.mp3`.

### 2. Beatmap Generation (Next Major Task)

The next core task is to build a system that can:
- Analyze the generated `drums.mp3` file to detect hit timings and types (`don`/`ka`).
- Automatically generate a `.json` beatmap file based on this analysis.

### 3. DAW-Style Annotation Tool (Current Priority)

The next major development phase focuses on rebuilding the annotation interface as a professional DAW-style tool:
- **BPM Detection & Beat Grid**: Automatically detect BPM and display beat alignment grid
- **Auto-Alignment**: Snap existing annotations to detected beat positions
- **Professional Timeline**: DAW-style track layout with precise time navigation
- **Measure Detection**: Find the first measure's starting position based on drum patterns
- **Visual Beat Representation**: Clear visual indication of don/ka positions within measures

### 4. Frontend Development

Once the DAW-style annotation tool is complete, development will focus on:
- Building the game interface.
- Synchronizing audio with the scrolling beatmap.
- Implementing player input and the scoring/judgment system.

## Current Status

- ✅ **Classic ML Beatmap Generation**: Achieved 80% F1-Score using SVM with MFCC features
- ✅ **Manual Annotation Complete**: All don/ka hits manually annotated for training data
- ✅ **DAW-Style Annotation Tool**: Complete with BPM detection, beat grid, and auto-alignment
- 🚧 **BeatNet Smart Score Generation**: In development with significant issues
- ⏳ **Game Interface**: Pending completion of annotation tools

### 5. BeatNet Smart Score Generation (Current Development - Issues Present)

**Goal**: Implement intelligent score generation using BeatNet deep learning for automated don/ka mapping from audio.

**Implementation Status**:
- ✅ **BeatNet Integration**: Deep learning beat detection and downbeat identification working
- ✅ **3-Step Wizard UI**: Complete user interface for audio upload, beat mapping, and score preview
- ✅ **Backend API Endpoints**: `/api/beatnet-full-analysis`, `/api/process-beat-mapping`, `/api/finalize-beatnet-project`
- ✅ **Annotation-Style Conversion Pipeline**: New conversion method referencing existing successful annotation→score pipeline
- ✅ **Offset Handling**: BeatNet offset correctly saved in metadata (not applied to note times)
- ⚠️ **Format Compatibility**: DAW score format compatibility implemented but untested

**Current Issues & Limitations**:
- 🔴 **End-to-End Testing**: Full workflow from BeatNet analysis to DAW display not fully validated
- 🔴 **Score Display Issues**: Generated scores may not display correctly in DAW interface
- 🔴 **Format Conversion Problems**: Complex conversion between BeatNet format and DAW-compatible JSON
- 🔴 **Offset Integration**: While offset is saved in metadata, DAW may not properly use it for audio alignment
- 🔴 **User Experience**: Multi-step wizard may have UX issues and error handling problems
- 🔴 **Performance**: BeatNet analysis can be slow for longer audio files
- 🔴 **Beat Mapping Accuracy**: Smart suggestions may not always match user expectations

**Development Notes**:
- Implementation spans multiple files: `server.py` (APIs), `test_beatnet_api.html` (UI), `audio_processor/bpm_detector.py` (BeatNet)
- Uses 2-step conversion: BeatNet notes → annotations → score (mimicking existing successful pipeline)
- Fixed 0.1s note duration and preserved BeatNet's precise timing
- Temporary file storage for multi-step workflow

**Next Steps**:
- Comprehensive end-to-end testing
- DAW integration validation
- User experience improvements
- Error handling enhancement
