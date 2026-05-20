import requests
import json

def test_postseason_scoreboard():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?seasontype=3&limit=100"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            with open("postseason_scoreboard.json", "w") as f:
                json.dump(data, f, indent=4)
            print(f"Postseason data saved. Games found: {len(data.get('events', []))}")
            
            series_info = {}
            for event in data.get('events', []):
                comp = event['competitions'][0]
                if 'series' in comp:
                    summary = comp['series'].get('summary')
                    series_info[event['name']] = summary
            
            print("Unique Series found:")
            for name, summary in series_info.items():
                print(f"{name}: {summary}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_postseason_scoreboard()
