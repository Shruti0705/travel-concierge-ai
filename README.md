# Travel Concierge AI Agent

An intelligent, multi-tool AI travel concierge built with the Google Agent Development Kit (ADK) and deployed to Vertex AI Agent Runtime. It assists users with trip planning, destination discovery, live weather forecasts, currency conversions, public holiday schedules, nearby point-of-interest searches, and generative destination artwork and videos.

![Travel Concierge AI Demo](./demo.gif)

---

## 🌟 What the Agent Does

The Travel Concierge AI Agent processes natural language requests to help users plan trips while remembering dietary restrictions and personal preferences across chat sessions using Vertex AI Memory Bank. It renders responses in plain text as well as rich, structured A2UI cards.

### Core Capabilities & Tools Implemented

- **🧠 Persistent Memory (Vertex AI Memory Bank)**: Automatically extracts and remembers user allergies (e.g. food, peanut, gluten, dairy) and travel preferences across turns using `VertexAiMemoryBankService` and ADK memory callbacks.
- **🗺️ Destination Database (Google Cloud Firestore)**: Queries and updates the `destinations` Firestore collection (`search_destinations`, `add_destination`) by country, category, budget level, and highlights.
- **📍 Location & Nearby Places (Google Maps & Places API)**: Converts addresses to geographical coordinates (`geocode_address`) and finds nearby points of interest (`find_nearby_places`) using Google Places API (New).
- **🌦️ Live Weather Forecasts (Open-Meteo API)**: Fetches real-time temperature, wind speed, and weather code conditions (`get_live_weather`) for any destination.
- **💰 Real-Time Currency Conversion (Frankfurt API)**: Converts monetary amounts between global currencies (`convert_currency`).
- **📅 Public Holidays Lookup (Nager.Date API)**: Retrieves official public holiday schedules (`get_public_holidays`) for any country code and calendar year.
- **🎨 AI Image Generation (Vertex AI Imagen)**: Generates destination photos and artwork (`generate_destination_image`) using `gemini-3.1-flash-lite-image` in the `global` region, uploading image bytes directly to Google Cloud Storage.
- **🎬 AI Video Generation (Google GenAI Omni Model)**: Generates short 3-second destination videos (`generate_destination_video`) using `gemini-omni-flash-preview` in the `global` region via the Google GenAI Interactions API, saving session artifacts and uploading video bytes to Google Cloud Storage.
- **📱 Agent-Driven UI (A2UI v0.8)**: Uses `A2uiSchemaManager` (version 0.8) and `a2ui_callback` to emit structured A2UI components (`Card`, `Column`, `Row`, `Text`, `Image`, `Icon`) alongside standard text responses over the Agent-to-Agent (A2A) protocol.

---

## ☁️ Google Cloud Services & Integrations

Based on `app/` and `agents-cli-manifest.yaml`, the project is wired to the following GCP infrastructure:

- **Vertex AI Agent Runtime (Reasoning Engine)**: Hosts the agent backend (`deployment_target: agent_runtime`).
- **Vertex AI Memory Bank**: Stores long-term user memory embeddings.
- **Google Cloud Firestore**: Persists travel destination documents and metadata.
- **Google Cloud Storage (GCS)**: Stores generated destination images and MP4 video assets.
- **Google Vertex AI GenAI SDK**: Powering `Gemini`, Imagen, and Omni multimodal model calls.
- **Google Maps Platform (Places API)**: Powers geocoding and nearby place lookups.

---

## 🏗️ Project Architecture

```
travel-concierge-agent/
├── app/
│   ├── agent.py               # Main ADK Agent, tools, Memory Bank, and A2UI prompt setup
│   ├── a2ui_utils.py          # A2UI model callback & A2A datapart wrapper
│   └── __init__.py
├── frontend/
│   ├── main.py                # FastAPI proxy connecting web browser to deployed Agent A2A API
│   ├── static/
│   │   └── index.html         # Custom Ocean Teal frontend UI with A2UI renderer, hero banner & prompt chips
│   └── requirements.txt
├── demo.gif                   # Looping walkthrough recording
├── agents-cli-manifest.yaml   # Manifest for agents-cli deployment configuration
├── pyproject.toml             # Python dependencies and package setup
└── GEMINI.md                  # Development guide and context rules
```

---

## 🚀 Local Setup & Running Instructions

### Prerequisites

- **Python 3.11+**
- **uv** (Fast Python package manager)
- **google-agents-cli**: Installed via `uv tool install google-agents-cli`
- **Google Cloud SDK (`gcloud`)**: Authenticated with application default credentials (`gcloud auth application-default login`)

### 1. Install Dependencies

```bash
uv pip install -e .
```

### 2. Configure Environment Variables

Set the required environment variables in your terminal:

```bash
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="us-east1"
export GOOGLE_GENAI_USE_VERTEXAI="true"
export GOOGLE_MAPS_API_KEY="<YOUR_GOOGLE_MAPS_API_KEY>"
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/us-east1/reasoningEngines/<RESOURCE_ID>"
export AGENT_DIRECTORY="app"
```

### 3. Run the Local ADK Developer Playground

To test agent logic, trace tool calls, and inspect Memory Bank states locally:

```bash
uv run adk web --memory_service_uri=agentengine://<MEMORY_BANK_ID> --port 8085 --allow_origins "*" --reload_agents
```

### 4. Run the Web Frontend Proxy & Chat Interface

To launch the web proxy and custom chat UI locally:

```bash
cd frontend
uv run python main.py
```

Open a web browser to the configured local port (default: `http://localhost:8080`).

---

## 📦 Deployment & Publishing Commands

### Deploy to Vertex AI Agent Runtime

```bash
agents-cli deploy --deployment-target agent_runtime --project <YOUR_GCP_PROJECT_ID> --region us-east1
```

### Deploy Frontend Web Proxy to Cloud Run

```bash
gcloud run deploy travel-concierge-frontend \
  --source ./frontend \
  --region us-east1 \
  --project <YOUR_GCP_PROJECT_ID> \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<RESOURCE_NAME>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
