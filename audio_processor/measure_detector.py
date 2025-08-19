import numpy as np
import librosa
from typing import Dict, List, Tuple, Optional
from scipy.signal import find_peaks

try:
    from .bpm_detector import BPMDetector
    from .beat_grid import BeatGridGenerator
except ImportError:
    from bpm_detector import BPMDetector
    from beat_grid import BeatGridGenerator

class FirstMeasureDetector:
    """
    Intelligent first measure detection for 大鼓达人.
    
    Analyzes drum patterns and musical structure to find the natural starting point
    of the first complete measure, essential for proper beat alignment in DAW interface.
    """
    
    def __init__(self, time_signature: Tuple[int, int] = (4, 4)):
        self.time_signature = time_signature
        self.bpm_detector = BPMDetector()
        self.beat_grid = BeatGridGenerator(time_signature)
        
    def detect_first_measure(self, audio_path: str, bpm_override: Optional[float] = None) -> Dict:
        """
        Detect the starting position of the first complete musical measure.
        
        Args:
            audio_path: Path to audio file
            bpm_override: Optional manual BPM override
            
        Returns:
            Dictionary with first measure detection results
        """
        try:
            print(f"[FirstMeasure] Analyzing: {audio_path}")
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            
            # Get BPM and beat grid
            if bpm_override:
                bpm = bpm_override
                print(f"[FirstMeasure] Using manual BPM: {bpm}")
            else:
                bpm_result = self.bpm_detector.detect_bpm(audio_path)
                bpm = bpm_result['bpm']
                print(f"[FirstMeasure] Using detected BPM: {bpm}")
            
            # Generate initial beat grid
            beat_grid = self.beat_grid.generate_beat_grid(audio_path, bpm)
            
            # Multiple detection methods
            onset_method = self._detect_by_onset_patterns(y, sr, bpm)
            spectral_method = self._detect_by_spectral_novelty(y, sr, bpm)
            energy_method = self._detect_by_energy_patterns(y, sr, bpm)
            
            # Combine results
            candidates = [onset_method, spectral_method, energy_method]
            best_result = max(candidates, key=lambda x: x['confidence'])
            
            # Validate and refine the result
            validated_result = self._validate_first_measure(y, sr, bpm, best_result['start_time'])
            
            result = {
                'first_measure_start': validated_result['start_time'],
                'confidence': validated_result['confidence'],
                'bpm': bpm,
                'time_signature': self.time_signature,
                'method_used': validated_result['method'],
                'measure_length': 60.0 / bpm * self.time_signature[0],
                'beat_grid_aligned': True,
                'analysis': {
                    'onset_detection': onset_method,
                    'spectral_detection': spectral_method,
                    'energy_detection': energy_method,
                    'validation': validated_result
                }
            }
            
            print(f"[FirstMeasure] Detected first measure at: {result['first_measure_start']:.3f}s "
                  f"(confidence: {result['confidence']:.3f})")
            
            return result
            
        except Exception as e:
            print(f"[FirstMeasure] Error detecting first measure: {e}")
            return self._fallback_first_measure(bpm if 'bpm' in locals() else 120.0)
    
    def _detect_by_onset_patterns(self, y: np.ndarray, sr: int, bpm: float) -> Dict:
        """Method 1: Detect first measure by analyzing onset patterns"""
        try:
            # Get onset times
            onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, units='frames', hop_length=512, backtrack=True
            )
            onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
            
            if len(onset_times) < 4:
                return {'start_time': 0.0, 'confidence': 0.0, 'method': 'onset_patterns'}
            
            # Calculate expected measure length
            beats_per_measure = self.time_signature[0]
            measure_length = (60.0 / bpm) * beats_per_measure
            
            # Look for patterns that suggest measure boundaries
            # Strong onsets often occur at measure starts
            onset_strengths = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
            onset_strength_times = librosa.frames_to_time(range(len(onset_strengths)), sr=sr, hop_length=512)
            
            # Find peaks in onset strength
            peaks, properties = find_peaks(
                onset_strengths, 
                height=np.percentile(onset_strengths, 70),  # Top 30% of peaks
                distance=int(sr * 0.1 / 512)  # Minimum 100ms between peaks
            )
            
            peak_times = onset_strength_times[peaks]
            peak_heights = onset_strengths[peaks]
            
            # Score potential measure starts
            candidates = []
            for i, peak_time in enumerate(peak_times[:20]):  # Check first 20 peaks
                if peak_time < measure_length * 2:  # Within first 2 measures
                    # Score based on:
                    # 1. Peak strength
                    # 2. Position consistency with expected beat grid
                    # 3. Following onset pattern strength
                    
                    peak_score = peak_heights[i] / np.max(peak_heights)
                    
                    # Check if subsequent beats align well
                    alignment_score = self._score_beat_alignment(
                        peak_time, bpm, onset_times, measure_length
                    )
                    
                    total_score = (peak_score * 0.4 + alignment_score * 0.6)
                    
                    candidates.append({
                        'start_time': peak_time,
                        'score': total_score,
                        'peak_strength': peak_score,
                        'alignment_score': alignment_score
                    })
            
            if candidates:
                best = max(candidates, key=lambda x: x['score'])
                return {
                    'start_time': best['start_time'],
                    'confidence': best['score'],
                    'method': 'onset_patterns'
                }
            else:
                return {'start_time': 0.0, 'confidence': 0.0, 'method': 'onset_patterns'}
                
        except Exception as e:
            print(f"[FirstMeasure] Onset pattern detection failed: {e}")
            return {'start_time': 0.0, 'confidence': 0.0, 'method': 'onset_patterns'}
    
    def _detect_by_spectral_novelty(self, y: np.ndarray, sr: int, bpm: float) -> Dict:
        """Method 2: Detect using spectral novelty analysis"""
        try:
            # Compute spectral features
            stft = librosa.stft(y, hop_length=512)
            spectral_centroids = librosa.feature.spectral_centroid(S=np.abs(stft), sr=sr)
            spectral_rolloff = librosa.feature.spectral_rolloff(S=np.abs(stft), sr=sr)
            
            # Compute novelty (rate of change in spectral features)
            centroid_novelty = np.diff(spectral_centroids[0])
            rolloff_novelty = np.diff(spectral_rolloff[0])
            
            # Combine novelties
            combined_novelty = np.abs(centroid_novelty) + np.abs(rolloff_novelty)
            
            # Find peaks in novelty
            peaks, _ = find_peaks(
                combined_novelty,
                height=np.percentile(combined_novelty, 80),
                distance=int(sr * 0.2 / 512)  # Minimum 200ms between peaks
            )
            
            # Convert to time
            novelty_times = librosa.frames_to_time(peaks, sr=sr, hop_length=512)
            
            # Score candidates based on spectral changes
            measure_length = (60.0 / bpm) * self.time_signature[0]
            
            best_time = 0.0
            best_score = 0.0
            
            for peak_time in novelty_times:
                if peak_time < measure_length * 1.5:  # Within first 1.5 measures
                    # Score based on timing and novelty strength
                    peak_idx = np.where(novelty_times == peak_time)[0][0]
                    novelty_strength = combined_novelty[peaks[peak_idx]]
                    
                    # Prefer peaks that align with expected beat positions
                    alignment_score = self._score_time_alignment(peak_time, bpm)
                    
                    total_score = (novelty_strength / np.max(combined_novelty)) * 0.5 + alignment_score * 0.5
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_time = peak_time
            
            return {
                'start_time': best_time,
                'confidence': best_score,
                'method': 'spectral_novelty'
            }
            
        except Exception as e:
            print(f"[FirstMeasure] Spectral novelty detection failed: {e}")
            return {'start_time': 0.0, 'confidence': 0.0, 'method': 'spectral_novelty'}
    
    def _detect_by_energy_patterns(self, y: np.ndarray, sr: int, bpm: float) -> Dict:
        """Method 3: Detect using energy pattern analysis"""
        try:
            # Compute RMS energy in frames
            hop_length = 512
            frame_length = 2048
            rms_energy = librosa.feature.rms(
                y=y, frame_length=frame_length, hop_length=hop_length
            )[0]
            
            # Find energy peaks
            energy_peaks, _ = find_peaks(
                rms_energy,
                height=np.percentile(rms_energy, 75),
                distance=int(sr * 0.15 / hop_length)  # 150ms minimum distance
            )
            
            energy_peak_times = librosa.frames_to_time(energy_peaks, sr=sr, hop_length=hop_length)
            
            # Look for periodic energy patterns that suggest measure boundaries
            measure_length = (60.0 / bpm) * self.time_signature[0]
            
            best_time = 0.0
            best_score = 0.0
            
            for peak_time in energy_peak_times:
                if peak_time < measure_length * 1.5:
                    # Score based on energy level and position
                    peak_idx = np.where(energy_peak_times == peak_time)[0][0]
                    energy_level = rms_energy[energy_peaks[peak_idx]]
                    
                    # Check for periodic pattern following this peak
                    pattern_score = self._score_periodic_pattern(
                        peak_time, energy_peak_times, measure_length
                    )
                    
                    total_score = (energy_level / np.max(rms_energy)) * 0.3 + pattern_score * 0.7
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_time = peak_time
            
            return {
                'start_time': best_time,
                'confidence': best_score,
                'method': 'energy_patterns'
            }
            
        except Exception as e:
            print(f"[FirstMeasure] Energy pattern detection failed: {e}")
            return {'start_time': 0.0, 'confidence': 0.0, 'method': 'energy_patterns'}
    
    def _score_beat_alignment(self, start_time: float, bpm: float, onset_times: np.ndarray, measure_length: float) -> float:
        """Score how well onsets align with expected beat positions"""
        try:
            beat_interval = 60.0 / bpm
            tolerance = beat_interval * 0.1  # 10% tolerance
            
            # Generate expected beat times from this start
            expected_beats = []
            for i in range(self.time_signature[0] * 2):  # Check 2 measures
                expected_beats.append(start_time + i * beat_interval)
            
            # Count how many onsets align with expected beats
            aligned_count = 0
            for expected_beat in expected_beats:
                # Find closest onset
                if len(onset_times) > 0:
                    closest_onset_distance = np.min(np.abs(onset_times - expected_beat))
                    if closest_onset_distance <= tolerance:
                        aligned_count += 1
            
            return aligned_count / len(expected_beats) if expected_beats else 0.0
            
        except Exception:
            return 0.0
    
    def _score_time_alignment(self, time: float, bpm: float) -> float:
        """Score how well a time aligns with expected beat grid"""
        beat_interval = 60.0 / bpm
        
        # Check alignment with beat positions
        beat_phase = (time % beat_interval) / beat_interval
        
        # Prefer times that are close to beat positions (0, 0.25, 0.5, 0.75)
        alignment_scores = [
            1.0 - abs(beat_phase - 0.0),      # Downbeat
            0.8 - abs(beat_phase - 0.25),     # Quarter beat
            0.6 - abs(beat_phase - 0.5),      # Half beat
            0.8 - abs(beat_phase - 0.75),     # Three-quarter beat
        ]
        
        return max(alignment_scores)
    
    def _score_periodic_pattern(self, start_time: float, peak_times: np.ndarray, measure_length: float) -> float:
        """Score periodicity of peaks following the start time"""
        try:
            # Look for peaks at measure intervals
            expected_times = [start_time + i * measure_length for i in range(1, 4)]  # Next 3 measures
            tolerance = measure_length * 0.1  # 10% tolerance
            
            matches = 0
            for expected_time in expected_times:
                if len(peak_times) > 0:
                    distances = np.abs(peak_times - expected_time)
                    if np.min(distances) <= tolerance:
                        matches += 1
            
            return matches / len(expected_times) if expected_times else 0.0
            
        except Exception:
            return 0.0
    
    def _validate_first_measure(self, y: np.ndarray, sr: int, bpm: float, candidate_start: float) -> Dict:
        """Validate and refine the detected first measure start"""
        try:
            # Fine-tune the position by looking for the exact onset near the candidate
            search_window = 60.0 / bpm * 0.25  # Quarter beat window
            
            start_sample = max(0, int((candidate_start - search_window) * sr))
            end_sample = min(len(y), int((candidate_start + search_window) * sr))
            
            if end_sample <= start_sample:
                return {'start_time': candidate_start, 'confidence': 0.5, 'method': 'validation_failed'}
            
            window_audio = y[start_sample:end_sample]
            
            # Find the strongest onset in this window
            onset_frames = librosa.onset.onset_detect(
                y=window_audio, sr=sr, units='frames', hop_length=128
            )
            
            if len(onset_frames) > 0:
                # Get onset strengths
                onset_strength = librosa.onset.onset_strength(
                    y=window_audio, sr=sr, hop_length=128
                )
                
                if len(onset_frames) > 0 and len(onset_strength) > max(onset_frames):
                    strongest_onset_idx = onset_frames[np.argmax(onset_strength[onset_frames])]
                    strongest_onset_time = librosa.frames_to_time(
                        strongest_onset_idx, sr=sr, hop_length=128
                    )
                    
                    refined_start = candidate_start - search_window + strongest_onset_time
                    
                    return {
                        'start_time': refined_start,
                        'confidence': 0.8,
                        'method': 'validated_onset'
                    }
            
            # If no strong onset found, use original candidate
            return {
                'start_time': candidate_start,
                'confidence': 0.6,
                'method': 'original_candidate'
            }
            
        except Exception as e:
            print(f"[FirstMeasure] Validation failed: {e}")
            return {'start_time': candidate_start, 'confidence': 0.3, 'method': 'validation_error'}
    
    def _fallback_first_measure(self, bpm: float) -> Dict:
        """Fallback when detection fails"""
        return {
            'first_measure_start': 0.0,
            'confidence': 0.0,
            'bpm': bpm,
            'time_signature': self.time_signature,
            'method_used': 'fallback',
            'measure_length': 60.0 / bpm * self.time_signature[0],
            'beat_grid_aligned': False,
            'analysis': {
                'error': 'Detection failed, using fallback'
            }
        }

def test_first_measure_detection():
    """Test first measure detection"""
    detector = FirstMeasureDetector()
    
    test_audio = "/Users/k/Documents/GitHub/taigu-online-practice/data/xwx-backtrack-n-drum/generated_audio/drums.mp3"
    
    if os.path.exists(test_audio):
        print(f"Testing first measure detection on: {test_audio}")
        
        result = detector.detect_first_measure(test_audio)
        
        print(f"\n=== First Measure Detection Results ===")
        print(f"First measure starts at: {result['first_measure_start']:.3f}s")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Method used: {result['method_used']}")
        print(f"BPM: {result['bpm']}")
        print(f"Measure length: {result['measure_length']:.3f}s")
        
        # Show analysis details
        if 'analysis' in result:
            print(f"\n=== Analysis Details ===")
            for method, details in result['analysis'].items():
                if isinstance(details, dict) and 'confidence' in details:
                    print(f"{method}: {details['start_time']:.3f}s (conf: {details['confidence']:.3f})")
    else:
        print(f"Test audio file not found: {test_audio}")

if __name__ == "__main__":
    import os
    test_first_measure_detection()