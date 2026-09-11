# SecureSense Prototype

SecureSense is an AI-powered real-time detection and prevention system for voice-cloning impersonation attacks. This repository contains both the frontend UI and the Python FastAPI backend.

## Quick Start Guide

Follow these simple steps to set up and run the project on your local machine.

### 1. Prerequisites
Ensure you have the following installed on your computer:
- [Python 3.10+](https://www.python.org/downloads/)
- A modern web browser (Chrome, Edge, Firefox, Safari)

### 2. Set Up the Backend
The backend uses Python and FastAPI. It includes machine learning and audio processing libraries, so we recommend using a virtual environment.

Open your terminal or command prompt in the project root (`SIH/`) and run these commands:

#### Create and activate a virtual environment (Optional but recommended)
**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```
**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Install dependencies
```cmd
pip install -r backend/requirements.txt
```
*(Note: If you run into issues installing audio libraries, ensure you have the latest version of `pip` by running `python -m pip install --upgrade pip` first).*

### 3. Run the Backend Server
Once the dependencies are installed, you can start the backend API server.

**On Windows:**
Simply double-click the `run_backend.bat` file in the project folder, or run it from the command line:
```cmd
run_backend.bat
```

**On macOS/Linux:**
```bash
python -m uvicorn backend.main:app --reload
```

The backend API will start running at `http://localhost:8000`. You can view the automatic API documentation by visiting `http://localhost:8000/docs` in your browser.

### 4. Run the Frontend UI
The frontend is built with pure HTML, CSS, and JavaScript. You do not need a special build tool or framework to view it.

Simply double-click on any of the HTML files to open them in your web browser:
- `index.html` - The login page
- `dashboard.html` - The main dashboard
- `call-check.html` - The active call analysis interface

---

## Troubleshooting

- **Audio Processing Errors:** If the backend fails to process audio, make sure `librosa` and `scipy` are properly installed. You can manually install them via `pip install librosa scipy`.
- **Database Missing Errors:** The database functionality is currently mocked out for testing. If you see database connection errors, they are safe to ignore for UI/Integration testing purposes.
