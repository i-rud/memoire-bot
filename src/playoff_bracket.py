import requests
import os
import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

class PlayoffBracket:
    def __init__(self):
        self.api_url = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
        # Используем динамический диапазон дат (с начала плей-офф до сегодня)
        today = datetime.now().strftime("%Y%m%d")
        self.scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20260415-{today}&limit=300"
        self.output_dir = "images/playoff"
        os.makedirs(self.output_dir, exist_ok=True)
        self.playoff_logo = "https://i.ibb.co/JjQQV6qN/tg-image-799289939.png"
        self.finals_logo = "https://i.ibb.co/DfbcVHvv/finals.png"

    def get_data(self):
        # 1. Seeds from Standings
        try:
            standings = requests.get(self.api_url).json()
            seeds = {"east": {}, "west": {}}
            for group in standings.get('children', []):
                conf_name = group['name'].lower()
                conf_key = "east" if "east" in conf_name else "west"
                for entry in group['standings']['entries']:
                    team = entry['team']
                    seed_val = next((int(s['value']) for s in entry['stats'] if s['name'] == 'playoffSeed'), 99)
                    if seed_val <= 8:
                        seeds[conf_key][seed_val] = {
                            "name": team['displayName'],
                            "abbrev": team['abbreviation'],
                            "logo": team['logos'][0]['href'] if team.get('logos') else "",
                            "id": team['id'],
                            "color": f"#{team.get('color', '2b2624')}"
                        }
        except Exception as e:
            print(f"Error fetching seeds: {e}")
            seeds = {"east": {}, "west": {}}

        # 2. Series info from Scoreboard
        series_data = {} # (team_id_1, team_id_2) sorted tuple -> summary
        try:
            scoreboard = requests.get(self.scoreboard_url).json()
            for event in scoreboard.get('events', []):
                comp = event['competitions'][0]
                if 'series' in comp:
                    t1 = comp['competitors'][0]['team']['id']
                    t2 = comp['competitors'][1]['team']['id']
                    key = tuple(sorted([str(t1), str(t2)]))
                    series_data[key] = comp['series'].get('summary', '0-0')
        except Exception as e:
            print(f"Error fetching scoreboard: {e}")

        return seeds, series_data

    def _parse_series_score(self, summary, team1_name, team1_abbrev):
        # Example: "ATL leads 2-1" or "Series tied 2-2"
        if not summary or summary == "0-0": return "0", "0"
        if "starts" in summary.lower(): return "0", "0"
        
        nums = re.findall(r'\d+', summary)
        if len(nums) >= 2:
            s1, s2 = nums[0], nums[1]
            # Check if team1 is leading
            if team1_name in summary or team1_abbrev in summary:
                # If team1 is mentioned, it's likely leading if not "tied"
                if "tied" in summary.lower():
                    return s1, s2
                return s1, s2
            else:
                # Team 2 is leading
                if "tied" in summary.lower():
                    return s1, s2
                return s2, s1
        return "0", "0"

    def generate_html(self, seeds, series_data):
        def get_team_data(conf, seed):
            if conf not in seeds: return {"abbrev": "TBD", "logo": "", "name": "TBD", "id": None}
            t = seeds[conf].get(seed)
            if not t: return {"abbrev": "TBD", "logo": "", "name": "TBD", "id": None}
            return t

        def get_matchup_data(conf, s1, s2):
            t1 = get_team_data(conf, s1)
            t2 = get_team_data(conf, s2)
            
            if not t1['id'] or not t2['id']:
                return t1, t2, "0", "0", "TBD"
            
            key = tuple(sorted([str(t1['id']), str(t2['id'])]))
            summary = series_data.get(key, "Series tied 0-0")
            score1, score2 = self._parse_series_score(summary, t1['name'], t1['abbrev'])
            return t1, t2, score1, score2, summary

        def render_matchup(conf, s1, s2, is_small=False):
            t1, t2, sc1, sc2, summary = get_matchup_data(conf, s1, s2)
            box_class = "matchup-box" + (" small" if is_small else "")
            
            logo1 = f'<img src="{t1["logo"]}" class="mini-logo">' if t1["logo"] else '<div class="no-logo"></div>'
            logo2 = f'<img src="{t2["logo"]}" class="mini-logo">' if t2["logo"] else '<div class="no-logo"></div>'
            
            # Подсвечиваем только если серия выиграна (4 победы)
            is_w1 = int(sc1) >= 4
            is_w2 = int(sc2) >= 4

            return f"""
            <div class="{box_class}">
                <div class="team-line {'winner' if is_w1 else ''}">
                    <div class="team-main">
                        <span class="seed">{s1 if s1 else ''}</span>
                        {logo1}
                        <span class="team-name">{t1['abbrev']}</span>
                    </div>
                    <span class="series-score">{sc1}</span>
                </div>
                <div class="team-line {'winner' if is_w2 else ''}">
                    <div class="team-main">
                        <span class="seed">{s2 if s2 else ''}</span>
                        {logo2}
                        <span class="team-name">{t2['abbrev']}</span>
                    </div>
                    <span class="series-score">{sc2}</span>
                </div>
            </div>
            """

        def render_round_col(conf, pairs, round_name, cls=""):
            html = f'<div class="round-col {cls}" style="position: relative;">'
            html += f"""
                <div class="round-header">
                    <div class="header-conf">{conf.upper()}</div>
                    <div class="header-round">{round_name}</div>
                </div>
            """
            for i in range(0, len(pairs), 2):
                if i + 1 < len(pairs):
                    html += f'<div class="matchup-pair">'
                    html += render_matchup(conf, pairs[i][0], pairs[i][1])
                    html += render_matchup(conf, pairs[i+1][0], pairs[i+1][1])
                    html += '</div>'
                else:
                    html += render_matchup(conf, pairs[i][0], pairs[i][1])
            html += '</div>'
            return html

        def get_winner(conf, s1, s2):
            if not s1 or not s2: return None
            t1, t2, sc1, sc2, summary = get_matchup_data(conf, s1, s2)
            if int(sc1) >= 4: return s1
            if int(sc2) >= 4: return s2
            return None

        r1_seeds = [(1, 8), (4, 5), (3, 6), (2, 7)]
        
        # Calculate East advancement
        east_r2_seeds = [
            (get_winner("east", r1_seeds[0][0], r1_seeds[0][1]), get_winner("east", r1_seeds[1][0], r1_seeds[1][1])),
            (get_winner("east", r1_seeds[2][0], r1_seeds[2][1]), get_winner("east", r1_seeds[3][0], r1_seeds[3][1]))
        ]
        east_r3_seeds = [(get_winner("east", east_r2_seeds[0][0], east_r2_seeds[0][1]), get_winner("east", east_r2_seeds[1][0], east_r2_seeds[1][1]))]
        east_champ = get_winner("east", east_r3_seeds[0][0], east_r3_seeds[0][1])

        # Calculate West advancement
        west_r2_seeds = [
            (get_winner("west", r1_seeds[0][0], r1_seeds[0][1]), get_winner("west", r1_seeds[1][0], r1_seeds[1][1])),
            (get_winner("west", r1_seeds[2][0], r1_seeds[2][1]), get_winner("west", r1_seeds[3][0], r1_seeds[3][1]))
        ]
        west_r3_seeds = [(get_winner("west", west_r2_seeds[0][0], west_r2_seeds[0][1]), get_winner("west", west_r2_seeds[1][0], west_r2_seeds[1][1]))]
        west_champ = get_winner("west", west_r3_seeds[0][0], west_r3_seeds[0][1])

        east_r1 = render_round_col("east", r1_seeds, "First Round", "r1")
        east_r2 = render_round_col("east", east_r2_seeds, "Conf. Semifinals", "semis")
        east_r3 = render_round_col("east", east_r3_seeds, "Conf. Finals", "finals")

        west_r1 = render_round_col("west", r1_seeds, "First Round", "r1")
        west_r2 = render_round_col("west", west_r2_seeds, "Conf. Semifinals", "semis")
        west_r3 = render_round_col("west", west_r3_seeds, "Conf. Finals", "finals")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;600;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #f0eee9;
                    --card-bg: #e6e4de;
                    --text-main: #2b2624;
                    --text-muted: #8e8a7e;
                    --east: #A63A2F;
                    --west: #263D52;
                    --accent: #C9A227;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    background: var(--bg); 
                    font-family: 'Unbounded', sans-serif; 
                    display: flex; justify-content: center; align-items: center; 
                    width: 1760px;
                    height: 900px;
                    margin: 0;
                }}
                .bracket-wrapper {{
                    width: 100%;
                    height: 100%;
                    padding: 100px 80px;
                    display: flex;
                    flex-direction: column;
                    position: relative;
                }}
                
                .bracket-layout {{
                    display: grid;
                    grid-template-columns: 660px 220px 660px;
                    gap: 30px;
                    align-items: center;
                    margin: 0 auto;
                }}

                .conference-side {{
                    display: flex;
                    gap: 30px;
                    align-items: center;
                    height: 100%;
                    position: relative;
                }}
                .side-east {{ flex-direction: row-reverse; }}

                .round-header {{
                    position: absolute;
                    top: -65px;
                    left: 50%;
                    transform: translateX(-50%);
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                    white-space: nowrap;
                }}
                .round-header .header-conf {{
                    font-size: 13px;
                    font-weight: 900;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                    color: var(--text-muted);
                }}
                .round-header .header-round {{
                    font-size: 15px;
                    font-weight: 700;
                    color: var(--text-main);
                }}

                .round-label {{
                    position: absolute;
                    top: -40px;
                    font-size: 12px;
                    font-weight: 900;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 3px;
                    width: 200px;
                    text-align: center;
                    white-space: nowrap;
                }}

                .round-col {{
                    display: flex;
                    flex-direction: column;
                    justify-content: space-around;
                    height: 700px;
                }}
                .round-col.semis, .round-col.finals {{
                    gap: 0;
                }}

                .matchup-box {{
                    width: 185px;
                    background: rgba(255,255,255,0.3);
                    backdrop-filter: blur(10px);
                    border-radius: 18px;
                    padding: 10px;
                    border: 1px solid rgba(255,255,255,0.5);
                    box-shadow: 0 4px 20px rgba(0,0,0,0.03);
                    position: relative;
                }}
                
                .matchup-pair {{
                    display: flex;
                    flex-direction: column;
                    justify-content: space-around;
                    position: relative;
                }}
                .r1 .matchup-pair {{ height: 350px; }}
                .semis .matchup-pair {{ height: 700px; }}

                .matchup-box::after {{
                    content: "";
                    position: absolute;
                    top: 50%;
                    width: 15px;
                    height: 1px;
                    background: var(--text-muted);
                    opacity: 0.5;
                }}
                .side-west .matchup-box::after {{ right: -15px; }}
                .side-east .matchup-box::after {{ left: -15px; }}

                /* Vertical line */
                .matchup-pair::after {{
                    content: "";
                    position: absolute;
                    top: 25%;
                    bottom: 25%;
                    width: 1px;
                    background: var(--text-muted);
                    opacity: 0.5;
                }}
                .side-west .matchup-pair::after {{ right: -15px; }}
                .side-east .matchup-pair::after {{ left: -15px; }}

                /* Dash to next round */
                .matchup-pair::before {{
                    content: "";
                    position: absolute;
                    top: 50%;
                    width: 15px;
                    height: 1px;
                    background: var(--text-muted);
                    opacity: 0.5;
                }}
                .side-west .matchup-pair::before {{ right: -30px; }}
                .side-east .matchup-pair::before {{ left: -30px; }}

                /* Finals round special dash - reaching the scaled Finals box */
                .round-col.finals .matchup-box::after {{
                    width: 70px;
                    opacity: 0.5;
                }}
                .side-west .round-col.finals .matchup-box::after {{ right: -70px; }}
                .side-east .round-col.finals .matchup-box::after {{ left: -70px; }}

                .finals-matchup::after, .finals-matchup::before {{
                    display: none;
                }}
                
                .team-line {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 6px 10px;
                    border-radius: 10px;
                    transition: all 0.2s;
                }}
                .team-line.winner {{ background: rgba(0,0,0,0.05); }}
                
                .team-main {{ display: flex; align-items: center; gap: 8px; }}
                .seed {{ font-size: 11px; font-weight: 800; color: var(--text-muted); width: 12px; }}
                .mini-logo {{ width: 32px; height: 32px; object-fit: contain; }}
                .no-logo {{ width: 32px; height: 32px; background: rgba(0,0,0,0.05); border-radius: 50%; }}
                .team-name {{ font-size: 18px; font-weight: 700; color: var(--text-main); }}
                .series-score {{ font-size: 20px; font-weight: 900; color: var(--text-muted); }}
                .winner .series-score {{ color: var(--text-main); }}

                
                .center-column {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 0 40px;
                }}
                
                .finals-matchup {{
                    transform: scale(1.2);
                    background: rgba(255,255,255,0.3);
                    backdrop-filter: blur(10px);
                    border-radius: 18px;
                    padding: 10px;
                    border: 1px solid rgba(255,255,255,0.5);
                    box-shadow: 0 4px 20px rgba(0,0,0,0.03);
                }}
                
            </style>
        </head>
        <body>
            <div class="bracket-wrapper">
                <div class="bracket-layout">
                    <div class="conference-side side-west">
                        {west_r1}
                        {west_r2}
                        {west_r3}
                    </div>

                    <div class="center-column">
                        <div style="position: relative;">
                            <img src="{self.finals_logo}" style="position: absolute; top: -120px; left: 50%; transform: translateX(-50%); width: 240px; opacity: 0.9;">
                            {render_matchup("finals", west_champ, east_champ).replace('matchup-box', 'matchup-box finals-matchup')}
                        </div>
                    </div>

                    <div class="conference-side side-east">
                        {east_r1}
                        {east_r2}
                        {east_r3}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def generate(self):
        seeds, series_data = self.get_data()
        html = self.generate_html(seeds, series_data)
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(device_scale_factor=2)
            page = context.new_page()
            page.set_content(html)
            
            output_path = os.path.join(self.output_dir, "playoff_bracket.png")
            # Wait for images to load
            page.wait_for_load_state("networkidle")
            
            container = page.query_selector(".bracket-wrapper")
            if container:
                container.screenshot(path=output_path)
                print(f"Bracket generated: {output_path}")
            
            browser.close()

if __name__ == "__main__":
    PlayoffBracket().generate()
