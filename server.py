from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment
import os
import sys
import time
import json
import uuid
import shutil
import numpy as np
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

# Import our new DAW modules from audio_processor folder
try:
    from audio_processor.bpm_detector import BPMDetector
    from audio_processor.beat_grid import BeatGridGenerator
    from audio_processor.measure_detector import FirstMeasureDetector
    DAW_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] DAW modules not available: {e}")
    DAW_MODULES_AVAILABLE = False

# --- Define Absolute Paths ---
# This makes the server runnable from any directory
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = APP_ROOT  # Now server.py is in root directory
ANNOTATOR_DIR = os.path.join(PROJECT_ROOT, 'annotator')
VISUALIZER_DIR = os.path.join(PROJECT_ROOT, 'beatmap_visualizer')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Now import alignment tools after PROJECT_ROOT is defined
try:
    if 'annotation_tools.auto_aligner' not in globals():
        sys.path.append(os.path.join(PROJECT_ROOT, 'annotation_tools'))
        from auto_aligner import AutoAligner, QuantizeMode, SwingAmount
        ALIGNMENT_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Auto-alignment modules not available: {e}")
    ALIGNMENT_MODULES_AVAILABLE = False

app = Flask(__name__, static_folder='static', static_url_path=None)

# Add SVG MIME type support
import mimetypes
mimetypes.add_type('image/svg+xml', '.svg')

# Database setup
DB_PATH = os.path.join(PROJECT_ROOT, 'game_stats.db')

def init_database():
    """Initialize the SQLite database with game statistics table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create game_results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            song_name TEXT NOT NULL,
            final_score INTEGER NOT NULL,
            max_combo INTEGER NOT NULL,
            accuracy REAL NOT NULL,
            final_spirit REAL NOT NULL,
            perfect_hits INTEGER NOT NULL,
            good_hits INTEGER NOT NULL,
            miss_hits INTEGER NOT NULL,
            total_notes INTEGER NOT NULL,
            duration_seconds REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[Database] Initialized SQLite database at {DB_PATH}")

# Initialize database on startup
init_database()

@app.route('/static/<path:filename>')
def custom_static(filename):
    """Custom static file handler with proper SVG MIME type"""
    response = send_from_directory('static', filename)
    if filename.endswith('.svg'):
        response.headers['Content-Type'] = 'image/svg+xml'
        response.headers['Cache-Control'] = 'no-cache'
    return response

def convert_beatnet_to_annotations_then_score(beatnet_notes, project_data):
    """
    使用现有的annotation→score转换管线
    参考DAW界面的generateScoreFromAnnotations()函数
    
    Step 1: BeatNet notes → annotations (假设beat发生的事件，音符长度0.1秒)
    Step 2: annotations → score (使用相同的转换逻辑)
    """
    import time
    import random
    
    # Step 1: Convert BeatNet notes to annotation format
    annotations = []
    for note in beatnet_notes:
        annotation = {
            'id': f"beatnet-{note.get('originalBeatIndex', 0)}-{int(time.time()*1000)}",
            'time': note['time'],  # Keep BeatNet's precise timing
            'type': note['type'],  # don/ka
            'duration': 0.1  # 固定音符长度0.1秒，如你建议
        }
        annotations.append(annotation)
    
    print(f"[BeatNet→Annotation] Converted {len(beatnet_notes)} BeatNet notes to annotations")
    
    # Step 2: Convert annotations to score (参考DAW的generateScoreFromAnnotations逻辑)
    score = []
    for annotation in annotations:
        score_note = {
            'id': f"score-{int(time.time()*1000)}-{random.randint(100000, 999999)}",
            'time': annotation['time'],
            'type': annotation['type'],
            'duration': annotation['duration']
        }
        score.append(score_note)
    
    print(f"[Annotation→Score] Converted {len(annotations)} annotations to score using DAW pipeline")
    
    return score

# Configure upload settings
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_image_file(filename):
    """Check if file has allowed image extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# --- Frontend Routes ---

@app.route('/')
def serve_start_screen():
    """Serves the new game start screen."""
    return send_from_directory(PROJECT_ROOT, 'start_screen.html')

@app.route('/daw')
def serve_daw_interface():
    """Serves the new DAW-style annotation interface."""
    return send_from_directory(ANNOTATOR_DIR, 'daw_interface.html')

@app.route('/game')
def serve_game_interface():
    """Serves the rhythm game performance mode interface."""
    return send_from_directory(PROJECT_ROOT, 'game_interface.html')

@app.route('/test-beatnet')
def serve_beatnet_test():
    """Serves the BeatNet API test page."""
    return send_from_directory(PROJECT_ROOT, 'test_beatnet_api.html')

@app.route('/svg-test')
def serve_svg_test():
    """Serves the SVG test page for debugging SVG loading issues."""
    return send_from_directory(PROJECT_ROOT, 'svg_test.html')

@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404 errors."""
    return '', 204

@app.route('/visualizer/')
def serve_visualizer_index():
    """Serves the beatmap visualizer's main page."""
    return send_from_directory(VISUALIZER_DIR, 'index.html')

@app.route('/data/<path:filepath>')
def serve_data_files(filepath):
    """Serves files from the 'data' directory (e.g., audio files)."""
    return send_from_directory(DATA_DIR, filepath)

@app.route('/<path:filename>')
def serve_annotator_static(filename):
    # First try the annotator folder for JS, CSS assets
    annotator_path = os.path.join(ANNOTATOR_DIR, filename)
    if os.path.exists(annotator_path):
        return send_from_directory(ANNOTATOR_DIR, filename)
    
    # Fallback to root directory for files like SVGs
    root_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(root_path):
        return send_from_directory(PROJECT_ROOT, filename)
    
    # If not found in either location, return 404
    return "File not found", 404

@app.route('/visualizer/<path:filename>')
def serve_visualizer_static(filename):
    """Serves static files for the beatmap visualizer (JS, CSS)."""
    return send_from_directory(VISUALIZER_DIR, filename)

# --- DAW API Routes ---

@app.route('/api/metadata/<project_name>')
def get_project_metadata(project_name):
    """Get project metadata including BPM, beat grid, and other settings"""
    try:
        # Look for metadata.json in project directory
        metadata_path = os.path.join(DATA_DIR, project_name, 'metadata.json')
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return jsonify({
                "status": "success",
                "metadata": metadata
            })
        else:
            return jsonify({
                "status": "not_found",
                "message": "Metadata file not found. Auto-detection may be needed."
            }), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/detect_bpm', methods=['POST'])
def detect_bpm():
    """Detect BPM for audio file"""
    if not DAW_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "BPM detection modules not available"}), 500
    
    try:
        data = request.json
        project_name = data.get('projectName')
        audio_file = data.get('audioFile', 'drums.mp3')
        use_original = data.get('useOriginal', False)  # New option to use original track
        
        if not project_name:
            return jsonify({"status": "error", "message": "Project name required"}), 400
        
        # Determine audio file path based on user choice
        if use_original:
            # Use original track: look for project_name/project_name.mp3 in data directory
            original_audio_path = os.path.join(DATA_DIR, project_name, f'{project_name}.mp3')
            if os.path.exists(original_audio_path):
                audio_path = original_audio_path
                audio_source = "original_track"
            else:
                # Fallback to drums if original not found
                audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', audio_file)
                audio_source = "drums_fallback"
        else:
            # Use drums track
            audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', audio_file)
            audio_source = "drums_track"
        
        if not os.path.exists(audio_path):
            return jsonify({"status": "error", "message": f"Audio file not found: {audio_path}"}), 404
        
        # Detect BPM
        detector = BPMDetector()
        result = detector.detect_bpm(audio_path)
        
        # Add audio source info to result (no path for privacy)
        result['audio_source'] = audio_source
        
        # Create and save metadata.json
        metadata = {
            "project_name": project_name,
            "audio_file": audio_file,
            "bpm_data": result,
            "created_at": time.time(),
            "last_updated": time.time(),
            "version": "1.0"
        }
        
        metadata_path = os.path.join(DATA_DIR, project_name, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        return jsonify({
            "status": "success",
            "bpm_data": result,
            "metadata_saved": True
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/analyze_beats', methods=['POST'])
def analyze_beats():
    """Generate beat grid analysis"""
    if not DAW_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "Beat analysis modules not available"}), 500
    
    try:
        data = request.json
        project_name = data.get('projectName')
        audio_file = data.get('audioFile', 'drums.mp3')
        bpm_override = data.get('bpmOverride')  # Optional manual BPM
        
        if not project_name:
            return jsonify({"status": "error", "message": "Project name required"}), 400
        
        # Construct audio file path
        audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', audio_file)
        
        if not os.path.exists(audio_path):
            return jsonify({"status": "error", "message": f"Audio file not found: {audio_file}"}), 404
        
        # Generate beat grid
        generator = BeatGridGenerator()
        beat_grid = generator.generate_beat_grid(audio_path, bpm_override)
        
        # Detect first measure
        measure_detector = FirstMeasureDetector()
        first_measure = measure_detector.detect_first_measure(audio_path, bpm_override)
        
        return jsonify({
            "status": "success",
            "beat_grid": beat_grid,
            "first_measure": first_measure
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/timeline_data')
def get_timeline_data(project_name):
    """Get complete timeline data for DAW interface"""
    if not DAW_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "Timeline analysis modules not available"}), 500
    
    try:
        # Get audio file path
        audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', 'drums.mp3')
        
        if not os.path.exists(audio_path):
            return jsonify({"status": "error", "message": "Audio file not found"}), 404
        
        # Load existing annotations
        annotations_path = os.path.join(DATA_DIR, project_name, 'annotation', 'annotations.json')
        annotations = []
        if os.path.exists(annotations_path):
            with open(annotations_path, 'r') as f:
                annotations = json.load(f)
        
        # Generate complete analysis
        detector = BPMDetector()
        generator = BeatGridGenerator()
        measure_detector = FirstMeasureDetector()
        
        bpm_result = detector.detect_bpm(audio_path)
        beat_grid = generator.generate_beat_grid(audio_path)
        first_measure = measure_detector.detect_first_measure(audio_path)
        
        return jsonify({
            "status": "success",
            "timeline_data": {
                "project_name": project_name,
                "audio_file": "drums.mp3",
                "annotations": annotations,
                "bpm_analysis": bpm_result,
                "beat_grid": beat_grid,
                "first_measure": first_measure,
                "generated_at": time.time()
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auto_align', methods=['POST'])
def auto_align_annotations():
    """Auto-align annotations with various quantization options"""
    if not DAW_MODULES_AVAILABLE or not ALIGNMENT_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "Auto-alignment modules not available"}), 500
    
    try:
        data = request.json
        project_name = data.get('projectName')
        quantize_mode = data.get('quantizeMode', '1/16')  # Default to 16th notes
        swing_amount = data.get('swingAmount', 'medium')  # light, medium, heavy, custom
        custom_swing = data.get('customSwing', 0.60)     # Custom swing ratio
        tolerance = data.get('tolerance', 0.25)          # Tolerance as fraction of beat
        preserve_off_beat = data.get('preserveOffBeat', True)
        annotations_override = data.get('annotations')   # Optional: provide annotations directly
        audio_offset = data.get('audioOffset', 0.0)      # Audio offset from frontend
        score_offset = data.get('scoreOffset', 0.0)      # Score offset from frontend
        
        if not project_name:
            return jsonify({"status": "error", "message": "Project name required"}), 400
        
        # Get current annotations
        if annotations_override:
            annotations = annotations_override
        else:
            annotations_path = os.path.join(DATA_DIR, project_name, 'annotation', 'annotations.json')
            if not os.path.exists(annotations_path):
                return jsonify({"status": "error", "message": "No annotations found for project"}), 404
            
            with open(annotations_path, 'r') as f:
                annotations = json.load(f)
        
        # Get beat grid and first measure data
        audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', 'drums.mp3')
        if not os.path.exists(audio_path):
            return jsonify({"status": "error", "message": "Audio file not found"}), 404
        
        # Generate beat analysis
        generator = BeatGridGenerator()
        measure_detector = FirstMeasureDetector()
        
        beat_grid = generator.generate_beat_grid(audio_path)
        first_measure = measure_detector.detect_first_measure(audio_path)
        
        # Map string parameters to enums
        mode_map = {
            "1/4": QuantizeMode.QUARTER,
            "1/8": QuantizeMode.EIGHTH,
            "1/16": QuantizeMode.SIXTEENTH,
            "1/4+swing": QuantizeMode.QUARTER_SWING,
            "1/8+swing": QuantizeMode.EIGHTH_SWING,
            "1/16+swing": QuantizeMode.SIXTEENTH_SWING,
            "1/4T": QuantizeMode.TRIPLET_QUARTER,
            "1/8T": QuantizeMode.TRIPLET_EIGHTH,
            "off": QuantizeMode.OFF_GRID
        }
        
        swing_map = {
            "light": SwingAmount.LIGHT,
            "medium": SwingAmount.MEDIUM,
            "heavy": SwingAmount.HEAVY,
            "custom": SwingAmount.CUSTOM
        }
        
        quantize_enum = mode_map.get(quantize_mode, QuantizeMode.SIXTEENTH)
        swing_enum = swing_map.get(swing_amount, SwingAmount.MEDIUM)
        
        # Perform auto-alignment
        aligner = AutoAligner()
        
        # Combine first_measure_start with audio_offset for proper alignment
        # The audio_offset shifts the visual beat grid, so we need to account for it
        effective_first_measure_start = first_measure['first_measure_start'] + audio_offset
        
        print(f"[AutoAlign API] Audio offset: {audio_offset:.3f}s, Score offset: {score_offset:.3f}s")
        print(f"[AutoAlign API] Original first_measure_start: {first_measure['first_measure_start']:.3f}s")
        print(f"[AutoAlign API] Effective first_measure_start: {effective_first_measure_start:.3f}s")
        
        alignment_result = aligner.auto_align_annotations(
            annotations=annotations,
            beat_grid=beat_grid,
            quantize_mode=quantize_enum,
            swing_amount=swing_enum,
            custom_swing=custom_swing,
            tolerance=tolerance,
            preserve_off_beat=preserve_off_beat,
            first_measure_start=effective_first_measure_start
        )
        
        return jsonify({
            "status": "success",
            "alignment_result": alignment_result,
            "original_count": len(annotations),
            "aligned_count": len(alignment_result['aligned_annotations'])
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/save_aligned_annotations', methods=['POST'])
def save_aligned_annotations(project_name):
    """Save aligned annotations back to project"""
    try:
        data = request.json
        aligned_annotations = data.get('alignedAnnotations', [])
        backup_original = data.get('backupOriginal', True)
        
        # Paths
        annotations_dir = os.path.join(DATA_DIR, project_name, 'annotation')
        annotations_path = os.path.join(annotations_dir, 'annotations.json')
        
        # Backup original if requested
        if backup_original and os.path.exists(annotations_path):
            backup_path = os.path.join(annotations_dir, f'annotations_backup_{int(time.time())}.json')
            import shutil
            shutil.copy2(annotations_path, backup_path)
            print(f"[SaveAlign] Backed up original annotations to: {backup_path}")
        
        # Save aligned annotations
        os.makedirs(annotations_dir, exist_ok=True)
        with open(annotations_path, 'w') as f:
            json.dump(aligned_annotations, f, indent=4)
        
        return jsonify({
            "status": "success",
            "message": f"Saved {len(aligned_annotations)} aligned annotations",
            "backup_created": backup_original
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/quantization_options')
def get_quantization_options():
    """Get available quantization modes and swing options"""
    return jsonify({
        "status": "success",
        "quantization_modes": [
            {"value": "1/4", "label": "Quarter Notes", "description": "Align to beat positions"},
            {"value": "1/8", "label": "Eighth Notes", "description": "Align to beat and off-beat positions"},
            {"value": "1/16", "label": "Sixteenth Notes", "description": "Align to fine subdivisions"},
            {"value": "1/4+swing", "label": "Quarter Notes + Swing", "description": "Quarter notes with swing feel"},
            {"value": "1/8+swing", "label": "Eighth Notes + Swing", "description": "Eighth notes with swing feel"},
            {"value": "1/16+swing", "label": "Sixteenth Notes + Swing", "description": "Sixteenth notes with swing feel"},
            {"value": "1/4T", "label": "Quarter Triplets", "description": "Quarter note triplets"},
            {"value": "1/8T", "label": "Eighth Triplets", "description": "Eighth note triplets"},
            {"value": "off", "label": "Off Grid", "description": "No quantization"}
        ],
        "swing_amounts": [
            {"value": "light", "label": "Light Swing", "ratio": 0.55},
            {"value": "medium", "label": "Medium Swing", "ratio": 0.60},
            {"value": "heavy", "label": "Heavy Swing", "ratio": 0.67},
            {"value": "custom", "label": "Custom", "ratio": "user_defined"}
        ]
    })

# --- BeatNet Smart Score Generation API Routes ---

@app.route('/api/beatnet-full-analysis', methods=['POST'])
def beatnet_full_analysis():
    """Complete BeatNet analysis for smart score generation"""
    if not DAW_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "BeatNet analysis modules not available"}), 500
    
    try:
        # Handle file upload
        if 'audioFile' not in request.files:
            return jsonify({"status": "error", "message": "No audio file provided"}), 400
        
        audio_file = request.files['audioFile']
        project_name = request.form.get('projectName')
        display_name = request.form.get('displayName')
        
        if not project_name or not display_name:
            return jsonify({"status": "error", "message": "Project name and display name are required"}), 400
        
        if audio_file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        # Generate unique project ID for temporary processing
        project_id = str(uuid.uuid4())
        
        # Create temporary directory
        temp_dir = os.path.join('temp', project_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save uploaded audio file
        audio_path = os.path.join(temp_dir, 'audio.mp3')
        audio_file.save(audio_path)
        
        # Get audio info
        import librosa
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        
        # Perform BeatNet analysis
        detector = BPMDetector()
        bpm_result = detector.detect_bpm(audio_path)
        
        # Check if BeatNet analysis was successful
        if 'beat_data' not in bpm_result or not bpm_result['beat_data']:
            return jsonify({"status": "error", "message": "BeatNet failed to detect beats"}), 500
        
        # Extract beat information from BeatNet result
        beat_data = bpm_result['beat_data']
        beats_analysis = []
        downbeat_count = 0
        
        for i, beat_info in enumerate(beat_data):
            beat_type = beat_info['type']  # Already 'downbeat' or 'beat'
            if beat_type == "downbeat":
                downbeat_count += 1
            
            # Calculate measure position (assuming 4/4 time)
            measure_number = (i // 4) + 1
            beat_in_measure = (i % 4) + 1
            
            # Calculate strength based on beat type and position
            # Downbeats get higher strength, off-beats get lower strength
            if beat_type == 'downbeat':
                strength = np.random.uniform(0.85, 0.95)  # Strong downbeats
            else:
                strength = np.random.uniform(0.60, 0.85)  # Weaker regular beats
            
            beats_analysis.append({
                'index': i,
                'time': beat_info['time'],
                'type': beat_type,
                'strength': float(strength),
                'measureNumber': measure_number,
                'beatInMeasure': beat_in_measure,
                'confidence': 0.9  # BeatNet is generally highly confident
            })
        
        # Generate smart suggestions based on beat analysis
        smart_suggestions = []
        suggestion_stats = {'don': 0, 'ka': 0, 'skip': 0}
        
        for beat in beats_analysis:
            if beat['type'] == 'downbeat':
                # Downbeats -> Don
                suggestion = 'don'
                confidence = 0.85
                reason = 'downbeat_high_priority'
                suggestion_stats['don'] += 1
            elif beat['strength'] > 0.75:
                # High strength beats -> Ka
                suggestion = 'ka' 
                confidence = 0.70
                reason = 'beat_high_strength'
                suggestion_stats['ka'] += 1
            elif beat['strength'] > 0.60:
                # Medium strength beats -> Ka
                suggestion = 'ka'
                confidence = 0.55
                reason = 'beat_medium_strength'  
                suggestion_stats['ka'] += 1
            else:
                # Low strength beats -> Skip
                suggestion = 'skip'
                confidence = 0.40
                reason = 'beat_low_strength'
                suggestion_stats['skip'] += 1
            
            smart_suggestions.append({
                'beatIndex': beat['index'],
                'suggestion': suggestion,
                'confidence': confidence,
                'reason': reason
            })
        
        # Store project data temporarily (using file storage for persistence)
        temp_project_data = {
            'projectId': project_id,
            'projectName': project_name,
            'displayName': display_name,
            'audioPath': audio_path,
            'audioInfo': {
                'duration': duration,
                'sampleRate': int(sr)
            },
            'createdAt': time.time(),
            'bpmData': bpm_result,
            'beatsAnalysis': beats_analysis
        }
        
        # Save to temporary JSON file
        temp_data_file = os.path.join(temp_dir, 'project_data.json')
        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(temp_project_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "status": "success",
            "data": {
                "projectId": project_id,
                "audioInfo": {
                    "duration": duration,
                    "sampleRate": int(sr),
                    "audioPath": f"/temp/{project_id}/audio.mp3"
                },
                "bpmData": bpm_result,  # Keep existing naming for compatibility
                "beatAnalysis": {
                    "beats": beats_analysis,
                    "totalBeats": len(beats_analysis),
                    "downbeatCount": downbeat_count,
                    "totalMeasures": max(1, downbeat_count)
                },
                "smartSuggestions": smart_suggestions,
                "suggestionStats": suggestion_stats
            }
        })
        
    except Exception as e:
        # Clean up temporary files on error
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/process-beat-mapping', methods=['POST'])
def process_beat_mapping():
    """Process user's beat-to-note mappings and generate score"""
    try:
        data = request.json
        project_id = data.get('projectId')
        mappings = data.get('mappings', [])
        settings = data.get('settings', {})
        
        if not project_id:
            return jsonify({"status": "error", "message": "Project ID required"}), 400
        
        # Get project data from temporary file storage
        temp_dir = os.path.join('temp', project_id)
        temp_data_file = os.path.join(temp_dir, 'project_data.json')
        
        if not os.path.exists(temp_data_file):
            return jsonify({"status": "error", "message": "Project not found or expired"}), 404
        
        with open(temp_data_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        beats_data = project_data['beatsAnalysis']
        
        # Create mapping dictionary for easy lookup
        mapping_dict = {m['beatIndex']: m['userChoice'] for m in mappings}
        
        # Generate score from mappings
        generated_score = []
        score_stats = {'totalNotes': 0, 'donCount': 0, 'kaCount': 0}
        
        for beat in beats_data:
            beat_index = beat['index']
            user_choice = mapping_dict.get(beat_index, 'skip')
            
            if user_choice in ['don', 'ka']:
                score_item = {
                    'id': f"score_{beat_index:03d}",
                    'time': beat['time'],  # Use BeatNet's precise timing
                    'type': user_choice,
                    'originalBeatIndex': beat_index,
                    'beatType': beat['type'],
                    'strength': beat['strength'],
                    'measurePosition': beat['measureNumber']
                }
                generated_score.append(score_item)
                score_stats['totalNotes'] += 1
                
                if user_choice == 'don':
                    score_stats['donCount'] += 1
                else:
                    score_stats['kaCount'] += 1
        
        # Calculate quality metrics
        total_beats = len(beats_data)
        downbeats_used = sum(1 for beat in beats_data 
                           if beat['type'] == 'downbeat' and mapping_dict.get(beat['index']) == 'don')
        total_downbeats = sum(1 for beat in beats_data if beat['type'] == 'downbeat')
        
        quality_metrics = {
            'rhythmComplexity': score_stats['totalNotes'] / total_beats if total_beats > 0 else 0,
            'beatCoverage': score_stats['totalNotes'] / total_beats if total_beats > 0 else 0,
            'downbeatAlignment': downbeats_used / total_downbeats if total_downbeats > 0 else 1.0
        }
        
        # Calculate additional stats
        avg_strength = sum(beat['strength'] for beat in beats_data 
                         if mapping_dict.get(beat['index']) in ['don', 'ka']) / score_stats['totalNotes'] if score_stats['totalNotes'] > 0 else 0
        
        score_stats.update({
            'averageNoteStrength': avg_strength,
            'strongBeatUtilization': downbeats_used / total_downbeats if total_downbeats > 0 else 0,
            'regularBeatUtilization': (score_stats['totalNotes'] - downbeats_used) / (total_beats - total_downbeats) if (total_beats - total_downbeats) > 0 else 0
        })
        
        # Update project data with generated score
        project_data['generatedScore'] = generated_score
        project_data['scoreStats'] = score_stats
        project_data['qualityMetrics'] = quality_metrics
        
        # Save updated project data back to file
        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "status": "success",
            "data": {
                "generatedScore": generated_score,
                "scoreStats": score_stats,
                "qualityMetrics": quality_metrics
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/finalize-beatnet-project', methods=['POST'])
def finalize_beatnet_project():
    """Finalize BeatNet project and save to permanent storage"""
    try:
        data = request.json
        project_id = data.get('projectId')
        final_score = data.get('finalScore', [])
        user_metadata = data.get('metadata', {})
        
        if not project_id:
            return jsonify({"status": "error", "message": "Project ID required"}), 400
        
        # Get project data from temporary file storage
        temp_dir = os.path.join('temp', project_id)
        temp_data_file = os.path.join(temp_dir, 'project_data.json')
        
        if not os.path.exists(temp_data_file):
            return jsonify({"status": "error", "message": "Project not found or expired"}), 404
        
        with open(temp_data_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        project_name = project_data['projectName']
        
        # Always use generated score from beat mapping if available, regardless of finalScore
        if 'generatedScore' in project_data:
            generated_score = project_data['generatedScore']
            
            # Use new annotation-style conversion pipeline (参考现有成功管线)
            final_score = convert_beatnet_to_annotations_then_score(generated_score, project_data)
            print(f"[Project] Converted {len(final_score)} BeatNet notes using annotation pipeline")
        elif not final_score:
            print("[Project] Warning: No score data available - project will have empty score")
        
        # Create final project directory
        final_dir = os.path.join(DATA_DIR, project_name)
        os.makedirs(final_dir, exist_ok=True)
        
        # Create complete directory structure for DAW compatibility
        generated_audio_dir = os.path.join(final_dir, 'generated_audio')
        annotation_dir = os.path.join(final_dir, 'annotation')
        os.makedirs(generated_audio_dir, exist_ok=True)
        os.makedirs(annotation_dir, exist_ok=True)
        
        # Move audio file from temp to final location
        temp_audio_path = project_data['audioPath']
        final_audio_path = os.path.join(final_dir, f"{project_name}.mp3")  # Original audio
        drums_audio_path = os.path.join(generated_audio_dir, 'drums.mp3')  # For DAW compatibility
        
        # Copy to both locations
        shutil.copy2(temp_audio_path, final_audio_path)  # Keep original
        shutil.move(temp_audio_path, drums_audio_path)   # Move to drums location for DAW
        
        # Save score data (使用与现有项目一致的格式)
        score_dir = os.path.join(final_dir, 'score')
        os.makedirs(score_dir, exist_ok=True)
        
        # Extract offset from BeatNet data for DAW compatibility  
        score_offset = 0.0
        if 'bpmData' in project_data and 'offset' in project_data['bpmData']:
            score_offset = project_data['bpmData']['offset']
        
        # 使用与现有DAW项目一致的score格式
        score_data = {
            'metadata': {
                'scoreOffset': score_offset,  # BeatNet offset for audio alignment
                'createdAt': int(time.time() * 1000),  # 使用毫秒时间戳，与现有项目一致
                'version': '2.0',  # 与现有项目版本一致
                'creationMethod': 'beatnet_smart_generation',
                'beatnetVersion': 'DBN_v1.0',
                **user_metadata
            },
            'notes': final_score
        }
        
        score_file = os.path.join(score_dir, 'score.json')
        with open(score_file, 'w', encoding='utf-8') as f:
            json.dump(score_data, f, indent=2, ensure_ascii=False)
        
        # Save project metadata (for compatibility with existing DAW)
        metadata = {
            'project_name': project_name,
            'display_name': project_data['displayName'],
            'audio_file': f"{project_name}.mp3",
            'creation_method': 'beatnet_smart_generation',
            'bpm_data': project_data['bpmData'],  # Keep existing naming
            'created_at': project_data['createdAt'],
            'finalized_at': time.time()
        }
        
        metadata_file = os.path.join(final_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Create empty annotations file for DAW compatibility
        annotations_file = os.path.join(annotation_dir, 'annotations.json')
        with open(annotations_file, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        
        # Clean up temporary data
        temp_dir = os.path.dirname(project_data['audioPath'])
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return jsonify({
            "status": "success",
            "data": {
                "savedProjectName": project_name,
                "projectPath": final_dir,
                "scoreFile": score_file,
                "metadataFile": metadata_file,
                "redirectUrl": f"/daw?project={project_name}"
            }
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Serve temporary files during BeatNet analysis
@app.route('/temp/<project_id>/<filename>')
def serve_temp_files(project_id, filename):
    """Serve temporary files during BeatNet analysis"""
    try:
        temp_dir = os.path.join('temp', project_id)
        if not os.path.exists(temp_dir):
            return "File not found", 404
        return send_from_directory(temp_dir, filename)
    except Exception:
        return "File not found", 404

# --- API Routes ---

@app.route('/api/projects')
def list_projects():
    """Scans the 'data/' directory for subfolders and returns them with display names."""
    try:
        if not os.path.isdir(DATA_DIR):
            return jsonify({"status": "error", "message": "'data' 目录未找到。"}), 404
        
        project_folders = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
        projects = []
        
        for folder_name in project_folders:
            project_info = {
                "folder_name": folder_name,
                "display_name": folder_name  # Default to folder name
            }
            
            # Try to read display_name from metadata.json
            metadata_path = os.path.join(DATA_DIR, folder_name, 'metadata.json')
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        if 'display_name' in metadata:
                            project_info["display_name"] = metadata['display_name']
                except Exception as e:
                    # If metadata.json is invalid, just use folder name
                    print(f"[Warning] Could not read metadata for {folder_name}: {e}")
            
            projects.append(project_info)
        
        # Sort by display_name for better user experience
        projects.sort(key=lambda x: x['display_name'])
        
        return jsonify({"status": "success", "projects": projects})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/display_name', methods=['POST'])
def update_project_display_name(project_name):
    """Update the display name for a project in its metadata.json"""
    try:
        data = request.json
        display_name = data.get('display_name', '').strip()
        
        if not display_name:
            return jsonify({"status": "error", "message": "Display name cannot be empty"}), 400
        
        # Check if project exists
        project_dir = os.path.join(DATA_DIR, project_name)
        if not os.path.isdir(project_dir):
            return jsonify({"status": "error", "message": "Project not found"}), 404
        
        # Read existing metadata or create new one
        metadata_path = os.path.join(project_dir, 'metadata.json')
        metadata = {}
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"[Warning] Could not read existing metadata for {project_name}: {e}")
                metadata = {}
        
        # Update display_name and timestamp
        metadata['display_name'] = display_name
        metadata['last_updated'] = time.time()
        
        # Ensure project_name is set
        if 'project_name' not in metadata:
            metadata['project_name'] = project_name
        
        # Save updated metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            "status": "success", 
            "message": f"Display name updated to '{display_name}'",
            "display_name": display_name
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/images/upload', methods=['POST'])
def upload_project_image(project_name):
    """Upload an image for a project"""
    try:
        # Check if project exists
        project_dir = os.path.join(DATA_DIR, project_name)
        if not os.path.isdir(project_dir):
            return jsonify({"status": "error", "message": "Project not found"}), 404
        
        # Get form data
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "No image file provided"}), 400
        
        file = request.files['image']
        category = request.form.get('category')
        image_type = request.form.get('type')
        
        if not category or not image_type:
            return jsonify({"status": "error", "message": "Category and type are required"}), 400
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400
        
        if not allowed_image_file(file.filename):
            return jsonify({"status": "error", "message": "File type not allowed. Use PNG, JPG, JPEG, or GIF"}), 400
        
        # Create images directory if it doesn't exist
        images_dir = os.path.join(project_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{category}_{image_type}_{uuid.uuid4().hex[:8]}.{file_extension}"
        filepath = os.path.join(images_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        # Update metadata.json
        metadata_path = os.path.join(project_dir, 'metadata.json')
        metadata = {}
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"[Warning] Could not read metadata for {project_name}: {e}")
                metadata = {}
        
        # Initialize images section if it doesn't exist
        if 'images' not in metadata:
            metadata['images'] = {}
        if category not in metadata['images']:
            metadata['images'][category] = {}
        
        # Remove old image if it exists
        if image_type in metadata['images'][category]:
            old_image_path = os.path.join(images_dir, metadata['images'][category][image_type])
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        
        # Update metadata with new image
        metadata['images'][category][image_type] = filename
        metadata['last_updated'] = time.time()
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            "status": "success",
            "message": "Image uploaded successfully",
            "filename": filename,
            "category": category,
            "type": image_type
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/images')
def get_project_images(project_name):
    """Get all images for a project"""
    try:
        # Check if project exists
        project_dir = os.path.join(DATA_DIR, project_name)
        if not os.path.isdir(project_dir):
            return jsonify({"status": "error", "message": "Project not found"}), 404
        
        # Read metadata
        metadata_path = os.path.join(project_dir, 'metadata.json')
        images = {}
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    images = metadata.get('images', {})
            except Exception as e:
                print(f"[Warning] Could not read metadata for {project_name}: {e}")
        
        return jsonify({
            "status": "success",
            "images": images
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/images/<category>/<image_type>', methods=['DELETE'])
def delete_project_image(project_name, category, image_type):
    """Delete an image for a project"""
    try:
        # Check if project exists
        project_dir = os.path.join(DATA_DIR, project_name)
        if not os.path.isdir(project_dir):
            return jsonify({"status": "error", "message": "Project not found"}), 404
        
        # Read metadata
        metadata_path = os.path.join(project_dir, 'metadata.json')
        if not os.path.exists(metadata_path):
            return jsonify({"status": "error", "message": "No images found for this project"}), 404
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            return jsonify({"status": "error", "message": "Could not read project metadata"}), 500
        
        # Check if image exists in metadata
        if 'images' not in metadata or category not in metadata['images'] or image_type not in metadata['images'][category]:
            return jsonify({"status": "error", "message": "Image not found"}), 404
        
        # Get filename and delete file
        filename = metadata['images'][category][image_type]
        image_path = os.path.join(project_dir, 'images', filename)
        
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Remove from metadata
        del metadata['images'][category][image_type]
        
        # Clean up empty categories
        if not metadata['images'][category]:
            del metadata['images'][category]
        if not metadata['images']:
            del metadata['images']
        
        metadata['last_updated'] = time.time()
        
        # Save metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            "status": "success",
            "message": "Image deleted successfully"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/project/<project_name>/images/<filename>')
def serve_project_image(project_name, filename):
    """Serve project image files"""
    try:
        project_dir = os.path.join(DATA_DIR, project_name)
        images_dir = os.path.join(project_dir, 'images')
        
        if not os.path.isdir(images_dir):
            return "Image not found", 404
        
        # Security check - ensure filename is safe
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return "Invalid filename", 400
        
        return send_from_directory(images_dir, filename)
        
    except Exception as e:
        return "Image not found", 404

@app.route('/api/score/<project_name>', methods=['GET', 'POST'])
def handle_score(project_name):
    """Handles both loading (GET) and saving (POST) of score data."""
    if request.method == 'POST':
        # --- SAVE score ---
        try:
            score_data = request.json.get('score', [])
            score_dir = os.path.join(DATA_DIR, project_name, 'score')
            os.makedirs(score_dir, exist_ok=True)
            file_path = os.path.join(score_dir, 'score.json')
            
            with open(file_path, 'w') as f:
                json.dump(score_data, f, indent=4)
            
            # Get note count from the score data
            if isinstance(score_data, dict) and 'notes' in score_data:
                note_count = len(score_data['notes'])
                score_offset = score_data.get('metadata', {}).get('scoreOffset', 0)
                offset_msg = f", score offset: {score_offset:.3f}s" if score_offset != 0 else ""
                message = f"已保存 {note_count} 个曲谱音符{offset_msg}。"
            else:
                note_count = len(score_data) if isinstance(score_data, list) else 0
                message = f"已保存 {note_count} 个曲谱音符。"
                
            return jsonify({"status": "success", "message": message})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # --- LOAD score (GET) ---
        try:
            file_path = os.path.join(DATA_DIR, project_name, 'score', 'score.json')
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    score_data = json.load(f)
                return jsonify({"status": "success", "score": score_data})
            else:
                return jsonify({"status": "success", "score": []})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/annotations/<project_name>', methods=['GET', 'POST'])
def handle_annotations(project_name):
    """Handles both loading (GET) and saving (POST) of annotations."""
    if request.method == 'POST':
        # --- SAVE annotations ---
        try:
            annotations_data = request.json.get('annotations', [])
            annotation_dir = os.path.join(DATA_DIR, project_name, 'annotation')
            os.makedirs(annotation_dir, exist_ok=True)
            file_path = os.path.join(annotation_dir, 'annotations.json')
            
            with open(file_path, 'w') as f:
                json.dump(annotations_data, f, indent=4)
                
            return jsonify({"status": "success", "message": f"已保存 {len(annotations_data)} 个标注。"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # --- LOAD annotations (GET) ---
        try:
            file_path = os.path.join(DATA_DIR, project_name, 'annotation', 'annotations.json')
            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    annotations_data = json.load(f)
                return jsonify({"status": "success", "annotations": annotations_data})
            else:
                return jsonify({"status": "success", "annotations": []})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/process', methods=['POST'])
def process_audio():
    try:
        data = request.json
        project_name = data.get('projectName')
        audio_file_name = data.get('audioFile')
        annotations = data.get('annotations', [])

        if not project_name or not audio_file_name or not annotations:
            return jsonify({"status": "error", "message": "缺少必需的数据。"}), 400

        # Construct absolute paths from the project name
        project_audio_dir = os.path.join(DATA_DIR, project_name, 'generated_audio')
        source_audio_path = os.path.join(project_audio_dir, audio_file_name)

        if not os.path.isfile(source_audio_path):
            return jsonify({"status": "error", "message": f"音频文件未找到于: {source_audio_path}"}), 404

        audio = AudioSegment.from_file(source_audio_path)

        don_dir = os.path.join(project_audio_dir, "don_samples")
        ka_dir = os.path.join(project_audio_dir, "ka_samples")
        os.makedirs(don_dir, exist_ok=True)
        os.makedirs(ka_dir, exist_ok=True)

        don_count = 0
        ka_count = 0

        for ann in annotations:
            start_ms = int(ann['time'] * 1000)
            end_ms = int((ann['time'] + ann['duration']) * 1000)
            clip = audio[start_ms:end_ms]
            timestamp_ms = int(time.time() * 1000)
            filename = f"{ann['type']}_{start_ms}_{timestamp_ms}.wav"

            if ann['type'] == 'don':
                output_path = os.path.join(don_dir, filename)
                don_count += 1
            elif ann['type'] == 'ka':
                output_path = os.path.join(ka_dir, filename)
                ka_count += 1
            else:
                continue

            clip.export(output_path, format="wav")

        return jsonify({
            "status": "success",
            "message": f"成功剪辑 {don_count} 个 'don' 和 {ka_count} 个 'ka' 采样。",
            "don_path": don_dir,
            "ka_path": ka_dir
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/save-game-result', methods=['POST'])
def save_game_result():
    """Save game result to database"""
    try:
        data = request.json
        
        # Extract game result data
        song_name = data.get('song_name', 'Unknown')
        final_score = data.get('final_score', 0)
        max_combo = data.get('max_combo', 0)
        accuracy = data.get('accuracy', 0.0)
        final_spirit = data.get('final_spirit', 0.0)
        perfect_hits = data.get('perfect_hits', 0)
        good_hits = data.get('good_hits', 0)
        miss_hits = data.get('miss_hits', 0)
        total_notes = data.get('total_notes', 0)
        duration_seconds = data.get('duration_seconds', 0.0)
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO game_results (
                song_name, final_score, max_combo, accuracy, final_spirit,
                perfect_hits, good_hits, miss_hits, total_notes, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            song_name, final_score, max_combo, accuracy, final_spirit,
            perfect_hits, good_hits, miss_hits, total_notes, duration_seconds
        ))
        
        conn.commit()
        result_id = cursor.lastrowid
        conn.close()
        
        print(f"[Database] Saved game result ID {result_id} for song '{song_name}'")
        
        return jsonify({
            "status": "success", 
            "message": "游戏结果已保存",
            "result_id": result_id
        })
        
    except Exception as e:
        print(f"[Database] Error saving game result: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/game-stats', methods=['GET'])
def get_game_stats():
    """Get game statistics and history"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get overall stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_games,
                MAX(final_score) as best_score,
                MAX(accuracy) as best_accuracy,
                MAX(max_combo) as best_combo,
                MAX(final_spirit) as best_spirit
            FROM game_results
        ''')
        overall_stats = cursor.fetchone()
        
        # Get recent games (last 10)
        cursor.execute('''
            SELECT 
                song_name, final_score, max_combo, accuracy, final_spirit,
                perfect_hits, good_hits, miss_hits, total_notes,
                datetime(created_at, 'localtime') as play_date
            FROM game_results 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        recent_games = cursor.fetchall()
        
        # Get song-specific stats
        cursor.execute('''
            SELECT 
                song_name,
                COUNT(*) as play_count,
                MAX(final_score) as best_score,
                MAX(accuracy) as best_accuracy,
                MAX(max_combo) as best_combo
            FROM game_results 
            GROUP BY song_name
            ORDER BY play_count DESC, best_score DESC
        ''')
        song_stats = cursor.fetchall()
        
        conn.close()
        
        # Format response
        response = {
            "overall_stats": {
                "total_games": overall_stats[0] or 0,
                "best_score": overall_stats[1] or 0,
                "best_accuracy": round(overall_stats[2] or 0, 2),
                "best_combo": overall_stats[3] or 0,
                "best_spirit": round(overall_stats[4] or 0, 2)
            },
            "recent_games": [
                {
                    "song_name": game[0],
                    "final_score": game[1],
                    "max_combo": game[2],
                    "accuracy": game[3],
                    "final_spirit": game[4],
                    "perfect_hits": game[5],
                    "good_hits": game[6],
                    "miss_hits": game[7],
                    "total_notes": game[8],
                    "play_date": game[9]
                } for game in recent_games
            ],
            "song_stats": [
                {
                    "song_name": song[0],
                    "play_count": song[1],
                    "best_score": song[2],
                    "best_accuracy": song[3],
                    "best_combo": song[4]
                } for song in song_stats
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[Database] Error getting game stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/song-stats/<song_name>', methods=['GET'])
def get_song_stats(song_name):
    """Get statistics for a specific song"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get stats for specific song
        cursor.execute('''
            SELECT 
                COUNT(*) as total_games,
                MAX(final_score) as best_score,
                MAX(accuracy) as best_accuracy,
                MAX(max_combo) as best_combo,
                MAX(final_spirit) as best_spirit,
                AVG(final_score) as avg_score,
                AVG(accuracy) as avg_accuracy
            FROM game_results 
            WHERE song_name = ?
        ''', (song_name,))
        song_stats = cursor.fetchone()
        
        # Get recent plays for this song (last 5)
        cursor.execute('''
            SELECT 
                final_score, max_combo, accuracy, final_spirit,
                perfect_hits, good_hits, miss_hits, total_notes,
                datetime(created_at, 'localtime') as play_date
            FROM game_results 
            WHERE song_name = ?
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (song_name,))
        recent_plays = cursor.fetchall()
        
        conn.close()
        
        # Format response
        response = {
            "song_name": song_name,
            "stats": {
                "total_games": song_stats[0] or 0,
                "best_score": song_stats[1] or 0,
                "best_accuracy": round(song_stats[2] or 0, 2),
                "best_combo": song_stats[3] or 0,
                "best_spirit": round(song_stats[4] or 0, 2),
                "avg_score": round(song_stats[5] or 0, 2),
                "avg_accuracy": round(song_stats[6] or 0, 2)
            },
            "recent_plays": [
                {
                    "final_score": play[0],
                    "max_combo": play[1],
                    "accuracy": play[2],
                    "final_spirit": play[3],
                    "perfect_hits": play[4],
                    "good_hits": play[5],
                    "miss_hits": play[6],
                    "total_notes": play[7],
                    "play_date": play[8]
                } for play in recent_plays
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"[Database] Error getting song stats for {song_name}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
