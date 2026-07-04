# Techathon 2026 - Smart Office Monitoring System

## Problem Statement Understanding
Modern offices consume a significant amount of electricity due to devices (lights, fans, ACs) being left on when not in use. The challenge for the Techathon Nationals 2026 Hackathon is to build a smart office monitoring system that can track the status and power consumption of various devices across different rooms in real-time. The system must consist of a backend to serve data, a web dashboard for live monitoring, and a Discord bot with AI capabilities to interact with the system conversationally.

## Solution Approach and Architecture
Our solution, developed by Team Holmes, is composed of three decoupled components:
1.  **Shared Backend API & Simulation:** A FastAPI-based REST server that maintains the single source of truth for the office. It simulates 15 devices across 3 rooms ("Drawing Room", "Work Room 1", "Work Room 2"), randomly toggling their states to mimic real office activity.
2.  **Real-Time Web Dashboard:** A vanilla HTML/CSS/JS frontend that polls the backend API to display live device statuses, total and per-room power consumption, and active anomalies (e.g., devices left on for an extended period). It features a modern dark-mode UI with CSS animations for active devices.
3.  **Discord Bot:** A Python bot built with `discord.py` that allows users to query office status via chat commands (`!status`, `!room`, `!usage`). It integrates with the Google Gemini LLM API to format raw JSON data into friendly, conversational responses.

## Technologies Used
-   **Backend:** Python 3, FastAPI, Uvicorn (ASGI server)
-   **Frontend:** HTML5, CSS3, Vanilla JavaScript (Fetch API)
-   **Discord Bot:** Python 3, `discord.py`, `aiohttp`
-   **AI Integration:** Google Gemini (`google-generativeai`)

## Setup and Installation Instructions

### Prerequisites
-   Python 3.9+
-   A Discord Bot Token
-   A Google Gemini API Key

### Installation
1.  Clone this repository or navigate to the `Techathon2026-Holmes` directory.
2.  Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file in the `bot` directory with your API keys:
    ```env
    DISCORD_BOT_TOKEN=your_discord_token_here
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

### Running the Servers Locally
1.  **Start the Backend API:**
    ```bash
    python -m uvicorn backend.main:app --reload
    ```
    The API will be available at `http://localhost:8000`.

2.  **View the Web Dashboard:**
    Simply open the `frontend/index.html` file in your preferred web browser. It will automatically connect to the local API on port 8000.

3.  **Start the Discord Bot:**
    In a separate terminal, run:
    ```bash
    python bot/bot.py
    ```

## API Endpoints Documentation
The backend exposes the following REST API endpoints:
-   `GET /api/status`: Returns the current ON/OFF status, power draw, and last changed timestamp for all devices, grouped by room.
-   `GET /api/usage/total`: Returns the total live power draw (in Watts) across the entire office and an estimated daily usage (kWh).
-   `GET /api/usage/rooms`: Returns the power consumption broken down by room.
-   `GET /api/anomalies`: Returns a list of devices that have been ON for longer than the defined threshold (e.g., 2 hours).

## AI Integration Details
The Discord bot utilizes the **Google Gemini LLM** to enhance user interaction. Instead of returning a raw JSON dump or a rigid text format when a user runs a command like `!status` or `!usage`, the bot fetches the live data from the FastAPI backend and sends it as context to Gemini. 
The LLM is prompted to act as a helpful office assistant, summarizing the data in a natural, friendly, and conversational tone, making the bot feel more human-like and accessible for non-technical office staff.
