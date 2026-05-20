import requests
import pytz
from playwright.sync_api import sync_playwright
from datetime import datetime


class PlayInSchedule:
    def _get_team_stats(self):
        try:
            url = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
            response = requests.get(url).json()
            stats_lookup = {}
            for group in response.get('children', []):
                for entry in group['standings']['entries']:
                    team_full_name = entry['team']['displayName']
                    stats = {s['name']: s['displayValue'] for s in entry['stats']}
                    l10 = stats.get('lastTenGamesRecord', stats.get('Last Ten Games', '0-0'))
                    streak = stats.get('streak', '-')
                    stats_lookup[team_full_name] = {
                        "streak": streak,
                        "l10": l10
                    }
            return stats_lookup
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}

    def get_nba_data(self, date: str):
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
        try:
            data = requests.get(url).json()
            games = []

            # Определяем часовые пояса
            utc_zone = pytz.utc
            moscow_zone = pytz.timezone('Europe/Moscow')

            for event in data['events']:
                comp = event['competitions'][0]
                away_team = comp['competitors'][1]['team']
                home_team = comp['competitors'][0]['team']

                away_name = away_team['displayName']
                home_name = home_team['displayName']

                # 1. Парсим строку времени и указываем, что это UTC
                dt_utc = datetime.strptime(event['date'], "%Y-%m-%dT%H:%MZ")
                dt_utc = utc_zone.localize(dt_utc)

                # 2. Конвертируем в Московское время
                dt_moscow = dt_utc.astimezone(moscow_zone)

                # Play-in note
                play_in_note = ""
                if 'series' in comp and comp['series']:
                    play_in_note = comp['series'].get('summary', '')

                games.append({
                    "away_full": away_name,
                    "home_full": home_name,
                    "away_logo": away_team.get('logo', ''),
                    "home_logo": home_team.get('logo', ''),
                    "time": dt_moscow.strftime("%H:%M"),
                    "date": dt_moscow.strftime("%d.%m"),
                    "note": play_in_note
                })
            return games
        except Exception as e:
            print(f"Ошибка: {e}")
            return []


    def generate(self, date: str):
        all_games = self.get_nba_data(date)
        if not all_games: return

        # Разбиваем на чанки
        chunks = [all_games[i:i + 4] for i in range(0, len(all_games), 4)]

        # Парсим дату
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
                                --accent: #263D52;
                                --radius: 32px;
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
                            grid-template-columns: 1fr 180px 1fr;
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
            
                        .team {{ 
                            display: flex; 
                            align-items: center; 
                            gap: 25px; 
                            font-size: 24px; 
                            font-weight: 500; 
                            color: #2b2624; 
                        }}
                        .team.away {{ justify-content: flex-end; text-align: right; }}
                        .team.home {{ justify-content: flex-start; text-align: left; }}
            
                        .team img {{ width: 70px; height: 70px; }}
        
                        .team-info {{
                            display: flex;
                            flex-direction: column;
                            gap: 6px;
                        }}
                        .team.away .team-info {{
                          align-items: flex-end;
                        }}
                        .team.home .team-info {{
                            align-items: flex-start;
                        }}
                        .team-name {{
                            font-size: 24px;
                            font-weight: 700;
                            color: #2b2624;
                        }}
            
                        .time-box {{
                            color: var(--text-muted);
                            padding: 10px 0;
                            border-radius: 12px;
                            text-align: center;
                            font-size: 24px;
                            font-weight: 700;
                            margin: 0 40px;
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
                                <div class="team away">
                                    <div class="team-info">
                                        <span class="team-name">{g['away_full']}</span>
                                    </div>
                                    <img src="{g['away_logo']}">
                                </div>
                                <div class="time-box">
                                    {g['time']}
                                    <div style="font-size:14px; font-weight:400; margin-top: 2px;">MCK</div>
                                </div>
                                <div class="team home">
                                    <img src="{g['home_logo']}">
                                    <div class="team-info">
                                        <span class="team-name">{g['home_full']}</span>
                                    </div>
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
                    if not os.path.exists("images/schedule"):
                        os.makedirs("images/schedule")
                    card.screenshot(path=f"images/schedule/nba_playin_schedule{suffix}.png")
                    print(f"Готово! Play-In Расписание (часть {idx + 1}) сохранено. Игр: {len(games)}")

            browser.close()


if __name__ == "__main__":
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else "20260414"
    PlayInSchedule().generate(date)
