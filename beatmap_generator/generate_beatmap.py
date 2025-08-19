import os
import sys
import numpy as np
import librosa
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib # For saving the trained model
import json

# --- Phase 1: Learning from Samples ---

def extract_features(file_path):
    """
    Extracts a feature vector from an audio file.
    Features: Mean MFCCs and Mean Spectral Centroid.
    """
    try:
        y, sr = librosa.load(file_path, sr=None)
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfccs_mean = np.mean(mfccs.T, axis=0)
        
        # Extract Spectral Centroid
        spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        spec_cent_mean = np.mean(spec_cent)

        # Extract Spectral Contrast
        spec_con = librosa.feature.spectral_contrast(y=y, sr=sr)
        spec_con_mean = np.mean(spec_con)

        # Extract Spectral Rolloff
        spec_roll = librosa.feature.spectral_rolloff(y=y, sr=sr)
        spec_roll_mean = np.mean(spec_roll)

        # Extract Zero-Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = np.mean(zcr)

        # Combine features into a single vector
        return np.hstack((mfccs_mean, spec_cent_mean, spec_con_mean, spec_roll_mean, zcr_mean))
    except Exception as e:
        print(f"  [Warning] Could not process {os.path.basename(file_path)}: {e}")
        return None

def train_classifier(project_path):
    """
    Trains an SVM classifier on the annotated don/ka samples.
    """
    print("\n--- Phase 1: Training classifier from samples ---")
    don_samples_path = os.path.join(project_path, 'generated_audio', 'don_samples')
    ka_samples_path = os.path.join(project_path, 'generated_audio', 'ka_samples')

    # 1. Load data and extract features
    X = [] # Feature vectors
    y = [] # Labels (0 for don, 1 for ka)

    print(" -> Processing 'don' samples...")
    for f in os.listdir(don_samples_path):
        if f.endswith('.wav'):
            features = extract_features(os.path.join(don_samples_path, f))
            if features is not None:
                X.append(features)
                y.append(0) # Label for 'don'

    print(" -> Processing 'ka' samples...")
    for f in os.listdir(ka_samples_path):
         if f.endswith('.wav'):
            features = extract_features(os.path.join(ka_samples_path, f))
            if features is not None:
                X.append(features)
                y.append(1) # Label for 'ka'
    
    if len(X) < 2:
        print("[Error] Not enough valid samples to train a model. Need at least one of each type.")
        return None, None

    X = np.array(X)
    y = np.array(y)

    # 2. Scale features
    # This is crucial for SVMs to work correctly.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    print(" -> Features have been scaled (standardized).")

    # 3. Train the SVM model
    # Split data for a quick accuracy test
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
    
    print(f" -> Training model on {len(X_train)} samples...")
    model = SVC(kernel='rbf', gamma='auto', probability=True) # probability=True is crucial for confidence filtering
    model.fit(X_train, y_train)

    # 4. Evaluate the model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f" -> Model training complete. Internal accuracy: {accuracy*100:.2f}%")
    
    # We must return both the model and the scaler
    return model, scaler

# --- Phase 2: Application to Full Track ---

def detect_onsets(audio_path):
    """
    Detects onsets in the full audio track.
    """
    print(f" -> Loading main track for onset detection: {os.path.basename(audio_path)}")
    try:
        y, sr = librosa.load(audio_path, sr=None)
        
        # Using a sensitive onset detection suitable for percussive tracks
        # backtrack=True helps to find the energy rise leading to the peak, which is a more robust onset definition.
        onset_frames = librosa.onset.onset_detect(
            y=y, 
            sr=sr, 
            units='frames',
            hop_length=512,
            backtrack=True # Use backtracking to find the start of the percussive event
        )
        print(f" -> Detected {len(onset_frames)} onsets using backtracking.")
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        return onset_times, y, sr
        
    except Exception as e:
        print(f"  [Error] Failed during onset detection: {e}")
        return None, None, None

def classify_onsets(onset_times, y, sr, model, scaler, confidence_threshold=0.955):
    """
    Classifies each onset as 'don', 'ka', or None based on a confidence threshold.
    """
    print(f"\n--- Phase 3: Classifying {len(onset_times)} onsets with a {confidence_threshold*100}% confidence threshold ---")
    
    classified_notes = []
    
    # Define a small window around each onset to extract features from
    # A window of 50ms is common for percussive hits
    frame_length = int(sr * 0.1) 

    for i, t in enumerate(onset_times):
        # Get the audio frame for this onset
        start_sample = int(t * sr)
        end_sample = start_sample + frame_length
        frame = y[start_sample:end_sample]

        if len(frame) == 0:
            continue

        # Extract features for this frame
        # We create a temporary WAV-like object in memory to reuse extract_features
        # This is a bit of a workaround but keeps feature extraction consistent
        # In a more advanced system, we'd refactor extract_features to accept (y, sr)
        import soundfile as sf
        from io import BytesIO
        
        buffer = BytesIO()
        sf.write(buffer, frame, sr, format='WAV')
        buffer.seek(0)
        
        features = extract_features(buffer)

        if features is not None:
            # Scale the features using the SAME scaler from training
            features_scaled = scaler.transform([features])

            # Get class probabilities
            probabilities = model.predict_proba(features_scaled)[0]
            
            # Check if the max probability meets our threshold
            max_proba = np.max(probabilities)
            if max_proba >= confidence_threshold:
                note_class = np.argmax(probabilities) # 0 for don, 1 for ka
                note_type = 'don' if note_class == 0 else 'ka'
                classified_notes.append({'time': t, 'type': note_type})
        
        # Simple progress indicator
        if (i + 1) % 100 == 0:
            print(f" -> Processed {i + 1}/{len(onset_times)} onsets...")

    print(f" -> Successfully classified {len(classified_notes)} notes.")
    return classified_notes

def generate_beatmap_json(classified_notes, project_path):
    """
    Generates the final beatmap JSON file from the classified notes.
    """
    print(f"\n--- Phase 4: Generating final beatmap JSON ---")
    
    # Simple metadata for now
    project_name = os.path.basename(project_path)
    metadata = {
        "songName": project_name,
        "artist": "Unknown",
        "audioFile": f"data/{project_name}/generated_audio/drums.mp3", # Relative path for the game
        "bpm": 120, # Placeholder - BPM detection is a future step
        "offset": 0,
        "difficulty": "Oni"
    }

    # Prepare notes in the final format, rounding to 3 decimal places
    notes_formatted = [
        {"time": round(note['time'], 3), "type": note['type']}
        for note in classified_notes
    ]

    beatmap_data = {
        "metadata": metadata,
        "notes": notes_formatted
    }

    # Write to file
    output_filename = f"beatmap_generated.json"
    output_path = os.path.join(project_path, output_filename)

    try:
        with open(output_path, 'w') as f:
            json.dump(beatmap_data, f, indent=4)
        print(f" -> Successfully created beatmap file at: {output_path}")
    except Exception as e:
        print(f"  [Error] Failed to write JSON file: {e}")

def evaluate_beatmap(predicted_notes, ground_truth_path, time_windows, tolerance=0.15):
    """
    Evaluates the generated beatmap against the ground truth annotations.
    """
    print(f"\n--- Phase 5: Evaluating beatmap against ground truth ---")

    # 1. Load ground truth
    try:
        with open(ground_truth_path, 'r') as f:
            ground_truth_data = json.load(f)
        # The annotator saves a list of dicts, not a nested structure
        ground_truth_notes = [{"time": note['time'], "type": note['type']} for note in ground_truth_data]
    except Exception as e:
        print(f"  [Error] Could not load or parse ground truth file: {e}")
        return

    # 2. Filter both lists by the specified time windows
    filter_notes = lambda notes: [
        note for note in notes
        if any(start <= note['time'] <= end for start, end in time_windows)
    ]
    
    predicted_filtered = sorted(filter_notes(predicted_notes), key=lambda x: x['time'])
    ground_truth_filtered = sorted(filter_notes(ground_truth_notes), key=lambda x: x['time'])

    print(f" -> Evaluating within time windows: {time_windows}")
    print(f" -> Found {len(ground_truth_filtered)} ground truth notes and {len(predicted_filtered)} predicted notes in these windows.")

    if not ground_truth_filtered:
        print("  [Warning] No ground truth notes found in the specified time windows. Cannot evaluate.")
        return

    # 3. Match notes and calculate metrics
    true_positives = 0
    false_positives = 0
    
    # Keep track of which ground truth notes have been matched to prevent double counting
    matched_gt_indices = set()

    for p_note in predicted_filtered:
        best_match_gt_idx = -1
        min_time_diff = float('inf')

        # Find the closest ground truth note within the tolerance
        for i, gt_note in enumerate(ground_truth_filtered):
            if i in matched_gt_indices:
                continue
            
            time_diff = abs(p_note['time'] - gt_note['time'])
            if time_diff <= tolerance and time_diff < min_time_diff:
                min_time_diff = time_diff
                best_match_gt_idx = i

        if best_match_gt_idx != -1:
            # We found a time match. Now check if the type is also correct.
            if p_note['type'] == ground_truth_filtered[best_match_gt_idx]['type']:
                true_positives += 1
                matched_gt_indices.add(best_match_gt_idx)
            else:
                # Time match but wrong type: counts as a false positive
                false_positives += 1
        else:
            # No time match found within tolerance: it's a false positive
            false_positives += 1
            
    false_negatives = len(ground_truth_filtered) - len(matched_gt_indices)

    # 4. Calculate Precision, Recall, and F1-Score
    # Avoid division by zero
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n--- Evaluation Report ---")
    print(f"  - Precision: {precision:.2%}")
    print(f"  - Recall:    {recall:.2%}")
    print(f"  - F1-Score:  {f1_score:.2%}")
    print("-------------------------")

def main(project_path):
    """
    Main function to drive the beatmap generation process.
    """
    # --- Step 1: Train the model and get the scaler ---
    model, scaler = train_classifier(project_path)
    
    if model is None or scaler is None:
        sys.exit(1)

    # --- Step 2: Detect onsets in the main drum track ---
    print("\n--- Phase 2: Detecting onsets in full drum track ---")
    main_drum_track = os.path.join(project_path, 'generated_audio', 'drums.mp3')
    if not os.path.exists(main_drum_track):
        print(f"[Error] Main drum track not found at: {main_drum_track}")
        sys.exit(1)
    
    onset_times, y, sr = detect_onsets(main_drum_track)

    if onset_times is None:
        sys.exit(1)

    # --- Step 3: Classify each onset ---
    classified_notes = classify_onsets(onset_times, y, sr, model, scaler)

    # --- Step 4: Generate final beatmap ---
    generate_beatmap_json(classified_notes, project_path)

    # --- Step 5: Evaluate the generated beatmap ---
    ground_truth_file = os.path.join(project_path, 'annotation', 'annotations.json')
    if os.path.exists(ground_truth_file):
        evaluate_beatmap(
            predicted_notes=classified_notes,
            ground_truth_path=ground_truth_file,
            time_windows=[(0, 72), (110, 170)]
        )
    else:
        print("\n--- Phase 5: Evaluation ---")
        print(f"  [Warning] Ground truth file not found at '{ground_truth_file}'. Skipping evaluation.")

    print("\nBeatmap generation process finished successfully!")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 beatmap_generator/generate_beatmap.py <path_to_project_directory>")
        sys.exit(1)
    
    project_directory = sys.argv[1]
    if not os.path.isdir(project_directory):
        print(f"Error: Directory not found at '{project_directory}'")
        sys.exit(1)

    main(project_directory)
