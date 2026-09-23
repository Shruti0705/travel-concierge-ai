#!/usr/bin/env python3
"""Seed script for Firestore database destinations collection."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-af3d95e43a89"

DESTINATIONS = [
    {
        "id": "san-francisco",
        "name": "San Francisco",
        "country": "USA",
        "category": "City & Bay",
        "budget_level": "moderate",
        "highlights": [
            "Golden Gate Bridge",
            "Fisherman's Wharf",
            "Alcatraz Island",
            "Cable Cars",
        ],
        "recommended_days": 3,
        "description": "Famous for iconic bridges, foggy bay views, Victorian houses, and vibrant culinary scenes.",
    },
    {
        "id": "kyoto",
        "name": "Kyoto",
        "country": "Japan",
        "category": "Culture & Heritage",
        "budget_level": "moderate",
        "highlights": [
            "Fushimi Inari Shrine",
            "Arashiyama Bamboo Grove",
            "Kinkaku-ji",
            "Gion District",
        ],
        "recommended_days": 4,
        "description": "Historical heart of Japan with serene shrines, traditional tea houses, and stunning cherry blossoms.",
    },
    {
        "id": "barcelona",
        "name": "Barcelona",
        "country": "Spain",
        "category": "Coastal & Architecture",
        "budget_level": "budget",
        "highlights": [
            "La Sagrada Familia",
            "Park Güell",
            "Gothic Quarter",
            "Barceloneta Beach",
        ],
        "recommended_days": 3,
        "description": "Mediterranean jewel renowned for Antoni Gaudí architecture, tapas culture, and sunny beaches.",
    },
    {
        "id": "paris",
        "name": "Paris",
        "country": "France",
        "category": "Arts & Gastronomy",
        "budget_level": "luxury",
        "highlights": [
            "Eiffel Tower",
            "Louvre Museum",
            "Notre-Dame Cathedral",
            "Champs-Élysées",
        ],
        "recommended_days": 4,
        "description": "The City of Light, famous for romance, art museums, world-class gastronomy, and fashion.",
    },
]


def seed_database():
    """Seeds the Firestore 'destinations' collection with sample data."""
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")

    for dest in DESTINATIONS:
        doc_id = dest["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(dest)
        print(f"Seeded destination: {dest['name']} ({doc_id})")

    print(
        f"\n✅ Firestore collection 'destinations' successfully seeded in project '{PROJECT_ID}'!"
    )


if __name__ == "__main__":
    seed_database()
