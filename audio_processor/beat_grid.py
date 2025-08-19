import numpy as np
import librosa
from typing import List, Dict, Tuple, Optional

try:
    from .bpm_detector import BPMDetector
except ImportError:
    from bpm_detector import BPMDetector

class BeatGridGenerator:
    """
    Beat grid generator for 大鼓达人 DAW-style annotation tool.
    
    Generates precise beat grids with subdivisions, measures, and downbeat detection.
    """
    
    def __init__(self, time_signature: Tuple[int, int] = (4, 4)):
        """
        Initialize beat grid generator.
        
        Args:
            time_signature: (numerator, denominator) e.g., (4, 4) for 4/4 time
        """
        self.time_signature = time_signature
        self.bpm_detector = BPMDetector()
        
    def generate_beat_grid(self, audio_path: str, bpm_override: Optional[float] = None) -> Dict:
        """
        Generate complete beat grid for audio file.
        
        Args:
            audio_path: Path to audio file
            bpm_override: Optional manual BPM override
            
        Returns:
            Dictionary with beat grid data
        """
        try:
            # Load audio for duration calculation
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            
            # Get BPM
            if bpm_override:
                bpm = bpm_override
                confidence = 1.0  # User override is always confident
                print(f"[BeatGrid] Using manual BPM: {bpm}")
            else:
                bpm_result = self.bpm_detector.detect_bpm(audio_path)
                bpm = bpm_result['bpm']
                confidence = bpm_result['confidence']
                print(f"[BeatGrid] Using detected BPM: {bpm} (confidence: {confidence:.3f})")
            
            # Generate beat positions
            beats = self._generate_beats(bpm, duration)
            
            # Generate subdivisions
            subdivisions = self._generate_subdivisions(beats, bpm)
            
            # Generate measures
            measures = self._generate_measures(beats)
            
            # Detect downbeats
            downbeats = self._detect_downbeats(beats)
            
            # Calculate grid metadata
            beat_interval = 60.0 / bpm
            beats_per_measure = self.time_signature[0]
            
            result = {
                'bpm': bpm,
                'confidence': confidence,
                'time_signature': self.time_signature,
                'duration': duration,
                'beat_interval': beat_interval,
                'beats_per_measure': beats_per_measure,
                'beats': beats.tolist(),
                'measures': measures,
                'downbeats': downbeats.tolist(),
                'subdivisions': subdivisions,
                'grid_metadata': {
                    'total_beats': len(beats),
                    'total_measures': len(measures),
                    'quarter_note_interval': beat_interval,
                    'eighth_note_interval': beat_interval / 2,
                    'sixteenth_note_interval': beat_interval / 4
                }
            }
            
            print(f"[BeatGrid] Generated grid: {len(beats)} beats, {len(measures)} measures")
            return result
            
        except Exception as e:
            print(f"[BeatGrid] Error generating beat grid: {e}")
            # Return minimal fallback grid
            return self._fallback_grid(120.0, 60.0)  # 60 second fallback
    
    def _generate_beats(self, bpm: float, duration: float) -> np.ndarray:
        """Generate regular beat positions based on BPM"""
        beat_interval = 60.0 / bpm
        num_beats = int(duration / beat_interval) + 1
        return np.arange(0, num_beats * beat_interval, beat_interval)
    
    def _generate_subdivisions(self, beats: np.ndarray, bpm: float) -> Dict:
        """Generate subdivision grids (eighth notes, sixteenth notes, etc.)"""
        beat_interval = 60.0 / bpm
        
        # Eighth notes (subdivide each beat in half)
        eighth_notes = []
        for beat in beats:
            eighth_notes.extend([beat, beat + beat_interval / 2])
        
        # Sixteenth notes (subdivide each beat in quarters)
        sixteenth_notes = []
        for beat in beats:
            for i in range(4):
                sixteenth_notes.append(beat + i * beat_interval / 4)
        
        # Triplets (subdivide each beat in thirds)
        triplets = []
        for beat in beats:
            for i in range(3):
                triplets.append(beat + i * beat_interval / 3)
        
        return {
            'eighth_notes': sorted(eighth_notes),
            'sixteenth_notes': sorted(sixteenth_notes),
            'triplets': sorted(triplets)
        }
    
    def _generate_measures(self, beats: np.ndarray) -> List[Dict]:
        """Generate measure boundaries based on time signature"""
        measures = []
        beats_per_measure = self.time_signature[0]
        
        for i in range(0, len(beats), beats_per_measure):
            if i + beats_per_measure <= len(beats):
                measure_start = beats[i]
                measure_end = beats[i + beats_per_measure - 1]
                
                measures.append({
                    'number': len(measures) + 1,
                    'start_time': float(measure_start),
                    'end_time': float(measure_end),
                    'beat_indices': list(range(i, i + beats_per_measure)),
                    'beats_in_measure': [float(beats[j]) for j in range(i, min(i + beats_per_measure, len(beats)))]
                })
        
        return measures
    
    def _detect_downbeats(self, beats: np.ndarray) -> np.ndarray:
        """Detect downbeats (first beat of each measure)"""
        beats_per_measure = self.time_signature[0]
        downbeat_indices = range(0, len(beats), beats_per_measure)
        return beats[list(downbeat_indices)]
    
    def _fallback_grid(self, bpm: float, duration: float) -> Dict:
        """Generate fallback grid when detection fails"""
        beats = self._generate_beats(bpm, duration)
        measures = self._generate_measures(beats)
        downbeats = self._detect_downbeats(beats)
        subdivisions = self._generate_subdivisions(beats, bpm)
        
        return {
            'bpm': bpm,
            'confidence': 0.0,
            'time_signature': self.time_signature,
            'duration': duration,
            'beat_interval': 60.0 / bpm,
            'beats_per_measure': self.time_signature[0],
            'beats': beats.tolist(),
            'measures': measures,
            'downbeats': downbeats.tolist(),
            'subdivisions': subdivisions,
            'grid_metadata': {
                'total_beats': len(beats),
                'total_measures': len(measures),
                'quarter_note_interval': 60.0 / bpm,
                'eighth_note_interval': 30.0 / bpm,
                'sixteenth_note_interval': 15.0 / bpm
            }
        }

class AdvancedBeatAnalyzer:
    """
    Advanced beat analysis for complex musical structures.
    """
    
    def __init__(self):
        self.beat_grid = BeatGridGenerator()
    
    def analyze_beat_strength(self, audio_path: str, beat_times: List[float]) -> List[Dict]:
        """
        Analyze the strength/intensity of each beat.
        
        Returns list of beat analysis with confidence scores.
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            
            # Get onset strength
            onset_envelope = librosa.onset.onset_strength(y=y, sr=sr)
            onset_times = librosa.frames_to_time(
                range(len(onset_envelope)), sr=sr
            )
            
            beat_analysis = []
            
            for i, beat_time in enumerate(beat_times):
                # Find closest onset strength value
                closest_idx = np.argmin(np.abs(onset_times - beat_time))
                strength = float(onset_envelope[closest_idx])
                
                # Determine beat type based on position in measure
                beats_per_measure = self.beat_grid.time_signature[0]
                beat_in_measure = (i % beats_per_measure) + 1
                
                # Classify beat strength
                if beat_in_measure == 1:
                    beat_type = "downbeat"
                    expected_strength = "strong"
                elif beat_in_measure == 3 and beats_per_measure == 4:
                    beat_type = "backbeat"
                    expected_strength = "medium"
                else:
                    beat_type = "upbeat"
                    expected_strength = "weak"
                
                beat_analysis.append({
                    'time': beat_time,
                    'strength': strength,
                    'beat_in_measure': beat_in_measure,
                    'beat_type': beat_type,
                    'expected_strength': expected_strength,
                    'index': i
                })
            
            return beat_analysis
            
        except Exception as e:
            print(f"[BeatAnalyzer] Error analyzing beat strength: {e}")
            return []
    
    def detect_tempo_changes(self, audio_path: str, window_size: float = 8.0) -> List[Dict]:
        """
        Detect tempo changes throughout the track.
        
        Args:
            audio_path: Path to audio file
            window_size: Analysis window size in seconds
            
        Returns:
            List of tempo change points
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            
            tempo_changes = []
            detector = BPMDetector()
            
            # Analyze tempo in overlapping windows
            overlap = 0.5  # 50% overlap
            step_size = window_size * (1 - overlap)
            
            for start_time in np.arange(0, duration - window_size, step_size):
                end_time = min(start_time + window_size, duration)
                
                # Extract audio window
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                window_audio = y[start_sample:end_sample]
                
                # Detect BPM in this window
                # (This would need a modified version of BPMDetector for audio arrays)
                # For now, we'll use a simplified approach
                
                tempo_changes.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'bpm': 120.0,  # Placeholder - would be actual detection
                    'confidence': 0.5
                })
            
            return tempo_changes
            
        except Exception as e:
            print(f"[BeatAnalyzer] Error detecting tempo changes: {e}")
            return []

def test_beat_grid():
    """Test beat grid generation"""
    generator = BeatGridGenerator()
    analyzer = AdvancedBeatAnalyzer()
    
    test_audio = "/Users/k/Documents/GitHub/taigu-online-practice/data/xwx-backtrack-n-drum/generated_audio/drums.mp3"
    
    if os.path.exists(test_audio):
        print(f"Testing beat grid generation on: {test_audio}")
        
        # Generate beat grid
        grid = generator.generate_beat_grid(test_audio)
        
        print(f"\n=== Beat Grid Results ===")
        print(f"BPM: {grid['bpm']}")
        print(f"Time Signature: {grid['time_signature']}")
        print(f"Total Beats: {grid['grid_metadata']['total_beats']}")
        print(f"Total Measures: {grid['grid_metadata']['total_measures']}")
        print(f"Beat Interval: {grid['beat_interval']:.3f}s")
        
        # Show first few beats and measures
        print(f"\nFirst 10 beats: {grid['beats'][:10]}")
        print(f"First 3 measures:")
        for measure in grid['measures'][:3]:
            print(f"  Measure {measure['number']}: {measure['start_time']:.2f}s - {measure['end_time']:.2f}s")
        
        # Test beat analysis
        beat_analysis = analyzer.analyze_beat_strength(test_audio, grid['beats'][:20])
        print(f"\nBeat strength analysis (first 20 beats):")
        for analysis in beat_analysis[:5]:
            print(f"  Beat {analysis['index']}: {analysis['strength']:.3f} ({analysis['beat_type']})")
            
    else:
        print(f"Test audio file not found: {test_audio}")

if __name__ == "__main__":
    import os
    test_beat_grid()