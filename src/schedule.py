import requests
import pytz
from playwright.sync_api import sync_playwright
from datetime import datetime


class Schedule:
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

                # 1. Парсим строку времени и указываем, что это UTC
                dt_utc = datetime.strptime(event['date'], "%Y-%m-%dT%H:%MZ")
                dt_utc = utc_zone.localize(dt_utc)

                # 2. Конвертируем в Московское время
                dt_moscow = dt_utc.astimezone(moscow_zone)

                games.append({
                    "away_full": away_team['displayName'],
                    "home_full": home_team['displayName'],
                    "away_logo": away_team['logo'],
                    "home_logo": home_team['logo'],
                    # Теперь берем время и дату из сконвертированного объекта
                    "time": dt_moscow.strftime("%H:%M"),
                    "date": dt_moscow.strftime("%d.%m")
                })
            return games
        except Exception as e:
            print(f"Ошибка: {e}")
            return []


    def generate(self, date: str):
        games = self.get_nba_data(date)
        if not games: return

        html_content = f"""
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;500;700&display=swap" rel="stylesheet">
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
                    width: 1000px; /* Увеличил ширину для большего расстояния */
                    box-sizing: border-box;
                }}
    
                .game-row {{
                    display: grid;
                    /* Увеличил центральную колонку до 180px для "воздуха" вокруг времени */
                    grid-template-columns: 1fr 180px 1fr;
                    align-items: center;
                    margin-bottom: 40px;
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
    
                .team img {{ width: 60px; height: 60px; }}
    
                .time-box {{
                    background-color: #e6e2d6;
                    color: #8e8a7e;
                    padding: 10px 0;
                    border-radius: 12px;
                    text-align: center;
                    font-size: 20px;
                    font-weight: 500;
                    /* margin здесь создает дополнительный отступ от команд */
                    margin: 0 40px;
                }}
                
    
                .footer {{
                    text-align: center;
                    margin-top: 60px;
                    color: #8e8a7e;
                    font-size: 16px;
                    letter-spacing: 10px;
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div id="card">
                {" ".join([f'''
                <div class="game-row">
                    <div class="team away">
                        <span>{g['away_full']}</span>
                        <img src="{g['away_logo']}">
                    </div>
                    <div class="time-box">
                        {g['time']}
                        <span style="font-size:14px;">MCK</span>
                    </div>
                    <div class="team home">
                        <img src="{g['home_logo']}">
                        <span>{g['home_full']}</span>
                    </div>
                </div>
                ''' for g in games])}
            </div>
        </body>
        </html>
        """

        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Задаем большой вьюпорт, чтобы ничего не резалось
            page = browser.new_page(viewport={'width': 1200, 'height': 1800})
            page.set_content(html_content)

            # Ожидание загрузки ресурсов (логотипов)
            page.wait_for_load_state("networkidle")

            card = page.query_selector("#card")
            if card:
                card.screenshot(path="images/schedule/nba_memoire_schedule.png")
                print(f"Готово! Скриншот сохранен. Игр в списке: {len(games)}")

            browser.close()
