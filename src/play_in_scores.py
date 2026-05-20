import requests
import pytz
from playwright.sync_api import sync_playwright
from datetime import datetime


class PlayInScores:
    def get_nba_results(self, date: str):
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
        try:
            data = requests.get(url).json()
            games = []

            for event in data['events']:
                status = event['status']['type']['name']
                # Берем только завершенные игры или в процессе
                if status == "STATUS_FINAL" or "STATUS" in status:
                    comp = event['competitions'][0]
                    away_team_obj = comp['competitors'][1]
                    home_team_obj = comp['competitors'][0]
                    
                    away_team = away_team_obj['team']
                    home_team = home_team_obj['team']

                    away_score = int(away_team_obj.get('score', 0))
                    home_score = int(home_team_obj.get('score', 0))

                    away_name = away_team['displayName']
                    home_name = home_team['displayName']

                    # Проверка на овертайм
                    is_ot = False
                    if len(away_team_obj.get('linescores', [])) > 4:
                        is_ot = True

                    # Play-in note
                    play_in_note = ""
                    if 'series' in comp and comp['series']:
                        play_in_note = comp['series'].get('summary', '')

                    games.append({
                        "away_full": away_name,
                        "home_full": home_name,
                        "away_logo": away_team.get('logo', ''),
                        "home_logo": home_team.get('logo', ''),
                        "away_score": away_score,
                        "home_score": home_score,
                        "is_ot": is_ot,
                        "note": play_in_note
                    })
            return games
        except Exception as e:
            print(f"Ошибка: {e}")
            return []

    def generate(self, date: str):
        all_games = self.get_nba_results(date)
        if not all_games: return "No games found"

        # Разбиваем на чанки по 4 игры (как в play_in)
        chunks = [all_games[i:i + 4] for i in range(0, len(all_games), 4)]

        try:
            dt_obj = datetime.strptime(date, "%Y%m%d")
            long_date = dt_obj.strftime("%B %d, %Y").upper()
        except:
            long_date = ""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1100, 'height': 1100})

            for idx, games in enumerate(chunks):
                html_content = f"""
                <html>
                <head>
                    <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;500;700;900&display=swap" rel="stylesheet">
                    <style>
                        :root {{
                            --bg: #f8fafc;
                            --card-bg: #f0eee9;
                            --text-main: #2b2624;
                            --text-muted: #8e8a7e;
                        }}
                        body {{
                            background-color: #f0eee9;
                            font-family: 'Unbounded', sans-serif;
                            margin: 0; padding: 0;
                            display: flex; justify-content: center;
                        }}
                        #card {{
                            background-color: #f0eee9;
                            padding: 60px 80px;
                            width: 1100px;
                            height: 1100px;
                            box-sizing: border-box;
                            display: flex;
                            flex-direction: column;
                            position: relative;
                        }}
                        .header {{ 
                            margin-bottom: 150px; 
                            width: 100%;
                            display: flex;
                            justify-content: center;
                            position: relative;
                        }}
                        .date-long {{
                            font-size: 20px;
                            font-weight: 600;
                            color: var(--text-muted);
                            text-transform: uppercase;
                            letter-spacing: 1px;
                        }}

                        .game-row {{
                            display: grid;
                            grid-template-columns: 1fr 100px 100px 40px 100px 100px 1fr;
                            align-items: center;
                            margin-bottom: 120px;
                            position: relative;
                        }}
            
                        .game-note {{
                            position: absolute;
                            top: -55px;
                            left: 0;
                            right: 0;
                            display: flex;
                            align-items: center;
                            gap: 20px;
                            font-size: 20px;
                            font-weight: 700;
                            color: #8e8a7e;
                            text-transform: uppercase;
                            letter-spacing: 3px;
                        }}
                        .game-note::before, .game-note::after {{
                            content: "";
                            height: 1px;
                            flex-grow: 1;
                            background: rgba(142, 138, 126, 0.3);
                        }}

                        .team-info {{ display: flex; flex-direction: column; gap: 4px; }}
                        .team-info.away {{ align-items: flex-end; text-align: right; }}
                        .team-info.home {{ align-items: flex-start; text-align: left; }}
                        
                        .team-name {{ font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--text-main); }}
                        
                        .logo {{ 
                            width: 70px; 
                            height: 70px; 
                            object-fit: contain;
                            margin: 0 auto;
                        }}

                        .score {{
                            font-size: 40px;
                            text-align: center;
                            font-weight: 500;
                            color: var(--text-muted);
                            letter-spacing: -2px;
                        }}
                        .score.winner {{
                            font-weight: 900;
                            color: var(--text-main);
                        }}

                        .spacer {{
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 14px;
                            font-weight: 700;
                            color: var(--text-muted);
                            text-transform: uppercase;
                        }}

                        .footer-logo {{
                            position: absolute;
                            bottom: 0px;
                            left: 0;
                            right: 0;
                            display: flex;
                            justify-content: center;
                        }}
                        .footer-logo img {{
                            width: 200px;
                            opacity: 0.9;
                        }}
                    </style>
                </head>
                <body>
                    <div id="card">
                        <div class="header">
                            <div class="date-long">{long_date}</div>
                        </div>
                        {" ".join([f'''
                            <div class="game-row">
                                <div class="game-note">{g['note']}</div>
                                <div class="team-info away">
                                    <span class="team-name">{g['away_full']}</span>
                                </div>

                                <img src="{g['away_logo']}" class="logo">

                                <div class="score away {'winner' if g['away_score'] > g['home_score'] else ''}">
                                    {g['away_score']}
                                </div>

                                <div class="spacer">{'OT' if g.get('is_ot') else ''}</div>

                                <div class="score home {'winner' if g['home_score'] > g['away_score'] else ''}">
                                    {g['home_score']}
                                </div>

                                <img src="{g['home_logo']}" class="logo">

                                <div class="team-info home">
                                    <span class="team-name">{g['home_full']}</span>
                                </div>
                            </div>
                        ''' for g in games])}

                        <div class="footer-logo">
                            <img src="https://i.ibb.co/JjQQV6qN/tg-image-799289939.png">
                        </div>
                    </div>
                </body>
                </html>
                """
                page.set_content(html_content)
                page.wait_for_load_state("networkidle")
                card = page.query_selector("#card")
                if card:
                    suffix = f"_{idx + 1}" if len(chunks) > 1 else ""
                    import os
                    if not os.path.exists("images/scores"):
                        os.makedirs("images/scores")
                    card.screenshot(path=f"images/scores/nba_playin_results{suffix}.png")
                    print(f"Готово! Результаты Play-In (часть {idx + 1}) сохранены.")
            
            browser.close()
        return "Success"


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else "20260414"
    PlayInScores().generate(date)
