# 大鼓达人 DAW-Style Annotation Tool Implementation Plan

## Overview

Transform the current web-based annotation tool into a professional DAW-style interface with BPM detection, beat grid visualization, and auto-alignment capabilities. This tool will provide precise control over drum hit annotations while maintaining the philosophical principle of authentic creation over mere imitation.

## Phase 1: Backend BPM Detection & Beat Analysis

### 1.1 BPM Detection Engine
**Location**: `audio_processor/bpm_detector.py`

**Features to implement**:
- Use `librosa.beat.tempo` for initial BPM estimation
- Implement onset-based tempo tracking for accuracy refinement
- Add confidence scoring for BPM detection quality
- Support for complex time signatures (4/4, 3/4, 6/8)

**API Endpoints**:
```python
POST /api/detect_bpm
- Input: audio file path
- Output: { "bpm": 120.5, "confidence": 0.92, "beat_times": [...] }

POST /api/analyze_beats
- Input: audio file path, optional BPM override
- Output: { "beats": [...], "measures": [...], "first_measure_start": 2.34 }
```

### 1.2 Beat Grid Generation
**Location**: `audio_processor/beat_grid.py`

**Features**:
- Generate precise beat positions based on detected BPM
- Calculate measure boundaries and subdivisions
- Identify strong beats (downbeats) vs weak beats
- Handle tempo variations and rubato sections

### 1.3 First Measure Detection
**Location**: `audio_processor/measure_detector.py`

**Algorithm**:
1. Analyze drum onset patterns to find repetitive structures
2. Use spectral novelty to identify phrase boundaries
3. Cross-reference with beat grid to find measure alignment
4. Provide confidence scoring for first measure position

## Phase 2: Auto-Alignment Algorithm Development

### 2.1 Annotation Alignment Engine
**Location**: `annotation_tools/auto_aligner.py`

**Core Algorithm**:
```python
def auto_align_annotations(annotations, beat_grid, tolerance=0.1):
    """
    Snap existing annotations to nearest beat positions
    
    Args:
        annotations: List of {"time": float, "type": "don"/"ka"}
        beat_grid: List of precise beat timestamps
        tolerance: Maximum distance to snap (in seconds)
    
    Returns:
        aligned_annotations: List with corrected timestamps
        alignment_report: Statistics on adjustments made
    """
```

**Features**:
- Smart snapping that preserves musical intent
- Batch alignment with undo/redo capability
- Conflict resolution for overlapping annotations
- Preservation of user-intended off-beat placements

### 2.2 Beat Quantization Options
- Snap to quarter notes, eighth notes, sixteenth notes
- Triplet quantization support
- Custom grid divisions
- "Humanize" option to add slight timing variations

## Phase 3: DAW-Style Frontend Interface Design

### 3.1 Interface Layout Redesign
**Location**: `annotator/daw_interface.html`

**New Layout Structure**:
```
[Header: Transport Controls | BPM Display | Timeline Position]
[Main Timeline: Waveform + Beat Grid + Annotations]
[Track Panel: Don Track | Ka Track | Audio Track]
[Tool Panel: Select | Add | Delete | Align Tools]
[Properties Panel: Selection Info | Timing Details]
```

### 3.2 Professional DAW Features
- **Transport Controls**: Play, Pause, Stop, Loop, Record
- **Zoom Controls**: Horizontal/Vertical zoom with precision
- **Grid Snap**: Magnetic snap to beat positions
- **Selection Tools**: Rectangle select, range select
- **Keyboard Shortcuts**: Industry-standard DAW shortcuts

### 3.3 Color Scheme & UI
- **Dark Theme**: Professional DAW aesthetic
- **Color Coding**: Don (red), Ka (blue), Beat grid (gray)
- **High DPI Support**: Crisp rendering on all displays
- **Accessibility**: Keyboard navigation, screen reader support

## Phase 4: Beat Grid Visual Implementation

### 4.1 Timeline Rendering Engine
**Location**: `annotator/js/timeline_renderer.js`

**Features**:
- Canvas-based rendering for smooth performance
- Dynamic beat grid with subdivisions
- Measure numbers and beat counters
- Time ruler with multiple time formats (seconds, bars:beats)

### 4.2 Grid Visualization
- **Strong Beats**: Thick vertical lines at measure boundaries
- **Beat Subdivisions**: Thinner lines for quarter/eighth notes
- **Measure Numbers**: Clear numbering starting from first detected measure
- **Tempo Map**: Visual representation of tempo changes

### 4.3 Annotation Visualization
- **Note Blocks**: Precise rectangles showing don/ka positions
- **Timing Indicators**: Exact timestamp display on hover
- **Alignment Status**: Visual indicators for grid-aligned vs off-beat notes
- **Selection Feedback**: Clear indication of selected annotations

## Phase 5: Integration & Testing

### 5.1 Backend Integration
**New API Endpoints**:
```
GET /api/project/{id}/beat_analysis
POST /api/project/{id}/auto_align
POST /api/project/{id}/save_aligned_annotations
GET /api/project/{id}/timeline_data
```

### 5.2 Real-time Updates
- WebSocket connection for live collaboration
- Auto-save functionality with version history
- Undo/redo system with 50-step history
- Real-time BPM detection while audio plays

### 5.3 Testing Strategy
- **Unit Tests**: BPM detection accuracy on various music styles
- **Integration Tests**: Auto-alignment precision testing
- **User Testing**: DAW usability with experienced users
- **Performance Testing**: Large file handling (>10 minute tracks)

## Implementation Priorities

### Immediate (Week 1-2):
1. Basic BPM detection backend implementation
2. Simple beat grid generation
3. Auto-alignment prototype

### Short-term (Week 3-4):
1. DAW-style interface mockup
2. Timeline rendering engine
3. Basic grid visualization

### Medium-term (Week 5-8):
1. Complete DAW interface implementation
2. Advanced auto-alignment features
3. First measure detection refinement

### Long-term (Week 9-12):
1. Polish and optimization
2. Advanced DAW features (loop regions, markers)
3. Export/import compatibility with other DAW formats

## Technical Requirements

### Dependencies
- **Backend**: `librosa`, `numpy`, `scipy`, `flask`, `socketio`
- **Frontend**: `canvas`, `web-audio-api`, `wavesurfer.js` (enhanced)
- **Build Tools**: `webpack`, `babel`, `sass`

### Performance Targets
- BPM detection: <2 seconds for 5-minute tracks
- Auto-alignment: <1 second for 500 annotations
- Timeline rendering: 60fps smooth scrolling
- Memory usage: <500MB for 10-minute tracks

## Success Metrics

1. **BPM Detection Accuracy**: >95% within ±1 BPM for standard music
2. **Auto-Alignment Precision**: >90% of annotations align within 20ms tolerance
3. **User Productivity**: 50% reduction in annotation time vs current tool
4. **Interface Usability**: <30 seconds learning curve for DAW users

## File Structure Changes

```
大鼓达人/
├── audio_processor/
│   ├── bpm_detector.py (NEW)
│   ├── beat_grid.py (NEW)
│   ├── measure_detector.py (NEW)
│   └── server.py (UPDATED)
├── annotation_tools/ (NEW)
│   ├── auto_aligner.py
│   └── timeline_engine.py
├── annotator/
│   ├── daw_interface.html (NEW)
│   ├── js/
│   │   ├── timeline_renderer.js (NEW)
│   │   ├── daw_controls.js (NEW)
│   │   └── auto_aligner.js (NEW)
│   └── css/
│       └── daw_theme.css (NEW)
└── tests/ (NEW)
    ├── test_bpm_detection.py
    ├── test_auto_alignment.py
    └── test_daw_interface.js
```

This comprehensive plan transforms the annotation tool into a professional-grade DAW-style application while maintaining the philosophical authenticity that defines 大鼓达人.