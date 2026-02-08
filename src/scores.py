import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from playwright.sync_api import sync_playwright

API_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"
OUTPUT_DIR = "images/scores"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


class Scores:
    def __init__(self):
        pass

    def generate_html(self, event):
        comp = event['competitions'][0]

        utc_dt = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
        et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))

        date_display = et_dt.strftime("%B %d, %Y")

        home = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
        away = next(t for t in comp['competitors'] if t['homeAway'] == 'away')

        home_score = home['score']
        away_score = away['score']

        home_win = int(home_score) > int(away_score)
        away_win = int(away_score) > int(home_score)

        STAT_LEFT_COLOR = "#263D52"
        STAT_RIGHT_COLOR = "#A63A2F"

        h_ls, a_ls = home.get('linescores', []), away.get('linescores', [])
        num_p = max(len(h_ls), len(a_ls), 4)
        thead, h_row, a_row = [], [], []

        for i in range(num_p):
            label = (
                f"{i + 1}ST" if i == 0 else f"{i + 1}ND" if i == 1 else f"{i + 1}RD" if i == 2 else "4TH") if i < 4 else (
                f"OT{i - 3}" if num_p > 5 else "OT")
            thead.append(f"<th>{label}</th>")
            h_row.append(f"<td>{int(h_ls[i]['value']) if i < len(h_ls) else '-'}</td>")
            a_row.append(f"<td>{int(a_ls[i]['value']) if i < len(a_ls) else '-'}</td>")

        def get_full_stat(team, type_prefix):
            stats = {s['name']: s['displayValue'] for s in team.get('statistics', [])}

            mapping = {
                'fg': ('fieldGoalPct', 'fieldGoalsMade', 'fieldGoalsAttempted'),
                '3p': ('threePointPct', 'threePointFieldGoalsMade', 'threePointFieldGoalsAttempted'),
                'ft': ('freeThrowPct', 'freeThrowsMade', 'freeThrowsAttempted')
            }

            pct_key, made_key, att_key = mapping[type_prefix]

            pct = stats.get(pct_key, "0")
            made = stats.get(made_key, "0")
            att = stats.get(att_key, "0")

            m_a_string = stats.get(f"{made_key}-{att_key}", f"{made}/{att}")
            if "/" not in m_a_string and "-" in m_a_string:
                m_a_string = m_a_string.replace("-", "/")

            return f"{pct}%", f"({m_a_string})"

        h_fg_p, h_fg_m = get_full_stat(home, 'fg')
        a_fg_p, a_fg_m = get_full_stat(away, 'fg')
        h_3p_p, h_3p_m = get_full_stat(home, '3p')
        a_3p_p, a_3p_m = get_full_stat(away, '3p')
        h_ft_p, h_ft_m = get_full_stat(home, 'ft')
        a_ft_p, a_ft_m = get_full_stat(away, 'ft')

        # Лидеры
        def get_leader_info(team):
            try:
                # 1. Ищем категорию 'rating' среди лидеров
                rating_category = next((c for c in team['leaders'] if c['name'] == 'rating'), None)

                # Если рейтинга нет, берем первую категорию (например, points) как запасную
                cat = rating_category if rating_category else team['leaders'][0]

                leader = cat['leaders'][0]
                athlete = leader['athlete']

                # 2. Возвращаем только displayValue этого лидера (например, "32.5")
                return {
                    "name": athlete['displayName'],
                    "headshot": athlete.get('headshot', ''),
                    "stats": leader.get('displayValue', 'N/A'),
                }
            except Exception as e:
                # Печатаем ошибку для отладки, если что-то пошло не так в структуре JSON
                print(f"Error parsing leader: {e}")
                return {"name": "N/A", "headshot": "", "stats": "N/A", "rating": "N/A"}

        h_l, a_l = get_leader_info(home), get_leader_info(away)

        h_lose_class = "is-loser" if not home_win else ""
        a_lose_class = "is-loser" if not away_win else ""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;500;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --stat-left: {STAT_LEFT_COLOR}; --stat-right: {STAT_RIGHT_COLOR};
                    --card-bg: #f0eee9; --text-main: #2b2624; --text-muted: #8e8a7e;
                    --gold: #336659; --radius-xl: 40px; --radius-lg: 30px;
                }}
                body {{ font-family: 'Unbounded', sans-serif; background: transparent; display: flex; justify-content: center; align-items: center; margin: 0; padding: 40px; }}
                .match-card {{ background: var(--card-bg); width: 800px; box-shadow: 0 30px 80px rgba(0,0,0,0.1); padding: 50px; box-sizing: border-box; }}
                .card-header {{ text-align: center; color: var(--text-muted); font-size: 11px; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 0.3em; }}
                .scoreboard {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 60px; }}
                .team-name {{ font-weight: 500; font-size: 13px; color: var(--text-muted); margin-bottom: 12px; }}
                .team {{ display: flex; flex-direction: column; align-items: center; flex: 1; }}
                .logo-wrapper {{ position: relative; background: #e6e2d6; width: 160px; height: 160px; border-radius: var(--radius-lg); display: flex; justify-content: center; align-items: center; margin-bottom: 24px; }}
                .team-logo {{ width: 100px; height: 100px; object-fit: contain; }}
                .winner-badge {{ position: absolute; top: -12px; right: -12px; background: var(--gold); color: white; width: 36px; height: 36px; border-radius: 14px; display: flex; justify-content: center; align-items: center; font-size: 10px; border: 4px solid #fff; }}
    .score-wrapper {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    position: relative;
                }}

                .score {{
                    font-size: 80px;
                    font-weight: 700;
                    color: var(--text-main);
                    line-height: 1;
                    transition: all 0.3s ease;
                }}

                .team.is-loser .score {{
                    opacity: 0.5;
                }}
                
                .quarters-table {{ width: 100%; margin-bottom: 25px; border-collapse: collapse; table-layout: fixed;}}
                .quarters-table th {{ font-size: 10px; color: var(--text-muted); padding-bottom: 20px; text-transform: uppercase; letter-spacing: 0.2em; }}
                .quarters-table td {{ text-align: center; font-size: 16px; padding: 18px 2px; border-bottom: 1px;}}
                .quarters-table .team-id {{ text-align: left; font-weight: 700; width: 70px; color: var(--text-muted); }}
                .quarters-table .total-score {{ font-weight: 700;}}

                .stats-container {{ padding: 30px 40px;}}
                .stat-row {{ margin-bottom: 24px; }}
                .stat-info {{ display: flex; justify-content: space-between; font-size: 11px; font-weight: 700; margin-bottom: 12px; align-items: baseline; }}
                .stat-val {{ width: 140px; }}
                .stat-val.left {{ text-align: left; color: var(--stat-left); }}
                .stat-val.right {{ text-align: right; color: var(--stat-right); }}
                .stat-name {{ color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.2em; flex-grow: 1; text-align: center; }}
                .stat-m-a {{ font-weight: 400; font-size: 10px; opacity: 0.8; margin-left: 4px; }}

                .dual-bar {{ height: 4px; display: flex; justify-content: center; gap: 6px; }}
                .bar-half {{ width: 50%; height: 100%; background: #e6e2d6; border-radius: 10px; position: relative; overflow: hidden; }}
                .fill {{ height: 100%; position: absolute; top: 0; }}
                .fill-l {{ right: 0; background: var(--stat-left); border-radius: 0 10px 10px 0; }}
                .fill-r {{ left: 0; background: var(--stat-right); border-radius: 10px 0 0 10px; }}

                .leaders-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .leader-card {{ display: flex; align-items: center; padding: 24px; background: #e6e2d6; border-radius: var(--radius-lg); position: relative; }}
                .leader-img {{ width: 90px; height: 90px; border-radius: 15px; margin-right: 20px; object-fit: cover; object-position: top; flex-shrink: 0; }}
                .leader-info {{ flex-grow: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }}
                .leader-name {{ font-weight: 700; font-size: 16px; margin-bottom: 6px; line-height: 1.2; color: var(--text-main); }}
                .leader-stat {{ font-size: 12px; color: var(--text-muted); font-weight: 500; }}
                .leader-team-logo {{ width: 32px; height: 32px; object-fit: contain; margin-left: 12px; }}
            </style>
        </head>
        <body>
            <div class="match-card">
                <div class="card-header">{date_display}</div>
<div class="scoreboard">
                    <div class="team {h_lose_class}">
                        <div class="team-name">{home['team']['abbreviation']}</div>
                        <div class="logo-wrapper">
                            <img src="{home['team']['logo']}" class="team-logo">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{home['score']}</div>
                        </div>
                    </div>
                    
                    <div style="font-weight: 900; color: #e6e2d6; font-size: 50px;">VS</div>

                    <div class="team {a_lose_class}">
                        <div class="team-name">{away['team']['abbreviation']}</div>
                        <div class="logo-wrapper">
                            <img src="{away['team']['logo']}" class="team-logo">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{away['score']}</div>
                        </div>
                    </div>
                </div>

                <table class="quarters-table">
                    <thead><tr><th class="team-id"></th>{"".join(thead)}<th class="total-score"></th></tr></thead>
                    <tbody>
                        <tr><td class="team-id">{home['team']['abbreviation']}</td>{"".join(h_row)}<td class="total-score">{home['score']}</td></tr>
                        <tr><td class="team-id">{away['team']['abbreviation']}</td>{"".join(a_row)}<td class="total-score">{away['score']}</td></tr>
                    </tbody>
                </table>

                <div class="stats-container">
                    <div class="stat-row">
                        <div class="stat-info">
                            <div class="stat-val left">{h_fg_p}<span class="stat-m-a">{h_fg_m}</span></div>
                            <div class="stat-name">Field Goals</div>
                            <div class="stat-val right">{a_fg_p}<span class="stat-m-a">{a_fg_m}</span></div>
                        </div>
                        <div class="dual-bar">
                            <div class="bar-half"><div class="fill fill-l" style="width:{h_fg_p}"></div></div>
                            <div class="bar-half"><div class="fill fill-r" style="width:{a_fg_p}"></div></div>
                        </div>
                    </div>
                    <div class="stat-row">
                        <div class="stat-info">
                            <div class="stat-val left">{h_3p_p}<span class="stat-m-a">{h_3p_m}</span></div>
                            <div class="stat-name">3-Pointers</div>
                            <div class="stat-val right">{a_3p_p}<span class="stat-m-a">{a_3p_m}</span></div>
                        </div>
                        <div class="dual-bar">
                            <div class="bar-half"><div class="fill fill-l" style="width:{h_3p_p}"></div></div>
                            <div class="bar-half"><div class="fill fill-r" style="width:{a_3p_p}"></div></div>
                        </div>
                    </div>
                    <div class="stat-row">
                        <div class="stat-info">
                            <div class="stat-val left">{h_ft_p}<span class="stat-m-a">{h_ft_m}</span></div>
                            <div class="stat-name">Free Throws</div>
                            <div class="stat-val right">{a_ft_p}<span class="stat-m-a">{a_ft_m}</span></div>
                        </div>
                        <div class="dual-bar">
                            <div class="bar-half"><div class="fill fill-l" style="width:{h_ft_p}"></div></div>
                            <div class="bar-half"><div class="fill fill-r" style="width:{a_ft_p}"></div></div>
                        </div>
                    </div>
                </div>

                <div class="leaders-grid">
                    <div class="leader-card">
                        <img src="{h_l['headshot']}" class="leader-img">
                        <div class="leader-info"><span class="leader-name">{h_l['name']}</span><span class="leader-stat">{h_l['stats']}</span></div>
                        <img src="{home['team']['logo']}" class="leader-team-logo">
                    </div>
                    <div class="leader-card">
                        <img src="{a_l['headshot']}" class="leader-img">
                        <div class="leader-info"><span class="leader-name">{a_l['name']}</span><span class="leader-stat">{a_l['stats']}</span></div>
                        <img src="{away['team']['logo']}" class="leader-team-logo">
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def get_daily_leader(self, response):
        all_leaders = []

        for event in response.get('events', []):
            for comp in event.get('competitions', []):
                for team in comp.get('competitors', []):
                    # Из каждого матча вытягиваем лидеров
                    # Обычно ESPN присылает категории: points, rebounds, assists, rating
                    for cat in team.get('leaders', []):
                        if cat['name'] == 'rating':  # Собираем по очкам для топа
                            leader_data = cat['leaders'][0]
                            all_leaders.append({
                                "player": leader_data['athlete']['displayName'],
                                "team": team['team']['abbreviation'],
                                "value": float(leader_data['value']),
                                "displayValue": leader_data['displayValue'],
                            })

        # Сортируем по убыванию очков и берем топ-5
        return sorted(all_leaders, key=lambda x: x['value'], reverse=True)[0]


    def generate(self, date: str):
        response = requests.get(API_URL.format(date)).json()
        events = response.get('events', [])

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 2000, 'height': 2400})

            headlines = []

            for i, event in enumerate(events):
                home_team = event['competitions'][0]['competitors'][0]['team']['abbreviation']
                away_team = event['competitions'][0]['competitors'][1]['team']['abbreviation']

                print(f"\nMATCH {i + 1}: {away_team} @ {home_team}")
                # headline = event['competitions'][0].get('headlines', [])
                #
                # if headline:
                #     headlines.append(headline[0]["description"])

                html_content = self.generate_html(event)
                page.set_content(html_content)
                page.wait_for_timeout(2000)

                card = page.query_selector(".match-card")
                card.screenshot(path=f"{OUTPUT_DIR}/match_{i + 1}.png", scale="device")
                print(f"Card {i + 1} loaded.")

            browser.close()

        day_leader = self.get_daily_leader(response)

        return f"{day_leader['player']} ({day_leader['team']}) – {day_leader['displayValue']}"

# if __name__ == "__main__":
#     main()