# Audio Processor Backend

This directory contains the Python Flask server responsible for clipping audio samples based on the data provided by the frontend annotation tool.

## Setup

1.  **Install Dependencies**: It is highly recommended to use a virtual environment.

    ```bash
    # Create and activate a virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install the required packages
    pip install -r requirements.txt
    ```

2.  **Run the Server**:

    ```bash
    python3 server.py
    ```

The server will start on `http://127.0.0.1:5001`. The annotator tool will send requests to this endpoint.
