# Audio Processor Backend

This directory contains a self-contained web application for audio annotation. The Python Flask server handles both the backend audio clipping and serves the frontend annotator tool.

## The New Simplified Workflow

1.  **Run the Server**: Start the Python server from your project's root directory.
2.  **Open Your Browser**: Navigate to `http://1227.0.0.1:5001`. The annotation tool will be loaded directly.
3.  **Annotate & Export**: Use the tool as before. When you click "Send to Server", the data is sent to the same server that is hosting the page, which then handles the audio clipping automatically.

## Setup Instructions

1.  **Use a Virtual Environment (Highly Recommended)**
    From the project root, create and activate a virtual environment:
    ```bash
    python3 -m venv audio_processor/venv
    source audio_processor/venv/bin/activate
    ```

2.  **Install Dependencies**
    Ensure your virtual environment is active, then install the required packages:
    ```bash
    pip install -r audio_processor/requirements.txt
    ```

3.  **Run the Application**
    From the **project root directory**, run the following command. This will start the server and make the annotator available in your browser.
    ```bash
    python3 audio_processor/server.py
    ```

Now, just open `http://127.0.0.1:5001` in your web browser to begin.
