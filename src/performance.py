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


class Performance:

    def _base_styles(self):
        return """
        <style>
            :root {
                --bg-main: #0B1220;
                --bg-top: #16233A;

                --primary-blue: #1E5DFF;
                --accent-red: #E53935;

                --gold: #C9A227;
                --gold-soft: #E0B84A;

                --text-main: #FFFFFF;
                --text-muted: rgba(255,255,255,0.65);
            }

            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: 'Unbounded', sans-serif;
                background: radial-gradient(circle at 50% 0%, var(--bg-top) 0%, var(--bg-main) 65%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }

            .player-card {
                width: 1000px;
                height: 1000px;
                display: flex;
                background: linear-gradient(180deg, #16233A 0%, #0F1A2D 100%);
                overflow: hidden;
                position: relative;
                box-shadow:
                    0 25px 60px rgba(0,0,0,0.6),
                    inset 0 0 0 1px rgba(255,255,255,0.04);
            }

            .player-card::before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                height: 4px;
                width: 100%;
                background: linear-gradient(90deg, var(--gold), var(--gold-soft));
            }

            .photo-wrapper {
                flex: 1;
                background: #000;
                overflow: hidden;
            }

            .player-img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: center top;
            }

            .info-wrapper {
                width: 420px;
                padding: 70px 55px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }

            .date {
                font-size: 13px;
                font-weight: 700;
                color: var(--text-muted);
                letter-spacing: 2px;
                margin-bottom: 14px;
                text-transform: uppercase;
            }

            .player-name {
                font-size: 48px;
                font-weight: 900;
                color: var(--text-main);
                line-height: 1.05;
                margin-bottom: 35px;
                letter-spacing: -2px;
            }

            .matchup-pill {
                display: inline-flex;
                align-items: center;
                gap: 16px;
                padding: 10px 22px;
                border-radius: 999px;
                background: rgba(255,255,255,0.08);
                box-shadow: 0 0 18px rgba(30,93,255,0.35);
                margin-bottom: 60px;
            }

            .team-logo {
                width: 38px;
                height: 38px;
                object-fit: contain;
            }

            .stats-container {
                display: flex;
                flex-direction: column;
                gap: 45px;
            }

            .stat-value {
                font-size: 100px;
                font-weight: 900;
                color: var(--gold);
                line-height: 1;
                letter-spacing: -5px;
            }

            .stat-label {
                font-size: 20px;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        </style>
        """

    def generate_card_right(self, photo_url, stats_string, data):
        items = [item.strip().split(' ', 1) for item in stats_string.split(';')]
        stats_html = "".join(
            f"""
            <div>
                <div class="stat-value">{v}</div>
                <div class="stat-label">{l}</div>
            </div>
            """ for v, l in items
        )

        return f"""
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap" rel="stylesheet">
            {self._base_styles()}
        </head>
        <body>
            <div class="player-card">
                <div class="photo-wrapper">
                    <img src="{photo_url}" class="player-img">
                </div>
                <div class="info-wrapper">
                    <div class="date">{data['date']}</div>
                    <div class="player-name">{data['name'].upper()}</div>

                    <div class="matchup-pill">
                        <img src="{data['team_logo']}" class="team-logo">
                        <span style="color:var(--text-muted); font-weight:900;">VS</span>
                        <img src="{data['opp_logo']}" class="team-logo">
                    </div>

                    <div class="stats-container">
                        {stats_html}
                    </div>
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