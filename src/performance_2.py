from playwright.sync_api import sync_playwright

TEAM_LOGOS = {
    'ATL': 'https://a.espncdn.com/i/teamlogos/nba/500/atl.png',
    'BOS': 'https://a.espncdn.com/i/teamlogos/nba/500/bos.png',
    'BKN': 'https://a.espncdn.com/i/teamlogos/nba/500/bkn.png',
    'CHA': 'https://a.espncdn.com/i/teamlogos/nba/500/cha.png',
    'CHI': 'https://a.espncdn.com/i/teamlogos/nba/500/chi.png',
    'CLE': 'https://a.espncdn.com/i/teamlogos/nba/500/cle.png',
    'DAL': 'https://a.espncdn.com/i/teamlogos/nba/500/dal.png',
    'DEN': 'https://a.espncdn.com/i/teamlogos/nba/500/den.png',
    'DET': 'https://a.espncdn.com/i/teamlogos/nba/500/det.png',
    'GSW': 'https://a.espncdn.com/i/teamlogos/nba/500/gsw.png',
    'HOU': 'https://a.espncdn.com/i/teamlogos/nba/500/hou.png',
    'IND': 'https://a.espncdn.com/i/teamlogos/nba/500/ind.png',
    'LAC': 'https://a.espncdn.com/i/teamlogos/nba/500/lac.png',
    'LAL': 'https://a.espncdn.com/i/teamlogos/nba/500/lal.png',
    'MEM': 'https://a.espncdn.com/i/teamlogos/nba/500/mem.png',
    'MIA': 'https://a.espncdn.com/i/teamlogos/nba/500/mia.png',
    'MIL': 'https://a.espncdn.com/i/teamlogos/nba/500/mil.png',
    'MIN': 'https://a.espncdn.com/i/teamlogos/nba/500/min.png',
    'NOP': 'https://a.espncdn.com/i/teamlogos/nba/500/no.png',
    'NYK': 'https://a.espncdn.com/i/teamlogos/nba/500/nyk.png',
    'OKC': 'https://a.espncdn.com/i/teamlogos/nba/500/okc.png',
    'ORL': 'https://a.espncdn.com/i/teamlogos/nba/500/orl.png',
    'PHI': 'https://a.espncdn.com/i/teamlogos/nba/500/phi.png',
    'PHX': 'https://a.espncdn.com/i/teamlogos/nba/500/phx.png',
    'POR': 'https://a.espncdn.com/i/teamlogos/nba/500/por.png',
    'SAC': 'https://a.espncdn.com/i/teamlogos/nba/500/sac.png',
    'SAS': 'https://a.espncdn.com/i/teamlogos/nba/500/sas.png',
    'TOR': 'https://a.espncdn.com/i/teamlogos/nba/500/tor.png',
    'UTA': 'https://a.espncdn.com/i/teamlogos/nba/500/utah.png',
    'WAS': 'https://a.espncdn.com/i/teamlogos/nba/500/was.png'
}

LOGO = "https://i.ibb.co/vvLV57QX/2025-12-28-13-00-53.jpg"


class Performance:
    def __init__(self):
        # Путь к локальному логотипу (замените на свой)
        self.local_logo_path = 'assets/memoire_logo.jpg'

    def generate_card_right(self, photo_url, stats_string, data):
        items = [item.strip().split(' ', 1) for item in stats_string.split(';')]
        stats_html = "".join([f"""
                <div class="stat-block">
                    <div class="stat-value">{v}</div>
                    <div class="stat-label">{l}</div>
                </div>""" for v, l in items])

        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap" rel="stylesheet">
                <style>
                    :root {{ --bg: #f0eee9; --accent: #2b2624; --text-main: #2b2624; --text-muted: #8e8a7e; --radius: 40px; }}
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ font-family: 'Unbounded', sans-serif; background: var(--bg); display: flex; justify-content: center; align-items: center; min-height: 100vh; }}

                    .player-card {{ display: flex; width: 1000px; height: 1000px; background: #f0eee9; overflow: hidden; position: relative;}}
                    .photo-wrapper {{ flex: 1; height: 100%; background: #000; overflow: hidden; }}
                    .player-img {{ width: 100%; height: 100%; object-fit: cover; object-position: center top; }}

                    .info-wrapper {{ 
                        width: 400px; flex: 0 0 400px; padding: 60px 45px; 
                        display: flex; flex-direction: column; justify-content: flex-start; 
                        border-left: 1px solid #f1f5f9; background: #f0eee9;
                        position: relative; /* ДЛЯ ПОЗИЦИОНИРОВАНИЯ ЛОГО */
                    }}
                    
                    .brand-logo {{
                        position: absolute;
                        top: 35px;
                        left: 35px;
                        width: 80px;
                        height: 80px;
                        object-fit: contain;
                        opacity: 0.7;
                    }}

                    .date {{ font-size: 12px; font-weight: 700; color: var(--text-muted); letter-spacing: 2px; margin-bottom: 12px; }}
                    .player-name {{ font-size: 42px; font-weight: 900; color: var(--text-main); line-height: 1.1; margin-bottom: 30px; letter-spacing: -1.5px; }}
                    .matchup-pill {{ display: inline-flex; align-items: center; gap: 14px; background: #e6e2d6; padding: 14px 22px; border-radius: 24px; margin-bottom: 50px; width: fit-content; }}
                    .team-logo {{ width: 36px; height: 36px; object-fit: contain; }}

                    .stats-container {{ display: flex; flex-direction: column; gap: 40px; }}
                    .stat-block {{ display: flex; flex-direction: column; gap: 4px; }}
                    .stat-value {{ font-size: 95px; font-weight: 900; color: var(--accent); line-height: 1; letter-spacing: -4px; }}
                    .stat-label {{ font-size: 20px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; white-space: normal; line-height: 1.2; }}
                </style>
            </head>
            <body>
                <div class="player-card">
                    <div class="photo-wrapper"><img src="{photo_url}" class="player-img"></div>
                    <div class="info-wrapper">
                        <div class="date">{data['date']}</div>
                        <h1 class="player-name">{data['name'].upper()}</h1>
                        <div class="matchup-pill">
                            <img src="{data['team_logo']}" class="team-logo">
                            <span style="font-weight:900; color:var(--text-muted);">VS</span>
                            <img src="{data['opp_logo']}" class="team-logo">
                        </div>
                        <div class="stats-container">{stats_html}</div>
                    </div>
                </div>
            </body>
            </html>
            """

    def generate_card_bottom(self, photo_url, stats_string, data):
        items = [item.strip().split(' ', 1) for item in stats_string.split(';')]
        stats_html = "".join([f"""
                <div class="stat-block">
                    <div class="stat-value">{v}</div>
                    <div class="stat-label">{l}</div>
                </div>""" for v, l in items])

        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap" rel="stylesheet">
                <style>
                    :root {{ --bg: #f8fafc; --accent: #2b2624; --text-main: #2b2624; --text-muted: #8e8a7e; --radius: 40px; }}
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ font-family: 'Unbounded', sans-serif; background: var(--bg); display: flex; justify-content: center; align-items: center; min-height: 100vh; }}

                    .player-card {{ display: flex; flex-direction: column; width: 1000px; height: 1000px; background: #f0eee9; overflow: hidden; }}
                    .photo-wrapper {{ flex: 1; width: 100%; background: #000; overflow: hidden; }}
                    .player-img {{ width: 100%; height: 100%; object-fit: cover; object-position: center top; }}

                    .info-wrapper {{ 
                        height: 350px; flex: 0 0 350px; width: 100%; 
                        padding: 50px 65px; border-top: 1px solid #f1f5f9; background: #f0eee9;
                        display: flex; flex-direction: column; justify-content: flex-start;
                         position: relative;
                    }}
                    
                    .brand-logo {{
                        position: absolute;
                        top: 35px;
                        left: 35px;
                        width: 60px;
                        height: 60px;
                        object-fit: contain;
                    }}

                    .header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
                    .player-name {{ font-size: 46px; font-weight: 900; color: var(--text-main); line-height: 1; letter-spacing: -2px; }}
                    .matchup-pill {{ display: flex; align-items: center; gap: 14px; background: #e6e2d6; padding: 14px 26px; border-radius: 26px; }}
                    .team-logo {{ width: 40px; height: 40px; object-fit: contain; }}

                    .stats-container {{ display: flex; justify-content: space-between; width: 100%; gap: 30px; }}
                    .stat-block {{ flex: 1; display: flex; flex-direction: column; gap: 6px; }}

                    /* ЕЩЕ БОЛЕЕ КРУПНЫЕ ЗНАЧЕНИЯ */
                    .stat-value {{ font-size: 96px; font-weight: 900; color: var(--accent); line-height: 1; letter-spacing: -5px; }}

                    .stat-label {{ 
                        font-size: 20px; font-weight: 700; color: var(--text-muted); 
                        text-transform: uppercase; letter-spacing: 1px; line-height: 1.2;
                    }}
                </style>
            </head>
            <body>
                <div class="player-card">
                    <div class="photo-wrapper"><img src="{photo_url}" class="player-img"></div>
                    <div class="info-wrapper">
                        <div class="header-row">
                            <div>
                                <div style="font-size: 13px; font-weight: 700; color: var(--text-muted); letter-spacing: 2px; margin-bottom: 10px;">{data['date']}</div>
                                <h1 class="player-name">{data['name'].upper()}</h1>
                            </div>
                            <div class="matchup-pill">
                                <img src="{data['team_logo']}" class="team-logo">
                                <span style="font-weight:900; color:var(--text-muted); margin:0 6px;">VS</span>
                                <img src="{data['opp_logo']}" class="team-logo">
                            </div>
                        </div>
                        <div class="stats-container">{stats_html}</div>
                    </div>
                </div>
            </body>
            </html>
            """

    def generate(self, name, date, home, away, url, stats, layout="right"):
        data = {
            'name': name,
            'date': date,
            'team_logo': TEAM_LOGOS[home.upper()],
            'opp_logo': TEAM_LOGOS[away.upper()],
        }

        if layout == "right":
            html = self.generate_card_right(url, stats, data)
        else:
            html = self.generate_card_bottom(url, stats, data)

        with sync_playwright() as p:
            browser = p.chromium.launch()

            context = browser.new_context(device_scale_factor=2)
            page = context.new_page()

            page.set_content(html)

            filename = f"images/performances/performance.png"
            card = page.query_selector(".player-card")
            if card:
                card.screenshot(path=filename)
                print(f"Loaded: {filename}")

            browser.close()


# if __name__ == "__main__":
#     performance = Performance()
#     performance.generate()