import requests
import json
from datetime import datetime

date = "20260425"
api_base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
url = f"{api_base}/scoreboard?dates={date}"

try:
    resp = requests.get(url).json()
    events = resp.get('events', [])
    print(f"Found {len(events)} events for {date}")
    for event in events:
        comp = event['competitions'][0]
        round_info = comp.get('type', {})
        print(f"Game: {event['name']}")
        print(f"Round Type: {json.dumps(round_info, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
