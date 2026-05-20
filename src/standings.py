import requests
import os
from playwright.sync_api import sync_playwright

API_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

TOTAL_GAMES = 82
PLAYOFF_CUTOFF = 6


class Standings:
    def __init__(self):
        pass

    def get_standings_data(self):
        response = requests.get(API_URL).json()
        print(f"API Response keys: {response.keys()}")
        conferences = []

        for group in response.get('children', []):
            print(f"Processing conference: {group.get('name')}")
            conf_data = {
                "name": group['name'],
                "slug": group['name'].lower().replace("ern conference", "").strip(),
                "teams": []
            }
            for entry in group['standings']['entries']:
                team = entry['team']
                stats = {s['name']: s['displayValue'] for s in entry['stats']}
                seed_raw = next((s['value'] for s in entry['stats'] if s['name'] == 'playoffSeed'), 99)
                pct_raw = next((float(s['value']) for s in entry['stats'] if s['name'] == 'winPercent'), 0.0)
                last_10 = stats.get('lastTenGamesRecord', stats.get('Last Ten Games', '0-0'))
                wins_raw = int(next((s['value'] for s in entry['stats'] if s['name'] == 'wins'), 0))
                losses_raw = int(next((s['value'] for s in entry['stats'] if s['name'] == 'losses'), 0))

                conf_data["teams"].append({
                    "logo": team['logos'][0]['href'],
                    "name": team['displayName'],
                    "winLoss": f"{stats.get('wins', '0')}-{stats.get('losses', '0')}",
                    "pct": stats.get('winPercent', '.000'),
                    "seed": int(seed_raw),
                    "pct_raw": pct_raw,
                    "streak": stats.get('streak', '-'),
                    "l10": last_10,
                    "wins_raw": wins_raw,
                    "losses_raw": losses_raw,
                })

            conf_data["teams"].sort(key=lambda x: (x['seed'], -x['pct_raw']))
            conferences.append(conf_data)
        return conferences

    def calculate_clinch_status(self, teams: list) -> list:
        """
        Помечает команды статусами:
        'clinched' (x): Гарантированный ТОП-6 (Плей-офф).
        'playin' (o): Гарантированный ТОП 7-10 (Плей-ин), нет шансов на топ-6 и нет риска вылететь.
        'eliminated' (e): Нет шансов даже на Плей-ин (11-15 место).
        """

        def games_remaining(team):
            return TOTAL_GAMES - team['wins_raw'] - team['losses_raw']

        sorted_teams = sorted(teams, key=lambda t: (t['seed'], -t['pct_raw']))
        n = len(sorted_teams)

        # Ориентиры
        team_at_6 = sorted_teams[5] if n > 5 else None
        team_at_7 = sorted_teams[6] if n > 6 else None
        team_at_10 = sorted_teams[9] if n > 9 else None
        team_at_11 = sorted_teams[10] if n > 10 else None

        for team in sorted_teams:
            gr_team = games_remaining(team)
            
            # 1. Clinched Playoffs (X)
            clinched = False
            if team_at_7:
                gr_7 = games_remaining(team_at_7)
                if team['wins_raw'] > team_at_7['wins_raw'] + gr_7:
                    clinched = True
            team['clinched'] = clinched

            # 2. Eliminated (E)
            eliminated = False
            if team_at_10:
                if team['wins_raw'] + gr_team < team_at_10['wins_raw']:
                    eliminated = True
            team['eliminated'] = eliminated

            # 3. Play-In Guaranteed (O)
            playin = False
            if team_at_6 and team_at_11:
                gr_11 = games_remaining(team_at_11)
                # Не может догнать 6-го и не может быть догнан 11-м
                cannot_reach_6 = team['wins_raw'] + gr_team < team_at_6['wins_raw']
                cannot_fall_below_10 = team['wins_raw'] > team_at_11['wins_raw'] + gr_11
                if cannot_reach_6 and cannot_fall_below_10:
                    playin = True
            team['playin'] = playin

        return sorted_teams

    def generate_conf_html(self, conf):
        teams = self.calculate_clinch_status(conf['teams'])

        rows = ""
        for idx, t in enumerate(teams, 1):
            display_rank = t['seed'] if t['seed'] < 99 else idx
            zone_class = "playoff-zone" if display_rank <= 6 else "playin-zone" if display_rank <= 10 else ""

            # Иконки статуса
            clinch_html = ""
            if t.get('clinched'):
                clinch_html = '<span class="status-icon status-x">x</span>'
            elif t.get('playin'):
                clinch_html = '<span class="status-icon status-o">pi</span>'
            elif t.get('eliminated'):
                clinch_html = '<span class="status-icon status-e">o</span>'

            # Логика группировки названий зон
            zone_label_html = ""
            if display_rank == 1:
                zone_label_html = '<td rowspan="6" class="vertical-zone-td"><div class="zone-text">PLAYOFFS</div></td>'
            elif display_rank == 7:
                zone_label_html = '<td rowspan="4" class="vertical-zone-td"><div class="zone-text">PLAY-IN</div></td>'
            elif display_rank == 11:
                zone_label_html = f'<td rowspan="{len(teams) - 10}" class="vertical-zone-td"></td>'

            rows += f"""
            <tr class="team-row">
                {zone_label_html}
                <td class="clinch-cell">{clinch_html}</td>
                <td class="rank-cell">
                    <span class="rank-badge {zone_class}">{display_rank}</span>
                </td>
                <td class="team-cell">
                    <img src="{t['logo']}" class="team-logo">
                    <span class="team-name">{t['name']}</span>
                </td>
                <td class="stat font-bold">{t['winLoss']}</td>
                <td class="stat font-bold">{t['pct']}</td>
                <td class="stat">{t['streak']}</td>
                <td class="stat">{t['l10']}</td>
            </tr>
            """

            if display_rank == 6 or display_rank == 10:
                rows += '<tr class="line-divider"><td colspan="8"><div></div></td></tr>'

        conf_color = {
            "Eastern Conference": "#A63A2F",
            "Western Conference": "#263D52"
        }

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;500;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #f8fafc;
                    --card-bg: #f0eee9;
                    --text-main: #2b2624;
                    --text-muted: #8e8a7e;
                    --accent: {conf_color[conf['name']]};
                    --divider: #8e8a7e;
                    --status-green: #166534;
                    --status-orange: #92400e;
                    --status-red: var(--text-muted);
                }}
                body {{ font-family: 'Unbounded', sans-serif; background: var(--bg); padding: 40px; display: flex; justify-content: center; margin: 0; }}

                .main-card {{ 
                    background: var(--card-bg); 
                    width: 950px; 
                    padding: 50px 40px; 
                }}

                .header {{ text-align: center; margin-bottom: 40px; }}
                .header h1 {{ font-weight: 900; font-size: 32px; margin: 0; color: var(--text-main); letter-spacing: -1px; }}
                .conf-badge {{ 
                    display: inline-block; background: var(--accent); color: white; 
                    padding: 8px 20px; border-radius: 14px; font-size: 12px; font-weight: 700; 
                    margin-top: 15px; letter-spacing: 2px; text-transform: uppercase;
                }}

                .standings-table {{ width: 100%; border-collapse: collapse; }}

                .vertical-zone-td {{
                    width: 20px;
                    vertical-align: middle;
                    padding: 0 !important;
                    text-align: center;
                }}

                .zone-text {{
                    transform: rotate(-90deg);
                    white-space: nowrap;
                    font-size: 14px;
                    font-weight: 800;
                    color: var(--text-muted);
                    letter-spacing: 3px;
                    opacity: 0.5;
                    display: inline-block;
                }}

                .standings-table th {{ font-size: 10px; color: var(--text-muted); padding: 15px 5px; text-transform: uppercase; letter-spacing: 1px; }}
                .standings-table td {{ padding: 10px 5px; text-align: center; font-size: 15px; }}
                .standings-table th:first-child {{ width: 40px; }}

                .line-divider td {{ padding: 0 !important; }}
                .line-divider div {{ border-bottom: 2px dashed var(--divider); opacity: 0.4; margin: 8px 0; }}

                .rank-cell {{
                    white-space: nowrap;
                    vertical-align: middle;
                }}

                .clinch-cell {{
                    width: 24px;
                    text-align: center;
                    vertical-align: middle;
                    padding: 0 4px !important;
                }}

                .team-cell {{ display: flex; align-items: center; text-align: left; }}
                .team-logo {{ width: 36px; height: 36px; margin-right: 15px; object-fit: contain; }}
                .team-name {{ font-weight: 600; color: var(--text-main); font-size: 17px; }}

                .rank-badge {{
                    display: inline-flex; justify-content: center; align-items: center;
                    width: 32px; height: 32px; border-radius: 10px; font-size: 12px;
                    font-weight: 700; color: var(--text-muted); background: #e6e2d6;
                    vertical-align: middle;
                }}

                .status-icon {{
                    display: inline-block;
                    font-size: 13px;
                    font-weight: 600;
                    vertical-align: middle;
                    text-align: center;
                    text-transform: lowercase;
                }}
                .status-x {{ color: var(--status-green); }}
                .status-o {{ color: var(--status-orange); }}
                .status-e {{ color: var(--status-red); }}


                /* Легенда */
                .legend {{
                    display: flex;
                    gap: 30px;
                    justify-content: center;
                    margin-top: 35px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(0,0,0,0.05);
                }}
                .legend-item {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    text-transform: uppercase;
                    color: var(--text-muted);
                }}

                .playoff-zone {{ background: rgba(34, 197, 94, 0.15); color: #166534; }}
                .playin-zone {{ background: rgba(245, 158, 11, 0.15); color: #92400e; }}

                .stat {{ color: var(--text-main); }}
                .font-bold {{ font-weight: 800; }}
            </style>
        </head>
        <body>
            <div class="main-card">
                <div class="header">
                    <h1>NBA STANDINGS 25/26</h1>
                    <div class="conf-badge">{conf['name']}</div>
                </div>
                <table class="standings-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th style="width: 14px;"></th>
                            <th style="width: 80px;">POS</th>
                            <th style="text-align: left;">TEAM</th>
                            <th style="width: 100px;">W-L</th>
                            <th style="width: 70px;">%</th>
                            <th style="width: 70px;">STRK</th>
                            <th style="width: 90px;">L10</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                <div class="legend">
                    <div class="legend-item"><span class="status-icon status-x">x</span> Clinched Playoffs</div>
                    <div class="legend-item"><span class="status-icon status-o">pi</span> Clinched Play-In</div>
                    <div class="legend-item"><span class="status-icon status-e">o</span> Eliminated</div>
                </div>

            </div>
        </body>
        </html>
        """

    def generate(self):
        data = self.get_standings_data()
        os.makedirs("images/standings", exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(device_scale_factor=2)
            page = context.new_page()
            for conf in data:
                html = self.generate_conf_html(conf)
                page.set_content(html)
                filename = f"images/standings/nba_{conf['slug']}_standings.png"
                card = page.query_selector(".main-card")
                if card:
                    card.screenshot(path=filename)
                    print(f"Loaded: {filename}")
            browser.close()

# if __name__ == "__main__":
#     Standings().generate()