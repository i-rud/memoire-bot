import requests
import json

def test_scoreboard_range():
    # April 15 to April 24, 2026
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20260415-20260425&limit=100"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"Games found in range: {len(data.get('events', []))}")
            
            series_info = {}
            for event in data.get('events', []):
                comp = event['competitions'][0]
                if 'series' in comp:
                    summary = comp['series'].get('summary')
                    series_info[event['name']] = summary
            
            print("Unique Series found:")
            for name, summary in sorted(series_info.items()):
                print(f"{name}: {summary}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scoreboard_range()
