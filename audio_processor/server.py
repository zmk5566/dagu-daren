from flask import Flask, request, jsonify, send_from_directory
from pydub import AudioSegment
import os
import time
import json

app = Flask(__name__, static_folder=None)

# --- Define Absolute Paths ---
# This makes the server runnable from any directory
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_ROOT, '..'))
ANNOTATOR_DIR = os.path.join(PROJECT_ROOT, 'annotator')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')


# --- Frontend Routes ---

@app.route('/')
def serve_annotator_index():
    return send_from_directory(ANNOTATOR_DIR, 'index.html')

@app.route('/data/<path:filepath>')
def serve_data_files(filepath):
    """Serves files from the 'data' directory (e.g., audio files)."""
    return send_from_directory(DATA_DIR, filepath)

@app.route('/<path:filename>')
def serve_annotator_static(filename):
    # This serves assets like JS, CSS from the annotator folder
    return send_from_directory(ANNOTATOR_DIR, filename)

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
