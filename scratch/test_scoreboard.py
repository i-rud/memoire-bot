import requests
import json

def test_scoreboard():
    # Use current date from system 2026-04-24
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            with open("scoreboard_sample.json", "w") as f:
                json.dump(data, f, indent=4)
            print("Scoreboard data saved to scoreboard_sample.json")
            
            for event in data.get('events', []):
                comp = event['competitions'][0]
                print(f"Game: {event['name']}")
                if 'series' in comp:
                    print(f"Series: {comp['series'].get('summary')}")
                    # Look for series detail
                    print(f"Series ID: {comp['series'].get('id')}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scoreboard()
