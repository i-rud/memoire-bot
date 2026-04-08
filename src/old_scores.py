import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from playwright.sync_api import sync_playwright

API_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
OUTPUT_DIR = "images/old_scores"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


class Scores:
    def __init__(self):
        pass

    def generate_html(self, summary):
        header = summary.get('header', {})
        comp = header.get('competitions', [{}])[0]
        date_str = header.get('competitions', [{}])[0].get('date', '')
        
        utc_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
        date_display = et_dt.strftime("%B %d, %Y")

        home = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
        away = next(t for t in comp['competitors'] if t['homeAway'] == 'away')

        def get_team_info(comp_obj):
            team = comp_obj['team']
            return {
                'logo': team['logos'][0]['href'] if team.get('logos') else "",
                'score': comp_obj.get('score', '0'),
                'abbrev': team.get('abbreviation', '')
            }

        home_info = get_team_info(home)
        away_info = get_team_info(away)
        
        home_score_val = int(home_info['score']) if home_info['score'].isdigit() else 0
        away_score_val = int(away_info['score']) if away_info['score'].isdigit() else 0
        h_lose_class = "is-loser" if home_score_val < away_score_val else ""
        a_lose_class = "is-loser" if away_score_val < home_score_val else ""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;500;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --card-bg: #f0eee9; --text-main: #2b2624; --text-muted: #8e8a7e;
                    --radius: 20px;
                }}
                * {{ box-sizing: border-box; }}
                body {{ font-family: 'Unbounded', sans-serif; background: transparent; display: flex; justify-content: center; align-items: center; margin: 0; padding: 40px; }}
                .match-card {{ background: var(--card-bg); width: 1700px; padding: 60px; position: relative; }}
                
                .date-header {{ text-align: center; color: var(--text-muted); font-size: 18px; font-weight: 700; margin-bottom: 60px; text-transform: uppercase; letter-spacing: 0.3em; }}
                
                .scoreboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; margin-bottom: 100px; position: relative; }}
                .team {{ display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }}
                .team-name {{ font-size: 22px; font-weight: 700; color: var(--text-muted); margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px; }}
                .logo-wrapper {{ position: relative; width: 300px; height: 300px; border-radius: 60px; display: flex; justify-content: center; align-items: center; margin-bottom: 40px; }}
                .team-logo-main {{ width: 210px; height: 210px; object-fit: contain; }}
                
                .score-wrapper {{ display: flex; align-items: center; justify-content: center; width: 100%; }}
                .score {{ font-size: 160px; font-weight: 800; color: var(--text-main); line-height: 0.9; transition: all 0.3s ease; letter-spacing: -8px; }}
                .team.is-loser .score {{ opacity: 0.3; }}
                
                .vs-divider {{ position: absolute; left: 50%; top: 40%; transform: translate(-50%, -50%); font-size: 80px; font-weight: 900; color: #e6e2d6; margin: 0; letter-spacing: -2px; }}
                
                .columns-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 80px; }}
                .players-list {{ width: max-content; margin: 0 auto; }}

                .player-entry {{ display: flex; align-items: center; gap: 25px; margin-bottom: 40px; }}
                .headshot-container {{ width: 140px; height: 140px; border-radius: 50%; background: #e6e2d6; overflow: hidden; flex-shrink: 0; }}
                .headshot-container img {{ width: 100%; height: 100%; object-fit: cover; object-position: top; }}
                
                .player-info {{ flex-grow: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }}
                .name-line {{ display: flex; align-items: center; gap: 15px; font-size: 32px; font-weight: 700; color: var(--text-main); }}
                .player-name {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
                .score-badge {{ background: var(--score-bg); color: #fff; padding: 8px 12px; border-radius: 10px; font-size: 28px; font-weight: 500; line-height: 1; display: flex; align-items: center; justify-content: center; }}
                
                .stats-row {{ display: flex; gap: 15px; align-items: baseline; margin-top: 5px; flex-wrap: wrap; }}
                .mini-stat {{ display: flex; align-items: baseline; gap: 5px; }}
                .mini-stat .val {{ font-size: 36px; font-weight: 900; color: var(--text-main); line-height: 1; letter-spacing: 0px; }}
                .mini-stat .lbl {{ font-size: 16px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }}
            </style>
        </head>
        <body>
            <div class="match-card">
                <div class="date-header">{date_display}</div>
                
                <div class="scoreboard">
                    <div class="team {h_lose_class}">
                        <div class="team-name">{home_info['abbrev']}</div>
                        <div class="logo-wrapper">
                            <img src="{home_info['logo']}" class="team-logo-main">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{home_info['score']}</div>
                        </div>
                    </div>
                    
                    <div class="vs-divider">VS</div>

                    <div class="team {a_lose_class}">
                        <div class="team-name">{away_info['abbrev']}</div>
                        <div class="logo-wrapper">
                            <img src="{away_info['logo']}" class="team-logo-main">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{away_info['score']}</div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def generate(self, date: str):
        scoreboard = requests.get(f"{API_BASE}/scoreboard?dates={date}").json()
        events = scoreboard.get('events', [])
        
        summary_list = []

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1600, 'height': 2000})

            for i, event in enumerate(events):
                game_id = event['id']
                print(f"Fetching summary for game {game_id}...")
                summary = requests.get(f"{API_BASE}/summary?event={game_id}").json()
                
                if not summary.get('boxscore', {}).get('teams'): continue
                
                summary_list.append(summary)
                
                html_content = self.generate_html(summary)
                page.set_content(html_content)
                page.wait_for_timeout(1000)

                card = page.query_selector(".match-card")
                if card:
                    card.screenshot(path=f"{OUTPUT_DIR}/match_{i + 1}.png", scale="device")
                    print(f"Match {i + 1} image saved.")

            browser.close()

        return "No games processed."

# if __name__ == "__main__":
#     main()