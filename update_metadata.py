#!/usr/bin/env python3
"""
Script to update all existing song metadata files to include category and difficulty fields.
"""

import os
import json
import sys
from pathlib import Path

def update_metadata_file(metadata_path):
    """Update a single metadata.json file to include category and difficulty fields."""
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if fields already exist
        if 'category' in metadata and 'difficulty' in metadata:
            print(f"✓ {metadata_path} already has category and difficulty fields")
            return True
            
        # Add category and difficulty fields with reasonable defaults
        # Assign categories based on song characteristics or defaults
        display_name = metadata.get('display_name', '').lower()
        
        # Simple heuristic to assign categories based on song names
        if any(word in display_name for word in ['pop', 'jpop', 'kpop']):
            category = 'Pop'
        elif any(word in display_name for word in ['trance', 'electronic', 'edm']):
            category = 'Trance'  
        elif any(word in display_name for word in ['brutal', 'metal', 'hard', 'extreme']):
            category = 'Brutal'
        elif any(word in display_name for word in ['soft', 'calm', 'gentle', 'peaceful']):
            category = 'Softcore'
        else:
            # Default to Pop for most songs
            category = 'Pop'
            
        # Assign difficulty based on BPM and complexity (rough heuristic)
        bpm = metadata.get('bpm_data', {}).get('bpm', 120)
        if bpm < 100:
            difficulty = 3  # Slow songs tend to be easier
        elif bpm < 130:
            difficulty = 5  # Medium tempo
        elif bpm < 160:
            difficulty = 7  # Fast tempo
        else:
            difficulty = 8  # Very fast songs are harder
            
        # Add the new fields
        metadata['category'] = category
        metadata['difficulty'] = difficulty
        
        # Update last_updated timestamp
        import time
        metadata['last_updated'] = time.time()
        
        # Write updated metadata back to file
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
            
        print(f"✓ Updated {metadata_path} - Category: {category}, Difficulty: {difficulty}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating {metadata_path}: {e}")
        return False

def main():
    # Find the data directory
    data_dir = Path(__file__).parent / 'data'
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        sys.exit(1)
        
    print(f"Updating metadata files in: {data_dir}")
    print("=" * 60)
    
    updated_count = 0
    error_count = 0
    
    # Find all metadata.json files
    for metadata_path in data_dir.glob('*/metadata.json'):
        if update_metadata_file(metadata_path):
            updated_count += 1
        else:
            error_count += 1
            
    print("=" * 60)
    print(f"Summary: {updated_count} files updated successfully, {error_count} errors")
    
    if error_count > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()