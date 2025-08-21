import numpy as np
import json
from typing import List, Dict, Tuple, Optional, Literal
from enum import Enum
import os

class QuantizeMode(Enum):
    """Quantization modes for auto-alignment"""
    QUARTER = "1/4"           # Quarter notes
    EIGHTH = "1/8"            # Eighth notes  
    SIXTEENTH = "1/16"        # Sixteenth notes
    QUARTER_SWING = "1/4+swing"      # Quarter notes with swing
    EIGHTH_SWING = "1/8+swing"       # Eighth notes with swing
    SIXTEENTH_SWING = "1/16+swing"   # Sixteenth notes with swing
    TRIPLET_QUARTER = "1/4T"  # Quarter note triplets
    TRIPLET_EIGHTH = "1/8T"   # Eighth note triplets
    OFF_GRID = "off"          # No quantization (preserve timing)

class SwingAmount(Enum):
    """Swing intensity levels"""
    LIGHT = 0.55      # Light swing (55% late)
    MEDIUM = 0.60     # Medium swing (60% late) 
    HEAVY = 0.67      # Heavy swing (67% late)
    CUSTOM = 0.0      # Custom swing amount

class AutoAligner:
    """
    Advanced auto-alignment engine for 大鼓达人 DAW annotation tool.
    
    Supports professional quantization modes including swing feel,
    triplets, and intelligent conflict resolution.
    """
    
    def __init__(self):
        self.swing_ratios = {
            SwingAmount.LIGHT: 0.55,
            SwingAmount.MEDIUM: 0.60, 
            SwingAmount.HEAVY: 0.67
        }
    
    def auto_align_annotations(
        self,
        annotations: List[Dict],
        beat_grid: Dict,
        quantize_mode: QuantizeMode = QuantizeMode.SIXTEENTH,
        swing_amount: SwingAmount = SwingAmount.MEDIUM,
        custom_swing: float = 0.60,
        tolerance: float = 0.25,
        preserve_off_beat: bool = True,
        first_measure_start: float = 0.0
    ) -> Dict:
        """
        Auto-align annotations to beat grid with various quantization options.
        
        Args:
            annotations: List of annotation objects with time, type, etc.
            beat_grid: Beat grid data from BeatGridGenerator
            quantize_mode: Quantization mode (1/4, 1/8, 1/16, swing, etc.)
            swing_amount: Swing intensity for swing modes
            custom_swing: Custom swing ratio (0.5=straight, 0.67=heavy swing)
            tolerance: Maximum distance to snap (in beat fractions)
            preserve_off_beat: Keep intentionally off-beat annotations
            first_measure_start: Offset from first measure detection
            
        Returns:
            Dictionary with aligned annotations and alignment report
        """
        try:
            print(f"[AutoAlign] Starting alignment with {quantize_mode.value} quantization")
            print(f"[AutoAlign] Processing {len(annotations)} annotations")
            
            # Get basic beat info
            bpm = beat_grid['bpm']
            beat_interval = beat_grid['beat_interval']
            tolerance_seconds = tolerance * beat_interval
            
            print(f"[AutoAlign] BPM: {bpm}, beat_interval: {beat_interval:.3f}s")
            print(f"[AutoAlign] Tolerance: {tolerance} = {tolerance_seconds:.3f}s ({tolerance_seconds*1000:.0f}ms)")
            
            # Generate quantization grid
            quant_grid = self._generate_quantization_grid(
                beat_grid, quantize_mode, swing_amount, custom_swing, first_measure_start
            )
            
            # Align annotations
            aligned_annotations = []
            alignment_stats = {
                'total_processed': 0,
                'aligned_count': 0,
                'preserved_count': 0,
                'conflicts_resolved': 0,
                'average_adjustment': 0.0,
                'max_adjustment': 0.0,
                'adjustments': [],
                'outside_tolerance_count': 0,
                'closest_distances': []
            }
            
            for annotation in annotations:
                original_time = annotation['time']
                
                # Find best alignment
                alignment_result = self._find_best_alignment(
                    original_time, quant_grid, tolerance, beat_interval
                )
                
                if alignment_result['aligned']:
                    # Create aligned annotation
                    aligned_annotation = annotation.copy()
                    aligned_annotation['time'] = alignment_result['new_time']
                    aligned_annotation['alignment_info'] = {
                        'original_time': original_time,
                        'adjustment': alignment_result['adjustment'],
                        'grid_position': alignment_result['grid_position'],
                        'quantize_mode': quantize_mode.value,
                        'confidence': alignment_result['confidence']
                    }
                    
                    aligned_annotations.append(aligned_annotation)
                    alignment_stats['aligned_count'] += 1
                    alignment_stats['adjustments'].append(abs(alignment_result['adjustment']))
                    
                elif preserve_off_beat:
                    # Preserve original timing for intentionally off-beat notes
                    preserved_annotation = annotation.copy()
                    preserved_annotation['alignment_info'] = {
                        'original_time': original_time,
                        'adjustment': 0.0,
                        'grid_position': 'off_beat',
                        'quantize_mode': 'preserved',
                        'confidence': 1.0,
                        'reason': alignment_result.get('reason', 'preserved')
                    }
                    aligned_annotations.append(preserved_annotation)
                    alignment_stats['preserved_count'] += 1
                    
                    # Track statistics for outside tolerance notes
                    if alignment_result.get('reason') == 'outside_tolerance':
                        alignment_stats['outside_tolerance_count'] += 1
                        alignment_stats['closest_distances'].append(alignment_result.get('closest_distance', 0))
                else:
                    # Skip annotation entirely if not preserving off-beat notes
                    pass
                
                alignment_stats['total_processed'] += 1
            
            # Calculate statistics
            if alignment_stats['adjustments']:
                alignment_stats['average_adjustment'] = np.mean(alignment_stats['adjustments'])
                alignment_stats['max_adjustment'] = np.max(alignment_stats['adjustments'])
            
            # Resolve conflicts (multiple annotations at same time)
            aligned_annotations = self._resolve_conflicts(aligned_annotations)
            alignment_stats['conflicts_resolved'] = len(annotations) - len(aligned_annotations)
            
            # Additional debug information
            if alignment_stats['closest_distances']:
                avg_distance = sum(alignment_stats['closest_distances']) / len(alignment_stats['closest_distances'])
                max_distance = max(alignment_stats['closest_distances'])
                print(f"[AutoAlign] Outside tolerance stats: {alignment_stats['outside_tolerance_count']} notes")
                print(f"[AutoAlign] Closest distances - avg: {avg_distance*1000:.0f}ms, max: {max_distance*1000:.0f}ms")
            
            print(f"[AutoAlign] Completed: {alignment_stats['aligned_count']} aligned, "
                  f"{alignment_stats['preserved_count']} preserved, "
                  f"{alignment_stats['conflicts_resolved']} conflicts resolved")
            
            return {
                'aligned_annotations': aligned_annotations,
                'alignment_stats': alignment_stats,
                'quantization_info': {
                    'mode': quantize_mode.value,
                    'swing_amount': swing_amount.value if swing_amount != SwingAmount.CUSTOM else custom_swing,
                    'beat_interval': beat_interval,
                    'bpm': bpm,
                    'grid_points': len(quant_grid),
                    'tolerance_seconds': tolerance * beat_interval
                }
            }
            
        except Exception as e:
            print(f"[AutoAlign] Error during alignment: {e}")
            return {
                'aligned_annotations': annotations,  # Return originals on error
                'alignment_stats': {'error': str(e)},
                'quantization_info': {'error': str(e)}
            }
    
    def _generate_quantization_grid(
        self, 
        beat_grid: Dict, 
        quantize_mode: QuantizeMode, 
        swing_amount: SwingAmount,
        custom_swing: float,
        first_measure_start: float
    ) -> List[Dict]:
        """Generate quantization grid points based on mode and swing"""
        
        beats = np.array(beat_grid['beats'])
        beat_interval = beat_grid['beat_interval']
        duration = beat_grid['duration']
        
        # Adjust beats to start from first measure
        beats = beats + first_measure_start
        print(f"[AutoAlign] Beat grid adjusted by first_measure_start: {first_measure_start:.3f}s")
        print(f"[AutoAlign] Sample beat times: {beats[:5]} (showing first 5)")
        
        grid_points = []
        
        if quantize_mode == QuantizeMode.QUARTER:
            # Quarter note grid (on beats)
            for beat_time in beats:
                if beat_time <= duration:
                    grid_points.append({
                        'time': beat_time,
                        'type': 'quarter',
                        'strength': 1.0,
                        'beat_position': 'on_beat'
                    })
        
        elif quantize_mode == QuantizeMode.EIGHTH:
            # Eighth note grid (beats + off-beats)
            for beat_time in beats:
                if beat_time <= duration:
                    # On beat
                    grid_points.append({
                        'time': beat_time,
                        'type': 'eighth_on',
                        'strength': 1.0,
                        'beat_position': 'on_beat'
                    })
                    # Off beat (halfway between beats)
                    off_beat_time = beat_time + beat_interval / 2
                    if off_beat_time <= duration:
                        grid_points.append({
                            'time': off_beat_time,
                            'type': 'eighth_off',
                            'strength': 0.7,
                            'beat_position': 'off_beat'
                        })
        
        elif quantize_mode == QuantizeMode.SIXTEENTH:
            # Sixteenth note grid
            for beat_time in beats:
                if beat_time <= duration:
                    for i in range(4):  # 4 sixteenth notes per beat
                        sixteenth_time = beat_time + (i * beat_interval / 4)
                        if sixteenth_time <= duration:
                            strength = 1.0 if i == 0 else (0.8 if i == 2 else 0.6)
                            position = 'on_beat' if i == 0 else 'subdivision'
                            
                            grid_points.append({
                                'time': sixteenth_time,
                                'type': f'sixteenth_{i}',
                                'strength': strength,
                                'beat_position': position
                            })
        
        elif quantize_mode in [QuantizeMode.EIGHTH_SWING, QuantizeMode.QUARTER_SWING, QuantizeMode.SIXTEENTH_SWING]:
            # Swing quantization
            swing_ratio = custom_swing if swing_amount == SwingAmount.CUSTOM else self.swing_ratios[swing_amount]
            
            if quantize_mode == QuantizeMode.EIGHTH_SWING:
                subdivision = 2  # Eighth notes
            elif quantize_mode == QuantizeMode.QUARTER_SWING:
                subdivision = 1  # Quarter notes
            else:  # SIXTEENTH_SWING
                subdivision = 4  # Sixteenth notes
            
            for beat_time in beats:
                if beat_time <= duration:
                    for i in range(subdivision):
                        if i % 2 == 0:
                            # Straight timing for on-beats
                            note_time = beat_time + (i * beat_interval / subdivision)
                        else:
                            # Swing timing for off-beats
                            straight_time = beat_interval / subdivision
                            swing_delay = straight_time * (swing_ratio - 0.5) * 2
                            note_time = beat_time + (i * beat_interval / subdivision) + swing_delay
                        
                        if note_time <= duration:
                            strength = 1.0 if i == 0 else 0.7
                            swing_type = 'swing_on' if i % 2 == 0 else 'swing_off'
                            
                            grid_points.append({
                                'time': note_time,
                                'type': f'{quantize_mode.value}_{i}',
                                'strength': strength,
                                'beat_position': swing_type,
                                'swing_ratio': swing_ratio
                            })
        
        elif quantize_mode == QuantizeMode.TRIPLET_EIGHTH:
            # Eighth note triplets
            for beat_time in beats:
                if beat_time <= duration:
                    for i in range(3):  # 3 triplets per beat
                        triplet_time = beat_time + (i * beat_interval / 3)
                        if triplet_time <= duration:
                            strength = 1.0 if i == 0 else 0.6
                            grid_points.append({
                                'time': triplet_time,
                                'type': f'triplet_eighth_{i}',
                                'strength': strength,
                                'beat_position': 'triplet'
                            })
        
        # Sort grid points by time
        grid_points.sort(key=lambda x: x['time'])
        
        print(f"[AutoAlign] Generated {len(grid_points)} grid points for {quantize_mode.value}")
        return grid_points
    
    def _find_best_alignment(
        self, 
        original_time: float, 
        quant_grid: List[Dict], 
        tolerance: float,
        beat_interval: float
    ) -> Dict:
        """Find the best grid point to align to"""
        
        if not quant_grid:
            return {'aligned': False, 'reason': 'empty_grid'}
        
        # Find closest grid points
        grid_times = [point['time'] for point in quant_grid]
        distances = np.abs(np.array(grid_times) - original_time)
        closest_idx = np.argmin(distances)
        closest_distance = distances[closest_idx]
        
        # Check if within tolerance
        tolerance_seconds = tolerance * beat_interval
        
        if closest_distance <= tolerance_seconds:
            closest_point = quant_grid[closest_idx]
            adjustment = closest_point['time'] - original_time
            
            # Calculate confidence based on distance and grid point strength
            distance_factor = 1.0 - (closest_distance / tolerance_seconds)
            strength_factor = closest_point['strength']
            confidence = (distance_factor * 0.7) + (strength_factor * 0.3)
            
            return {
                'aligned': True,
                'new_time': closest_point['time'],
                'adjustment': adjustment,
                'grid_position': closest_point['type'],
                'confidence': confidence,
                'original_distance': closest_distance
            }
        else:
            return {
                'aligned': False,
                'reason': 'outside_tolerance',
                'closest_distance': closest_distance,
                'tolerance': tolerance_seconds
            }
    
    def _resolve_conflicts(self, annotations: List[Dict]) -> List[Dict]:
        """Resolve conflicts when multiple annotations align to same time"""
        
        # Group by aligned time
        time_groups = {}
        for annotation in annotations:
            time_key = round(annotation['time'], 6)  # Round to microsecond precision
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(annotation)
        
        resolved_annotations = []
        
        for time_key, group in time_groups.items():
            if len(group) == 1:
                # No conflict
                resolved_annotations.append(group[0])
            else:
                # Resolve conflict
                print(f"[AutoAlign] Resolving conflict: {len(group)} annotations at {time_key:.3f}s")
                
                # Strategy 1: Keep the annotation with highest alignment confidence
                best_annotation = max(group, key=lambda x: x.get('alignment_info', {}).get('confidence', 0))
                
                # Strategy 2: Merge annotations if they're the same type
                same_type_groups = {}
                for ann in group:
                    ann_type = ann['type']
                    if ann_type not in same_type_groups:
                        same_type_groups[ann_type] = []
                    same_type_groups[ann_type].append(ann)
                
                if len(same_type_groups) == 1:
                    # All same type - keep the best one
                    resolved_annotations.append(best_annotation)
                else:
                    # Different types - keep all but slightly offset
                    for i, ann in enumerate(group):
                        if i == 0:
                            resolved_annotations.append(ann)  # Keep first at original time
                        else:
                            # Slightly offset others by small amount
                            offset_ann = ann.copy()
                            offset_ann['time'] += 0.001 * i  # 1ms per annotation
                            offset_ann['alignment_info']['conflict_resolved'] = True
                            resolved_annotations.append(offset_ann)
        
        return resolved_annotations

def create_alignment_api():
    """Create alignment API functions for the Flask server"""
    
    aligner = AutoAligner()
    
    def align_project_annotations(
        project_name: str,
        quantize_mode: str = "1/16",
        swing_amount: str = "medium", 
        custom_swing: float = 0.60,
        tolerance: float = 0.25,
        preserve_off_beat: bool = True
    ) -> Dict:
        """
        API function to align annotations for a project
        """
        try:
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
            
            # This would be called from Flask with proper paths
            # For now, return the function for integration
            return {
                'quantize_mode': quantize_enum,
                'swing_amount': swing_enum,
                'custom_swing': custom_swing,
                'tolerance': tolerance,
                'preserve_off_beat': preserve_off_beat
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    return align_project_annotations

def test_auto_alignment():
    """Test auto-alignment functionality"""
    
    # Mock beat grid data (would come from BeatGridGenerator)
    mock_beat_grid = {
        'bpm': 120.0,
        'beat_interval': 0.5,  # 500ms per beat at 120 BPM
        'duration': 10.0,
        'beats': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    }
    
    # Mock annotations (slightly off-beat)
    mock_annotations = [
        {'id': '1', 'time': 0.05, 'type': 'don', 'duration': 0.1},    # Slightly late
        {'id': '2', 'time': 0.48, 'type': 'ka', 'duration': 0.1},     # Slightly early
        {'id': '3', 'time': 1.02, 'type': 'don', 'duration': 0.1},    # Slightly late
        {'id': '4', 'time': 1.73, 'type': 'ka', 'duration': 0.1},     # Off-beat (should align to 1.75)
        {'id': '5', 'time': 2.8, 'type': 'don', 'duration': 0.1},     # Way off (should be preserved or align to 3.0)
    ]
    
    aligner = AutoAligner()
    
    # Test different quantization modes
    test_modes = [
        (QuantizeMode.QUARTER, SwingAmount.MEDIUM),
        (QuantizeMode.EIGHTH, SwingAmount.MEDIUM),
        (QuantizeMode.SIXTEENTH, SwingAmount.MEDIUM),
        (QuantizeMode.EIGHTH_SWING, SwingAmount.HEAVY),
    ]
    
    for quantize_mode, swing_amount in test_modes:
        print(f"\n=== Testing {quantize_mode.value} with {swing_amount.name} swing ===")
        
        result = aligner.auto_align_annotations(
            annotations=mock_annotations,
            beat_grid=mock_beat_grid,
            quantize_mode=quantize_mode,
            swing_amount=swing_amount,
            tolerance=0.3  # 30% of beat interval
        )
        
        print(f"Alignment Stats: {result['alignment_stats']}")
        
        for i, (original, aligned) in enumerate(zip(mock_annotations, result['aligned_annotations'])):
            adjustment = aligned['alignment_info']['adjustment']
            print(f"  Note {i+1}: {original['time']:.3f}s -> {aligned['time']:.3f}s "
                  f"(adj: {adjustment:+.3f}s, pos: {aligned['alignment_info']['grid_position']})")

if __name__ == "__main__":
    test_auto_alignment()