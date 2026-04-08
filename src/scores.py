import requests
import pytz
from playwright.sync_api import sync_playwright
from datetime import datetime


class Scores:
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

    def get_nba_results(self, date: str):
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}"
        try:
            data = requests.get(url).json()
            team_stats = self._get_team_stats()
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

                    a_stats = team_stats.get(away_name, {"streak": "-", "l10": "0-0"})
                    h_stats = team_stats.get(home_name, {"streak": "-", "l10": "0-0"})

                    # Проверка на овертайм (количество периодов > 4)
                    is_ot = False
                    if len(away_team_obj.get('linescores', [])) > 4:
                        is_ot = True

                    games.append({
                        "away_full": away_name,
                        "home_full": home_name,
                        "away_logo": away_team.get('logo', ''),
                        "home_logo": home_team.get('logo', ''),
                        "away_record": away_team_obj.get('records', [{}])[0].get('summary', ''),
                        "home_record": home_team_obj.get('records', [{}])[0].get('summary', ''),
                        "away_score": away_score,
                        "home_score": home_score,
                        "away_streak": a_stats['streak'],
                        "away_l10": a_stats['l10'],
                        "home_streak": h_stats['streak'],
                        "home_l10": h_stats['l10'],
                        "is_ot": is_ot
                    })
            return games
        except Exception as e:
            print(f"Ошибка: {e}")
            return []

    def generate(self, date: str):
        all_games = self.get_nba_results(date)
        if not all_games: return "No games found"

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
                            grid-template-columns: 1fr 100px 100px 40px 100px 100px 1fr;
                            align-items: center;
                            margin-bottom: 60px;
                        }}
            
                        .team-info {{ display: flex; flex-direction: column; gap: 4px; }}
                        .team-info.away {{ align-items: flex-end; text-align: right; }}
                        .team-info.home {{ align-items: flex-start; text-align: left; }}
                        
                        .team-name {{ font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--text-main); }}
                        
                        .stats-row {{ display: flex; gap: 10px; align-items: flex-start; margin-top: 6px; }}
                        .team-info.away .stats-row {{ flex-direction: row-reverse; }}

                        .stat-col {{ 
                            display: flex; 
                            flex-direction: column; 
                            gap: 2px; 
                            align-items: center; 
                            min-width: 60px;
                        }}

                        .stat-value {{ font-size: 16px; font-weight: 700; color: var(--text-main); line-height: 1; }}
                        .stat-label {{ font-size: 9px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.2px; }}

                        .spacer {{
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 14px;
                            font-weight: 700;
                            color: var(--text-muted);
                            text-transform: uppercase;
                        }}

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
                    </style>
                </head>
                <body>
                    <div id="card">
                        <div class="header">
                            <div class="date-long">{long_date}</div>
                        </div>
                        {" ".join([f'''
                            <div class="game-row">
                                <div class="team-info away">
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
                    card.screenshot(path=f"images/scores/nba_results_summary{suffix}.png")
                    print(f"Готово! Результаты (часть {idx + 1}) сохранены.")
            
            browser.close()
        return "Success"