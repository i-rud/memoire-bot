import requests
import pytz
from playwright.sync_api import sync_playwright
from datetime import datetime


class Schedule:
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
            team_stats = self._get_team_stats()
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

                # Достаем доп статку
                a_stats = team_stats.get(away_name, {"streak": "-", "l10": "0-0"})
                h_stats = team_stats.get(home_name, {"streak": "-", "l10": "0-0"})

                games.append({
                    "away_full": away_name,
                    "home_full": home_name,
                    "away_logo": away_team.get('logo', ''),
                    "home_logo": home_team.get('logo', ''),
                    "away_record": comp['competitors'][1].get('records', [{}])[0].get('summary', ''),
                    "home_record": comp['competitors'][0].get('records', [{}])[0].get('summary', ''),
                    "away_streak": a_stats['streak'],
                    "away_l10": a_stats['l10'],
                    "home_streak": h_stats['streak'],
                    "home_l10": h_stats['l10'],
                    "time": dt_moscow.strftime("%H:%M"),
                    "date": dt_moscow.strftime("%d.%m")
                })
            return games
        except Exception as e:
            print(f"Ошибка: {e}")
            return []


    def generate(self, date: str):
        all_games = self.get_nba_data(date)
        if not all_games: return

        # Разбиваем на чанки по 6 игр
        chunks = [all_games[i:i + 6] for i in range(0, len(all_games), 6)]

        # Парсим дату для заголовка (ожидаем YYYYMMDD)
        try:
            dt_obj = datetime.strptime(date, "%Y%m%d")
            formatted_date = dt_obj.strftime("%d/%m")
            long_date = dt_obj.strftime("%B %d, %Y").upper()
        except:
            formatted_date = ""
            long_date = ""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Квадратный вьюпорт
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
                        }}
            
                        .header {{ 
                            margin-bottom: 70px; 
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
                            margin-bottom: 60px;
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
                        .stats-row {{
                            display: flex;
                            gap: 24px;
                            align-items: flex-start;
                            margin-top: 4px;
                        }}
                        .team.away .stats-row {{ flex-direction: row-reverse; }}
        
                        .stat-col {{
                            display: flex;
                            flex-direction: column;
                            gap: 4px;
                        }}
                        .team.away .stat-col {{ align-items: flex-end; }}
                        .team.home .stat-col {{ align-items: flex-start; }}
        
                        .stat-value {{
                            font-size: 18px;
                            font-weight: 700;
                            color: #2b2624;
                            line-height: 1;
                        }}
                        .stat-label {{
                            font-size: 10px;
                            font-weight: 700;
                            color: #8e8a7e;
                            text-transform: uppercase;
                            letter-spacing: 1px;
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
                    </style>
                </head>
                <body>
                    <div id="card">
                        <div class="header">
                            <div class="date-long">{long_date}</div>
                        </div>
                        {" ".join([f'''
                            <div class="game-row">
                                <div class="team away">
                                    <div class="team-info">
                                        <span class="team-name">{g['away_full']}</span>
                                        <div class="stats-row">
                                            <div class="stat-col">
                                                <span class="stat-value">{g['away_record']}</span>
                                                <span class="stat-label">W-L</span>
                                            </div>
                                            <div class="stat-col">
                                                <span class="stat-value">{g['away_l10']}</span>
                                                <span class="stat-label">L10</span>
                                            </div>
                                            <div class="stat-col">
                                                <span class="stat-value">{g['away_streak']}</span>
                                                <span class="stat-label">STRK</span>
                                            </div>
                                        </div>
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
                                        <div class="stats-row">
                                            <div class="stat-col">
                                                <span class="stat-value">{g['home_record']}</span>
                                                <span class="stat-label">W-L</span>
                                            </div>
                                            <div class="stat-col">
                                                <span class="stat-value">{g['home_l10']}</span>
                                                <span class="stat-label">L10</span>
                                            </div>
                                            <div class="stat-col">
                                                <span class="stat-value">{g['home_streak']}</span>
                                                <span class="stat-label">STRK</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ''' for g in games])}
                    </div>
                </body>
                </html>
                """
                page.set_content(html_content)
                page.wait_for_load_state("networkidle")
                card = page.query_selector("#card")
                if card:
                    suffix = f"_{idx + 1}" if len(chunks) > 1 else ""
                    card.screenshot(path=f"images/schedule/nba_memoire_schedule{suffix}.png")
                    print(f"Готово! Расписание (часть {idx + 1}) сохранено. Игр: {len(games)}")

            browser.close()
