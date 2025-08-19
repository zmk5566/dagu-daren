# Beatmap Generator

This tool automatically generates a Taiko no Tatsujin beatmap from a project's drum audio track and its corresponding annotated samples.

## Workflow

The generator follows a machine learning-based approach:

1.  **Feature Extraction**: It first analyzes the annotated `don_samples` and `ka_samples` to learn the distinct acoustic features of each drum sound (e.g., spectral characteristics).
2.  **Onset Detection**: It then processes the full `drums.mp3` track to identify the precise timestamps of all drum hits (onsets).
3.  **Classification**: For each detected onset, it extracts the same acoustic features and uses a simple classifier (trained on the sample data) to determine whether the sound is a 'don' or a 'ka'.
4.  **Beatmap Generation**: Finally, it compiles the classified timestamps into the standard JSON beatmap format.

## Dependencies

- Python 3.x
- librosa
- scikit-learn
- numpy

Install the dependencies using the provided `requirements.txt`:
```bash
pip install -r beatmap_generator/requirements.txt
```

## Usage (Planned)

The script will be run from the command line, pointing to a specific project directory:

```bash
python3 beatmap_generator/generate_beatmap.py data/<project_name>
```
