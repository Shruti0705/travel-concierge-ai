# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from google.cloud import firestore, storage

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-02-af3d95e43a89")
loc_env = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east1")
LOCATION = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION") or ("us-east1" if loc_env == "global" else loc_env)
MEMORY_BANK_ID = os.getenv("MEMORY_BANK_ID", "8090622172571107328")
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-af3d95e43a89"
GCS_BUCKET_NAME = "travel-concierge-assets-qwiklabs-gcp-02-af3d95e43a89"


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to extract and persist memories."""
    await callback_context.add_session_to_memory()
    return None


def get_live_weather(city: str) -> str:
    """Fetches real-time live weather forecasts for any city worldwide using Open-Meteo.

    Args:
        city: The name of the city (e.g. 'Kyoto', 'Paris', 'San Francisco').

    Returns:
        A string describing current live temperature in °C and °F, weather condition, and wind speed.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "TravelConciergeAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            geo_data = json.loads(response.read().decode())

        results = geo_data.get("results", [])
        if not results:
            return f"Could not find coordinates for city: '{city}'."

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        country = results[0].get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req2 = urllib.request.Request(weather_url, headers={"User-Agent": "TravelConciergeAgent/1.0"})
        with urllib.request.urlopen(req2, timeout=5) as response2:
            weather_data = json.loads(response2.read().decode())

        current = weather_data.get("current_weather", {})
        temp_c = current.get("temperature", "N/A")
        temp_f = round(temp_c * 9 / 5 + 32, 1) if isinstance(temp_c, (int, float)) else "N/A"
        windspeed = current.get("windspeed", "N/A")

        return (
            f"Live Weather for {city} ({country}):\n"
            f"- Temperature: {temp_c}°C ({temp_f}°F)\n"
            f"- Wind Speed: {windspeed} km/h"
        )
    except Exception as e:
        return f"Error fetching weather for {city}: {str(e)}"


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> str:
    """Converts a monetary amount from one currency to another using live exchange rates.

    Args:
        amount: The numeric amount to convert (e.g. 100.0).
        from_currency: 3-letter currency code to convert from (e.g. 'USD', 'EUR', 'GBP').
        to_currency: 3-letter currency code to convert to (e.g. 'JPY', 'EUR', 'CAD').

    Returns:
        A summary string showing the converted amount and live exchange rate.
    """
    try:
        from_curr = from_currency.upper().strip()
        to_curr = to_currency.upper().strip()
        url = f"https://open.er-api.com/v6/latest/{from_curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "TravelConciergeAgent/1.0"})

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        rates = data.get("rates", {})
        if to_curr not in rates:
            return f"Unsupported target currency code: '{to_curr}'. Available codes include: JPY, EUR, GBP, CAD, AUD."

        rate = rates[to_curr]
        converted = amount * rate
        return (
            f"Currency Conversion:\n"
            f"- {amount:,.2f} {from_curr} = {converted:,.2f} {to_curr}\n"
            f"- Live Exchange Rate: 1 {from_curr} = {rate:,.4f} {to_curr}"
        )
    except Exception as e:
        return f"Error performing currency conversion: {str(e)}"


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def search_destinations(query: str = "", category: str = "") -> str:
    """Searches travel destinations stored in the Firestore database.

    Args:
        query: Optional text query to match against destination names, countries, or descriptions.
        category: Optional category filter (e.g. 'Beach & Coastal', 'Culture & History', 'Food & Wine', 'Nature').

    Returns:
        A summary string listing matching travel destinations and their details.
    """
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    docs = db.collection("destinations").stream()
    results = []
    query_lower = query.lower() if query else ""
    category_lower = category.lower() if category else ""

    for doc in docs:
        data = doc.to_dict()
        name = data.get("name", "")
        country = data.get("country", "")
        cat = data.get("category", "")
        desc = data.get("description", "")
        budget = data.get("budget_level", "")
        highlights = ", ".join(data.get("highlights", []))

        match_category = not category_lower or category_lower in cat.lower()
        match_query = not query_lower or (
            query_lower in name.lower()
            or query_lower in country.lower()
            or query_lower in desc.lower()
            or query_lower in highlights.lower()
        )

        if match_category and match_query:
            results.append(
                f"- Document ID: {doc.id}\n"
                f"  Name: {name} ({country})\n"
                f"  Category: {cat} | Budget: {budget}\n"
                f"  Highlights: {highlights}\n"
                f"  Description: {desc}"
            )

    if not results:
        return f"No destinations found matching query='{query}' and category='{category}'."

    return "Found matching destinations:\n\n" + "\n\n".join(results)


def add_destination(
    name: str,
    country: str,
    category: str,
    budget_level: str,
    highlights: str,
    description: str,
) -> str:
    """Adds or updates a travel destination in the Firestore database.

    Args:
        name: Name of the destination (e.g. 'Kyoto').
        country: Country where destination is located (e.g. 'Japan').
        category: Destination category (e.g. 'Culture & History', 'Beach & Coastal').
        budget_level: Budget tier (e.g. '$', '$$', '$$$', '$$$$').
        highlights: Comma-separated list of key highlights or attractions.
        description: A brief summary of what makes the destination special.

    Returns:
        Confirmation message with document ID.
    """
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    doc_id = name.lower().replace(" ", "-")
    highlights_list = [h.strip() for h in highlights.split(",") if h.strip()]

    doc_data = {
        "name": name,
        "country": country,
        "category": category,
        "budget_level": budget_level,
        "highlights": highlights_list,
        "description": description,
    }

    db.collection("destinations").document(doc_id).set(doc_data)
    return f"Successfully saved destination '{name}' to Firestore with ID '{doc_id}'."


def get_public_holidays(country_code: str = "US", year: int = 2026) -> str:
    """Fetches official public holidays for a destination country (from Nager.Date Public API).

    Args:
        country_code: 2-letter ISO country code (e.g. 'JP', 'US', 'FR', 'ES', 'GB').
        year: 4-digit calendar year (e.g. 2026).

    Returns:
        A list of upcoming public holidays with dates and names to assist with trip planning.
    """
    try:
        cc = country_code.upper().strip()
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{cc}"

        # Reads API key from environment variable if configured
        api_key = os.getenv("PUBLIC_HOLIDAYS_API_KEY") or os.getenv("NAGER_DATE_API_KEY")
        headers = {"User-Agent": "TravelConciergeAgent/1.0"}
        if api_key:
            headers["X-API-Key"] = api_key

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        if not data:
            return f"No public holidays found for country code '{cc}' in year {year}."

        formatted_holidays = [
            f"- {h.get('date')}: {h.get('name')} ({h.get('localName')})"
            for h in data[:10]
        ]
        return f"Public Holidays for {cc} ({year}):\n" + "\n".join(formatted_holidays)
    except Exception as e:
        return f"Error fetching public holidays for {country_code}: {str(e)}"


def geocode_address(address: str) -> str:
    """Converts an address or location name into geographic coordinates (latitude and longitude).

    Args:
        address: The address or place name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Kyoto Station').

    Returns:
        A formatted string with the address, latitude, longitude, and location status.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    try:
        encoded_address = urllib.parse.quote(address.strip())
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "TravelConciergeAgent/1.0"})

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        status = data.get("status")
        if status != "OK" or not data.get("results"):
            return f"Could not geocode address '{address}'. Status: {status}"

        result = data["results"][0]
        formatted_address = result.get("formatted_address", address)
        location = result.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        return (
            f"Geocoding Result:\n"
            f"- Address: {formatted_address}\n"
            f"- Location: ({lat}, {lng})"
        )
    except Exception as e:
        return f"Error during geocoding: {str(e)}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 500.0,
) -> str:
    """Finds nearby points of interest or places of a given type around coordinates using Places API (New).

    Args:
        latitude: Latitude coordinate (e.g. 37.7749 or 35.0037).
        longitude: Longitude coordinate (e.g. -122.4194 or 135.7772).
        place_type: Type of place to search for (e.g. 'restaurant', 'tourist_attraction', 'cafe', 'museum').
        radius_meters: Search radius in meters (default is 500.0).

    Returns:
        A list of nearby places including name, formatted address, and coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
            "User-Agent": "TravelConciergeAgent/1.0",
        }
        payload = {
            "includedTypes": [place_type.strip().lower()],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        places = data.get("places", [])
        if not places:
            return f"No nearby places found of type '{place_type}' within {radius_meters}m of ({latitude}, {longitude})."

        results = []
        for p in places:
            display_name = p.get("displayName", {}).get("text", "Unknown Name")
            address = p.get("formattedAddress", "N/A")
            loc = p.get("location", {})
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            results.append(
                f"- Name: {display_name}\n"
                f"  Address: {address}\n"
                f"  Location: ({lat}, {lng})"
            )

        return f"Nearby Places ({place_type}):\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Error finding nearby places: {str(e)}"


async def generate_destination_image(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates an image for a travel destination or attraction using gemini-3.1-flash-lite-image in global region.

    Args:
        prompt: Description of the travel destination image to generate (e.g. 'Kyoto Bamboo Forest in morning light' or 'Eiffel Tower at sunset').
        tool_context: Tool context injected by ADK to save session artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated image.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        image_bytes = None
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    break

        if not image_bytes:
            return f"Error: No image bytes generated for prompt '{prompt}'."

        filename = f"destination_{uuid.uuid4().hex[:8]}.jpg"

        # (1) Save artifact in session context
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload image bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket("travel-concierge-assets-qwiklabs-gcp-02-af3d95e43a89")
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/travel-concierge-assets-qwiklabs-gcp-02-af3d95e43a89/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating destination image: {str(e)}"


async def generate_destination_video(
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates a short video for a travel destination or landmark using Google's Omni model (gemini-omni-flash-preview) in global region.

    Args:
        prompt: Description of the travel destination video to generate (e.g. 'Kyoto Bamboo Forest in morning light' or 'Eiffel Tower at sunset').
        tool_context: Tool context injected by ADK to save session artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated video.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global",
        )
        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            if getattr(interaction.output_video, "data", None):
                video_bytes = base64.b64decode(interaction.output_video.data)

        if not video_bytes:
            return f"Error: No video bytes generated for prompt '{prompt}'."

        filename = f"destination_{uuid.uuid4().hex[:8]}.mp4"

        # (1) Save artifact in session context
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket("travel-concierge-assets-qwiklabs-gcp-02-af3d95e43a89")
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/travel-concierge-assets-qwiklabs-gcp-02-af3d95e43a89/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating destination video: {str(e)}"



def memory_bank_service_builder():
    """Builds and returns the Vertex AI Memory Bank service instance."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


import threading
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback


class PicklableAgentEngineSandboxCodeExecutor(AgentEngineSandboxCodeExecutor):
    """Subclass of AgentEngineSandboxCodeExecutor that properly handles pickle serialization for cloud deployment."""

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_agent_engine_creation_lock"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._agent_engine_creation_lock = threading.Lock()


AGENT_ENGINE_RESOURCE_NAME = os.getenv(
    "AGENT_ENGINE_RESOURCE_NAME",
    f"projects/255199647468/locations/us-east1/reasoningEngines/2408205342736384000",
)

code_executor = PicklableAgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a helpful travel concierge AI assistant. You must always pay strict attention to "
        "and remember all user-stated allergies (such as food, peanut, gluten, dairy, seafood, "
        "or environmental/medication allergies) and dietary restrictions across all conversations. "
        "Always confirm and strictly honor all remembered user allergies when making any dining, "
        "activity, or travel recommendations."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    tools=[
        PreloadMemoryTool(),
        get_live_weather,
        convert_currency,
        get_public_holidays,
        geocode_address,
        find_nearby_places,
        generate_destination_image,
        generate_destination_video,
        get_current_time,
        search_destinations,
        add_destination,
    ],
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

