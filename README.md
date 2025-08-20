# 大鼓达人 (Da Gu Da Ren)

韩炳哲是我兄弟

## 项目咪表 Project Goal

解放力比多其实并不重要，解放享乐才重要。可是享乐已经享了，难道还能回到过去？难道你还记得过去？

我们在平面上游走，我们是平面的陷阱。其实也没有什么陷阱，毕竟还是享乐。但是也没有那么简单 当然也没有那么复杂。

------ 以下都不是我写的 都是AI写的 但是我保证上面儿都是我写的 ---------


The core idea is to develop a fully automated pipeline:
1.  **Input**: A standard audio file (e.g., MP3).
2.  **Processing**: The system separates the drum track from the song, analyzes it to detect individual drum hits, and classifies them.
3.  **Output**: A JSON-based beatmap file and various backing tracks for gameplay.
4.  **Gameplay**: A front-end application that loads the beatmap and audio, presenting an interactive rhythm game to the user.

## Current Progress

We are currently in the **Phase 1: Audio Processing and Asset Generation**.

- **[✓] Beatmap Format**: A clear and extensible JSON format for defining beatmaps has been designed and documented. (See `data/beatmap_format_guide.md`)
- **[✓] Audio Separation Workflow**: We are using tools to separate songs into their core components (drums, bass, vocals, etc.).
- **[✓] Automated Backing Track Generation**: An automated script (`scripts/create_backing_tracks.sh`) has been created to:
    - Generate multiple versions of the song's backing track (e.g., without drums, with low-volume drums).
    - Isolate and convert the drum track into a clean `drums.mp3` for analysis.

## Next Steps

The next major phase is **Phase 2: Beatmap Generation and Gameplay**.

1.  **Drum Beat Analysis**:
    - Implement an algorithm to analyze the `drums.mp3` file.
    - Detect the precise timing of each drum hit (onset detection).
    - Classify each hit as either a "don" (center) or "ka" (rim) hit.
2.  **Automatic Beatmap Creation**:
    - Create a script that takes the analysis results and generates a valid `.json` beatmap file.
3.  **Frontend Development**:
    - Build the game interface using HTML, CSS, and JavaScript.
    - Synchronize the scrolling notes with the backing track.
    - Implement the input and judgment system for scoring player performance.
