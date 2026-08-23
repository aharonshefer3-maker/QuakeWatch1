import redis
import os
import time
import json
from db_connect import r

# טעינת משתני סביבה בלבד (ללא שום ערכים קשיחים)

SEED_FILE_PATH = os.getenv('SEED_FILE_PATH', 'config.json')




def run_external_seed():
    system_key = "quakewatch:system:info"

    if not r.exists(system_key):
        print(f"Redis is empty. Loading seed from external file: {SEED_FILE_PATH}...")

        # קריאת קובץ ה-JSON החיצוני
        with open(SEED_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # שתילת מידע כללי (Hash)
        if "system_info" in data:
            r.hset(system_key, mapping=data["system_info"])

        # שתילת תחנות (Set)
        if "stations" in data and data["stations"]:
            r.sadd("quakewatch:stations:list", *data["stations"])

        # שתילת אירועים (List)
        if "recent_events" in data:
            for event in data["recent_events"]:
                r.rpush("quakewatch:recent:events", event)

        print("External seed data inserted successfully!")
    else:
        print("Seed already exists in Redis, skipping.")


if __name__ == "__main__":
    run_external_seed()