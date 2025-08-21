import numpy as np
import librosa
import os
from typing import Tuple, List, Dict, Optional
from scipy import stats

# Try to import BeatNet for advanced BPM detection
try:
    from BeatNet.BeatNet import BeatNet
    BEATNET_AVAILABLE = True
    print("[BPM] BeatNet available - using advanced deep learning BPM detection")
except ImportError:
    BEATNET_AVAILABLE = False
    print("[BPM] BeatNet not available - falling back to librosa methods")

class BPMDetector:
    """
    Advanced BPM detection engine for 大鼓达人 DAW-style annotation tool.
    
    Features:
    - Multiple algorithm approach for robust BPM detection
    - Confidence scoring for BPM quality assessment
    - Beat tracking with precise timing
    - Support for complex time signatures
    """
    
    def __init__(self, hop_length: int = 512, sr: int = 22050):
        self.hop_length = hop_length
        self.sr = sr
        
        # Initialize BeatNet if available
        self.beatnet_estimator = None
        if BEATNET_AVAILABLE:
            try:
                self.beatnet_estimator = BeatNet(1, mode='offline', inference_model='DBN', plot=[], thread=False)
                print("[BPM] BeatNet estimator initialized successfully")
            except Exception as e:
                print(f"[BPM] Failed to initialize BeatNet: {e}")
                self.beatnet_estimator = None
        
    def detect_bpm(self, audio_path: str) -> Dict:
        """
        Detect BPM using multiple algorithms and return the most confident result.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with BPM, confidence score, and beat times
        """
        try:
            print(f"[BPM] Analyzing: {os.path.basename(audio_path)}")
            
            # Use BeatNet exclusively - no fallback methods
            if self.beatnet_estimator is None:
                raise RuntimeError("BeatNet not available - cannot perform BPM detection")
            
            return self._detect_tempo_beatnet(audio_path)
            
        except Exception as e:
            print(f"[BPM] Error detecting BPM: {e}")
            return {
                'bpm': 120.0,  # Fallback BPM
                'confidence': 0.0,
                'beat_times': [],
                'method_used': 'fallback',
                'error': str(e)
            }
    
    def _detect_tempo_beatnet(self, audio_path: str) -> Dict:
        """Advanced BPM detection using BeatNet deep learning model with offset calculation"""
        try:
            # Process audio with BeatNet
            output = self.beatnet_estimator.process(audio_path)
            
            if output is None or len(output) == 0:
                raise RuntimeError("BeatNet failed to detect any beats")
            
            beat_times = output[:, 0]  # First column is timestamps
            beat_types = output[:, 1]  # Second column is beat types (1=downbeat, 2=beat)
            
            print(f"[BPM] BeatNet detected {len(beat_times)} beats")
            
            # Linear regression for overall tempo
            beat_numbers = np.arange(len(beat_times))
            slope, intercept, r_value, p_value, std_err = stats.linregress(beat_times, beat_numbers)
            fitted_bpm = slope * 60
            
            # Calculate confidence based on R² value
            r_squared = r_value ** 2
            confidence = r_squared  # Direct use of R² as confidence
            
            # Validate BPM range
            if not (60 <= fitted_bpm <= 200):
                # Try harmonic relationships
                for harmonic in [2, 0.5, 4, 0.25]:
                    adjusted_bpm = fitted_bpm * harmonic
                    if 60 <= adjusted_bpm <= 200:
                        fitted_bpm = adjusted_bpm
                        confidence *= 0.9
                        break
                else:
                    raise RuntimeError(f"BPM {fitted_bpm:.1f} outside valid range")
            
            # Calculate offset for downbeat alignment
            offset = self._calculate_downbeat_offset(beat_times, beat_types, fitted_bpm)
            
            # Prepare complete beat data with types
            beat_data = []
            for i, (time, beat_type) in enumerate(zip(beat_times, beat_types)):
                beat_data.append({
                    'time': float(time),
                    'type': 'downbeat' if beat_type == 1 else 'beat',
                    'index': i
                })
            
            # Calculate residuals for quality assessment
            residuals = beat_numbers - (slope * beat_times + intercept)
            max_residual = np.max(np.abs(residuals))
            
            # Count downbeats
            downbeat_count = len(np.where(beat_types == 1)[0])
            
            print(f"[BPM] Analysis: {fitted_bpm:.1f} BPM, R²={r_squared:.6f}, offset={offset:.3f}s, downbeats={downbeat_count}")
            
            return {
                'bpm': float(fitted_bpm),
                'confidence': float(confidence),
                'beat_times': beat_times.tolist(),  # Keep for backward compatibility
                'beat_data': beat_data,  # Complete beat information
                'offset': float(offset),  # Calculated offset for alignment
                'method_used': 'beatnet_deep_learning',
                'r_squared': r_squared,
                'max_residual': max_residual,
                'total_beats': len(beat_times),
                'downbeat_count': downbeat_count
            }
            
        except Exception as e:
            print(f"[BPM] BeatNet method failed: {e}")
            raise RuntimeError(f"BeatNet detection failed: {e}")
    
    def _detect_tempo_onset(self, y: np.ndarray, sr: int) -> Dict:
        """Method 1: Onset-based tempo detection"""
        try:
            # Get onset envelope
            onset_envelope = librosa.onset.onset_strength(
                y=y, sr=sr, hop_length=self.hop_length
            )
            
            # Detect tempo from onset envelope
            tempo = librosa.beat.tempo(
                onset_envelope=onset_envelope, 
                sr=sr, 
                hop_length=self.hop_length,
                aggregate=None  # Get all tempo estimates
            )[0]  # Take the strongest one
            
            # Calculate confidence based on onset strength consistency
            confidence = self._calculate_onset_confidence(onset_envelope, tempo, sr)
            
            return {
                'bpm': float(tempo),
                'confidence': confidence,
                'method_used': 'onset_envelope'
            }
        except Exception as e:
            print(f"[BPM] Onset method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method_used': 'onset_envelope'}
    
    def _detect_tempo_beat_tracking(self, y: np.ndarray, sr: int) -> Dict:
        """Method 2: Beat tracking approach"""
        try:
            # Get tempo and beat frames
            tempo, beat_frames = librosa.beat.beat_track(
                y=y, sr=sr, hop_length=self.hop_length, units='frames'
            )
            
            # Calculate confidence from beat consistency
            if len(beat_frames) > 1:
                beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=self.hop_length)
                beat_intervals = np.diff(beat_times)
                confidence = 1.0 - (np.std(beat_intervals) / np.mean(beat_intervals))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
            else:
                confidence = 0.0
            
            return {
                'bpm': float(tempo),
                'confidence': confidence,
                'method_used': 'beat_tracking'
            }
        except Exception as e:
            print(f"[BPM] Beat tracking method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method_used': 'beat_tracking'}
    
    def _detect_tempo_spectral(self, y: np.ndarray, sr: int) -> Dict:
        """Method 3: Spectral-based tempo detection"""
        try:
            # Compute spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(
                y=y, sr=sr, hop_length=self.hop_length
            )[0]
            
            # Find periodicity in spectral centroid
            # This works well for music with strong rhythmic content
            autocorr = np.correlate(spectral_centroids, spectral_centroids, mode='full')
            autocorr = autocorr[autocorr.size // 2:]
            
            # Find peaks in autocorrelation
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(autocorr, height=np.max(autocorr) * 0.3)
            
            if len(peaks) > 0:
                # Convert peak position to BPM
                time_per_frame = self.hop_length / sr
                period_seconds = peaks[0] * time_per_frame
                bpm = 60.0 / period_seconds
                
                # Ensure BPM is in reasonable range
                if 60 <= bpm <= 200:
                    confidence = autocorr[peaks[0]] / np.max(autocorr)
                else:
                    # Try harmonic relationships
                    for harmonic in [2, 0.5, 4, 0.25]:
                        adjusted_bpm = bpm * harmonic
                        if 60 <= adjusted_bpm <= 200:
                            bpm = adjusted_bpm
                            confidence = autocorr[peaks[0]] / np.max(autocorr) * 0.8
                            break
                    else:
                        bpm = 120.0
                        confidence = 0.0
            else:
                bpm = 120.0
                confidence = 0.0
            
            return {
                'bpm': float(bpm),
                'confidence': float(confidence),
                'method_used': 'spectral_periodicity'
            }
        except Exception as e:
            print(f"[BPM] Spectral method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method_used': 'spectral_periodicity'}
    
    def _calculate_onset_confidence(self, onset_envelope: np.ndarray, bpm: float, sr: int) -> float:
        """Calculate confidence score based on onset strength consistency"""
        try:
            # Expected beat interval in frames
            beat_interval_frames = int((60.0 / bpm) * sr / self.hop_length)
            
            if beat_interval_frames <= 0:
                return 0.0
            
            # Create a template for expected beats
            template_length = min(len(onset_envelope), beat_interval_frames * 8)
            template = np.zeros(template_length)
            
            # Place expected beats
            for i in range(0, template_length, beat_interval_frames):
                if i < template_length:
                    template[i] = 1.0
            
            # Correlate with actual onset envelope
            if len(onset_envelope) >= len(template):
                correlation = np.correlate(
                    onset_envelope[:len(template)], 
                    template, 
                    mode='valid'
                )[0]
                
                # Normalize correlation
                template_energy = np.sum(template ** 2)
                envelope_energy = np.sum(onset_envelope[:len(template)] ** 2)
                
                if template_energy > 0 and envelope_energy > 0:
                    normalized_correlation = correlation / np.sqrt(template_energy * envelope_energy)
                    return max(0.0, min(1.0, normalized_correlation))
            
            return 0.0
        except Exception:
            return 0.0
    
    def _generate_beat_times(self, y: np.ndarray, sr: int, bpm: float) -> np.ndarray:
        """Generate precise beat times based on detected BPM"""
        try:
            # Use librosa's beat tracking with the detected tempo
            _, beat_frames = librosa.beat.beat_track(
                y=y, sr=sr, hop_length=self.hop_length, 
                bpm=bpm, units='frames'
            )
            
            # Convert frames to time
            beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=self.hop_length)
            
            return beat_times
        except Exception as e:
            print(f"[BPM] Failed to generate beat times: {e}")
            # Fallback: generate regular beat times
            duration = len(y) / sr
            beat_interval = 60.0 / bpm
            return np.arange(0, duration, beat_interval)
    
    def _calculate_downbeat_offset(self, beat_times: np.ndarray, beat_types: np.ndarray, bpm: float) -> float:
        """Calculate optimal offset to align downbeats with measure grid"""
        try:
            # Find all downbeats
            downbeat_indices = np.where(beat_types == 1)[0]
            if len(downbeat_indices) < 2:
                return 0.0  # Not enough downbeats to calculate offset
            
            downbeat_times = beat_times[downbeat_indices]
            
            # Calculate expected measure duration (assuming 4/4 time)
            beats_per_minute = bpm
            beats_per_second = beats_per_minute / 60.0
            beats_per_measure = 4  # Assuming 4/4 time signature
            measure_duration = beats_per_measure / beats_per_second
            
            print(f"[Offset] Measure duration: {measure_duration:.3f}s, analyzing {len(downbeat_times)} downbeats")
            
            # Try different offset values to find best alignment
            best_offset = 0.0
            best_score = float('inf')
            
            # Test offset range from 0 to one measure duration
            test_offsets = np.linspace(0, measure_duration, 100)
            
            for offset in test_offsets:
                # Calculate how well downbeats align with measure grid after applying offset
                adjusted_times = downbeat_times + offset
                # Find how far each downbeat is from nearest measure grid line
                grid_positions = adjusted_times / measure_duration
                deviations = np.abs(grid_positions - np.round(grid_positions))
                # Score is average deviation (lower is better)
                score = np.mean(deviations)
                
                if score < best_score:
                    best_score = score
                    best_offset = offset
            
            # Negative offset means we need to wait before starting
            final_offset = -best_offset
            
            print(f"[Offset] Best offset: {final_offset:.3f}s (alignment score: {best_score:.4f})")
            
            return final_offset
            
        except Exception as e:
            print(f"[Offset] Calculation failed: {e}")
            return 0.0

def test_bpm_detection():
    """Test BPM detection on the current project's drum track"""
    detector = BPMDetector()
    
    # Test on the xwx-backtrack-n-drum project
    test_audio = "/Users/k/Documents/GitHub/taigu-online-practice/data/xwx-backtrack-n-drum/generated_audio/drums.mp3"
    
    if os.path.exists(test_audio):
        print(f"Testing BPM detection on: {test_audio}")
        result = detector.detect_bpm(test_audio)
        
        print("\n=== BPM Detection Results ===")
        print(f"BPM: {result['bpm']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Method used: {result['method_used']}")
        print(f"Beat times detected: {len(result['beat_times'])} beats")
        
        if result['beat_times']:
            print(f"First few beat times: {result['beat_times'][:10]}")
        
        # Show all candidates
        print("\n=== All Method Results ===")
        for candidate in result.get('all_candidates', []):
            print(f"{candidate['method_used']}: {candidate['bpm']:.2f} BPM (conf: {candidate['confidence']:.3f})")
    else:
        print(f"Test audio file not found: {test_audio}")

if __name__ == "__main__":
    test_bpm_detection()