from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment
import os
import time
import json

# Import our new DAW modules
try:
    from .bpm_detector import BPMDetector
    from .beat_grid import BeatGridGenerator
    from .measure_detector import FirstMeasureDetector
    DAW_MODULES_AVAILABLE = True
except ImportError:
    # Handle relative import issues when running as script
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from bpm_detector import BPMDetector
        from beat_grid import BeatGridGenerator
        from measure_detector import FirstMeasureDetector
        DAW_MODULES_AVAILABLE = True
    except ImportError as e:
        print(f"[Warning] DAW modules not available: {e}")
        DAW_MODULES_AVAILABLE = False

# --- Define Absolute Paths ---
# This makes the server runnable from any directory
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_ROOT, '..'))
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

app = Flask(__name__, static_folder=None)


# --- Frontend Routes ---

@app.route('/')
def serve_annotator_index():
    return send_from_directory(ANNOTATOR_DIR, 'index.html')

@app.route('/daw')
def serve_daw_interface():
    """Serves the new DAW-style annotation interface."""
    return send_from_directory(ANNOTATOR_DIR, 'daw_interface.html')

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
    # This serves assets like JS, CSS from the annotator folder
    return send_from_directory(ANNOTATOR_DIR, filename)

@app.route('/visualizer/<path:filename>')
def serve_visualizer_static(filename):
    """Serves static files for the beatmap visualizer (JS, CSS)."""
    return send_from_directory(VISUALIZER_DIR, filename)

# --- DAW API Routes ---

@app.route('/api/detect_bpm', methods=['POST'])
def detect_bpm():
    """Detect BPM for audio file"""
    if not DAW_MODULES_AVAILABLE:
        return jsonify({"status": "error", "message": "BPM detection modules not available"}), 500
    
    try:
        data = request.json
        project_name = data.get('projectName')
        audio_file = data.get('audioFile', 'drums.mp3')
        
        if not project_name:
            return jsonify({"status": "error", "message": "Project name required"}), 400
        
        # Construct audio file path
        audio_path = os.path.join(DATA_DIR, project_name, 'generated_audio', audio_file)
        
        if not os.path.exists(audio_path):
            return jsonify({"status": "error", "message": f"Audio file not found: {audio_file}"}), 404
        
        # Detect BPM
        detector = BPMDetector()
        result = detector.detect_bpm(audio_path)
        
        return jsonify({
            "status": "success",
            "bpm_data": result
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
        alignment_result = aligner.auto_align_annotations(
            annotations=annotations,
            beat_grid=beat_grid,
            quantize_mode=quantize_enum,
            swing_amount=swing_enum,
            custom_swing=custom_swing,
            tolerance=tolerance,
            preserve_off_beat=preserve_off_beat,
            first_measure_start=first_measure['first_measure_start']
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

# --- API Routes ---

@app.route('/api/projects')
def list_projects():
    """Scans the 'data/' directory for subfolders and returns them as a list."""
    try:
        if not os.path.isdir(DATA_DIR):
            return jsonify({"status": "error", "message": "'data' 目录未找到。"}), 404
        projects = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
        return jsonify({"status": "success", "projects": projects})
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
