import numpy as np
import librosa
import os
from typing import Tuple, List, Dict, Optional

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
        
    def detect_bpm(self, audio_path: str) -> Dict:
        """
        Detect BPM using multiple algorithms and return the most confident result.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with BPM, confidence score, and beat times
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=self.sr)
            print(f"[BPM] Loaded audio: {os.path.basename(audio_path)} ({len(y)/sr:.1f}s)")
            
            # Method 1: Tempo detection with onset envelope
            tempo_onset = self._detect_tempo_onset(y, sr)
            
            # Method 2: Beat tracking approach
            tempo_beat = self._detect_tempo_beat_tracking(y, sr)
            
            # Method 3: Spectral centroid periodicity
            tempo_spectral = self._detect_tempo_spectral(y, sr)
            
            # Combine results and select most confident
            candidates = [tempo_onset, tempo_beat, tempo_spectral]
            best_result = max(candidates, key=lambda x: x['confidence'])
            
            # Generate precise beat times using the best BPM
            beat_times = self._generate_beat_times(y, sr, best_result['bpm'])
            
            result = {
                'bpm': round(best_result['bpm'], 2),
                'confidence': round(best_result['confidence'], 3),
                'beat_times': beat_times.tolist(),
                'method_used': best_result['method'],
                'all_candidates': candidates
            }
            
            print(f"[BPM] Detected: {result['bpm']} BPM (confidence: {result['confidence']:.3f})")
            return result
            
        except Exception as e:
            print(f"[BPM] Error detecting BPM: {e}")
            return {
                'bpm': 120.0,  # Fallback BPM
                'confidence': 0.0,
                'beat_times': [],
                'method_used': 'fallback',
                'error': str(e)
            }
    
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
                'method': 'onset_envelope'
            }
        except Exception as e:
            print(f"[BPM] Onset method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method': 'onset_envelope'}
    
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
                'method': 'beat_tracking'
            }
        except Exception as e:
            print(f"[BPM] Beat tracking method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method': 'beat_tracking'}
    
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
                'method': 'spectral_periodicity'
            }
        except Exception as e:
            print(f"[BPM] Spectral method failed: {e}")
            return {'bpm': 120.0, 'confidence': 0.0, 'method': 'spectral_periodicity'}
    
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
            print(f"{candidate['method']}: {candidate['bpm']:.2f} BPM (conf: {candidate['confidence']:.3f})")
    else:
        print(f"Test audio file not found: {test_audio}")

if __name__ == "__main__":
    test_bpm_detection()