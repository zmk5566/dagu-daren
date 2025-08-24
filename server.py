from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment
import os
import sys
import time
import json
import uuid
import shutil
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

app = Flask(__name__, static_folder=None)

# Configure upload settings
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_image_file(filename):
    """Check if file has allowed image extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# --- Frontend Routes ---

@app.route('/')
def serve_annotator_index():
    return send_from_directory(ANNOTATOR_DIR, 'index.html')

@app.route('/daw')
def serve_daw_interface():
    """Serves the new DAW-style annotation interface."""
    return send_from_directory(ANNOTATOR_DIR, 'daw_interface.html')

@app.route('/game')
def serve_game_interface():
    """Serves the rhythm game performance mode interface."""
    return send_from_directory(PROJECT_ROOT, 'game_interface.html')

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
