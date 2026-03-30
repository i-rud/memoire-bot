import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from playwright.sync_api import sync_playwright

API_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
OUTPUT_DIR = "images/scores"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


class Scores:
    def __init__(self):
        pass

    def _calculate_performance_rating(self, s):
        def get_f(key):
            try:
                val = s.get(key, '0')
                if val == '-': return 0.0
                return float(val)
            except: return 0.0

        pts = get_f('points')
        ast = get_f('assists')
        stl = get_f('steals')
        blk = get_f('blocks')
        tov = get_f('turnovers')
        pf = get_f('fouls')
        mins = get_f('minutes')
        pm = get_f('plusMinus')
        
        # Rebounds
        orb = get_f('offensiveRebounds')
        drb = get_f('defensiveRebounds')
        total_reb = get_f('rebounds')
        if orb == 0 and drb == 0 and total_reb > 0:
            orb = total_reb * 0.3
            drb = total_reb * 0.7

        # FGM/FGA
        fgs = s.get('fieldGoalsMade-fieldGoalsAttempted', '0-0').split('-')
        fgm = float(fgs[0]) if len(fgs) > 0 else 0.0
        fga = float(fgs[1]) if len(fgs) > 1 else 0.0

        # FTM/FTA
        fts = s.get('freeThrowsMade-freeThrowsAttempted', '0-0').split('-')
        ftm = float(fts[0]) if len(fts) > 0 else 0.0
        fta = float(fts[1]) if len(fts) > 1 else 0.0

        gs = pts + 0.4*fgm - 0.5*fga - 0.3*(fta-ftm) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov
        pm_impact = 0.4 * pm * (mins / 48.0)
        raw_score = gs + pm_impact

        milestones = [
            (-15.0, 1.0), (-5.0, 3.0), (0.0, 5.0), (8.0, 6.5), 
            (15.0, 7.5), (25.0, 8.5), (35.0, 9.0), (45.0, 9.6), (65.0, 10.0)
        ]
        
        if raw_score <= milestones[0][0]: return 1.0
        if raw_score >= milestones[-1][0]: return 10.0

        for i in range(len(milestones) - 1):
            x1, y1 = milestones[i]
            x2, y2 = milestones[i+1]
            if x1 <= raw_score <= x2:
                val = y1 + (raw_score - x1) * (y2 - y1) / (x2 - x1)
                return round(val, 2)
        return 1.0

    def _get_player_stats_string(self, s):
        def parse_stat(key):
            try:
                val = s.get(key, '0')
                return int(val) if val and val.isdigit() else 0
            except: return 0

        pts = parse_stat('points')
        reb = parse_stat('rebounds')
        ast = parse_stat('assists')
        stl = parse_stat('steals')
        blk = parse_stat('blocks')

        fgs = s.get('fieldGoalsMade-fieldGoalsAttempted', '0-0').replace('-', '/')
        tgs = s.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '0-0').replace('-', '/')

        parts = [f"{pts} PTS"]
        if reb >= 3: parts.append(f"{reb} REB")
        if ast >= 3: parts.append(f"{ast} AST")
        if stl >= 3: parts.append(f"{stl} STL")
        if blk >= 3: parts.append(f"{blk} BLK")
        
        parts.append(f"{fgs} FG")
        parts.append(f"{tgs} 3PT")
        
        return " · ".join(parts)

    def _get_rating_color(self, rating):
        try:
            r = float(rating)
        except: r = 0.0
        if r >= 9: return "#0068B9"
        if r >= 8: return "#00929C"
        if r >= 7: return "#41A67E"
        if r > 6: return "#BF8B33"
        return "#A63A2F"

    def generate_html(self, summary):
        header = summary.get('header', {})
        comp = header.get('competitions', [{}])[0]
        date_str = header.get('competitions', [{}])[0].get('date', '')
        
        utc_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
        date_display = et_dt.strftime("%B %d, %Y")

        home = next(t for t in comp['competitors'] if t['homeAway'] == 'home')
        away = next(t for t in comp['competitors'] if t['homeAway'] == 'away')

        def get_team_info(comp_obj):
            team = comp_obj['team']
            return {
                'logo': team['logos'][0]['href'] if team.get('logos') else "",
                'score': comp_obj.get('score', '0'),
                'abbrev': team.get('abbreviation', '')
            }

        home_info = get_team_info(home)
        away_info = get_team_info(away)
        
        home_score_val = int(home_info['score']) if home_info['score'].isdigit() else 0
        away_score_val = int(away_info['score']) if away_info['score'].isdigit() else 0
        h_lose_class = "is-loser" if home_score_val < away_score_val else ""
        a_lose_class = "is-loser" if away_score_val < home_score_val else ""


        # Boxscore Players
        team_players = []
        for team_box in summary.get('boxscore', {}).get('players', []):
            labels = team_box['statistics'][0]['keys']
            team_abbrev = team_box['team']['abbreviation']
            players_list = []
            
            for athlete_stat in team_box['statistics'][0]['athletes']:
                stats_data = athlete_stat.get('stats', [])
                if not stats_data: continue
                
                stats_dict = dict(zip(labels, stats_data))
                rating = self._calculate_performance_rating(stats_dict)
                
                try:
                    pts = int(stats_dict.get('points', '0'))
                except:
                    pts = 0
                
                players_list.append({
                    'name': athlete_stat['athlete']['displayName'],
                    'shortName': athlete_stat['athlete']['shortName'],
                    'headshot': athlete_stat['athlete'].get('headshot', {}).get('href', 'https://a.espncdn.com/i/headshots/nophoto.png'),
                    'rating': rating,
                    'pts': pts,
                    'stats_str': self._get_player_stats_string(stats_dict),
                    'color': self._get_rating_color(rating)
                })
            
            # Sort by points and take top 5
            players_list.sort(key=lambda x: x['pts'], reverse=True)
            team_players.append({
                'abbrev': team_abbrev,
                'logo': team_box['team']['logo'],
                'players': players_list[:5]
            })

        home_players = next(t for t in team_players if t['abbrev'] == home['team']['abbreviation'])
        away_players = next(t for t in team_players if t['abbrev'] == away['team']['abbreviation'])

        def render_player(p):
            # Split stats string into segments for val/lbl styling
            stat_segments = []
            shoot_segments = []
            
            for s in p['stats_str'].split(' · '):
                parts = s.split(' ')
                if len(parts) == 2:
                    stat_html = f'<div class="mini-stat"><span class="val">{parts[0]}</span><span class="lbl">{parts[1]}</span></div>'
                    if parts[1] in ('FG', '3PT'):
                        shoot_segments.append(stat_html)
                    else:
                        stat_segments.append(stat_html)
            
            stats_html = "".join(stat_segments)
            shoot_html = "".join(shoot_segments)

            return f"""
            <div class="player-entry">
                <div class="headshot-container">
                    <img src="{p['headshot']}">
                </div>
                <div class="player-info">
                    <div class="name-line">
                        <span class="player-name">{p['shortName']}</span>
                        <div class="score-badge" style="background: {p['color']}">{p['rating']}</div>
                    </div>
                    <div class="stats-row">{stats_html}</div>
                    <div class="stats-row" style="margin-top: 5px;">{shoot_html}</div>
                </div>
            </div>
            """

        home_html = "".join([render_player(p) for p in home_players['players']])
        away_html = "".join([render_player(p) for p in away_players['players']])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@300;400;500;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --card-bg: #f0eee9; --text-main: #2b2624; --text-muted: #8e8a7e;
                    --radius: 20px;
                }}
                * {{ box-sizing: border-box; }}
                body {{ font-family: 'Unbounded', sans-serif; background: transparent; display: flex; justify-content: center; align-items: center; margin: 0; padding: 40px; }}
                .match-card {{ background: var(--card-bg); width: 1700px; padding: 60px; position: relative; }}
                
                .date-header {{ text-align: center; color: var(--text-muted); font-size: 18px; font-weight: 700; margin-bottom: 60px; text-transform: uppercase; letter-spacing: 0.3em; }}
                
                .scoreboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 80px; align-items: center; margin-bottom: 100px; position: relative; }}
                .team {{ display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }}
                .team-name {{ font-size: 22px; font-weight: 700; color: var(--text-muted); margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px; }}
                .logo-wrapper {{ position: relative; width: 300px; height: 300px; border-radius: 60px; display: flex; justify-content: center; align-items: center; margin-bottom: 40px; }}
                .team-logo-main {{ width: 210px; height: 210px; object-fit: contain; }}
                
                .score-wrapper {{ display: flex; align-items: center; justify-content: center; width: 100%; }}
                .score {{ font-size: 160px; font-weight: 800; color: var(--text-main); line-height: 0.9; transition: all 0.3s ease; letter-spacing: -8px; }}
                .team.is-loser .score {{ opacity: 0.3; }}
                
                .vs-divider {{ position: absolute; left: 50%; top: 40%; transform: translate(-50%, -50%); font-size: 80px; font-weight: 900; color: #e6e2d6; margin: 0; letter-spacing: -2px; }}
                
                .columns-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 80px; }}
                .players-list {{ width: max-content; margin: 0 auto; }}

                .player-entry {{ display: flex; align-items: center; gap: 25px; margin-bottom: 40px; }}
                .headshot-container {{ width: 140px; height: 140px; border-radius: 50%; background: #e6e2d6; overflow: hidden; flex-shrink: 0; }}
                .headshot-container img {{ width: 100%; height: 100%; object-fit: cover; object-position: top; }}
                
                .player-info {{ flex-grow: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }}
                .name-line {{ display: flex; align-items: center; gap: 15px; font-size: 32px; font-weight: 700; color: var(--text-main); }}
                .player-name {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
                .score-badge {{ background: var(--score-bg); color: #fff; padding: 8px 12px; border-radius: 10px; font-size: 28px; font-weight: 500; line-height: 1; display: flex; align-items: center; justify-content: center; }}
                
                .stats-row {{ display: flex; gap: 15px; align-items: baseline; margin-top: 5px; flex-wrap: wrap; }}
                .mini-stat {{ display: flex; align-items: baseline; gap: 5px; }}
                .mini-stat .val {{ font-size: 36px; font-weight: 900; color: var(--text-main); line-height: 1; letter-spacing: 0px; }}
                .mini-stat .lbl {{ font-size: 16px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }}
            </style>
        </head>
        <body>
            <div class="match-card">
                <div class="date-header">{date_display}</div>
                
                <div class="scoreboard">
                    <div class="team {h_lose_class}">
                        <div class="team-name">{home_info['abbrev']}</div>
                        <div class="logo-wrapper">
                            <img src="{home_info['logo']}" class="team-logo-main">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{home_info['score']}</div>
                        </div>
                    </div>
                    
                    <div class="vs-divider">VS</div>

                    <div class="team {a_lose_class}">
                        <div class="team-name">{away_info['abbrev']}</div>
                        <div class="logo-wrapper">
                            <img src="{away_info['logo']}" class="team-logo-main">
                        </div>
                        <div class="score-wrapper">
                            <div class="score">{away_info['score']}</div>
                        </div>
                    </div>
                </div>

                <div class="columns-container">
                    <div class="column">
                        <div class="players-list">
                            {home_html}
                        </div>
                    </div>
                    <div class="column">
                        <div class="players-list">
                            {away_html}
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def get_daily_leader(self, summary_list):
        all_leaders = []
        for summary in summary_list:
            for team_box in summary.get('boxscore', {}).get('players', []):
                labels = team_box['statistics'][0]['keys']
                team_abbrev = team_box['team']['abbreviation']
                for athlete_stat in team_box['statistics'][0]['athletes']:
                    stats_data = athlete_stat.get('stats', [])
                    if not stats_data: continue
                    stats_dict = dict(zip(labels, stats_data))
                    rating = self._calculate_performance_rating(stats_dict)
                    all_leaders.append({
                        "player": athlete_stat['athlete']['displayName'],
                        "team": team_abbrev,
                        "value": rating,
                        "displayValue": f"{rating}"
                    })
        if not all_leaders: return None
        return sorted(all_leaders, key=lambda x: x['value'], reverse=True)[0]

    def generate(self, date: str):
        scoreboard = requests.get(f"{API_BASE}/scoreboard?dates={date}").json()
        events = scoreboard.get('events', [])
        
        summary_list = []

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1600, 'height': 2000})

            for i, event in enumerate(events):
                game_id = event['id']
                print(f"Fetching summary for game {game_id}...")
                summary = requests.get(f"{API_BASE}/summary?event={game_id}").json()
                
                if not summary.get('boxscore', {}).get('teams'): continue
                
                summary_list.append(summary)
                
                html_content = self.generate_html(summary)
                page.set_content(html_content)
                page.wait_for_timeout(1000)

                card = page.query_selector(".match-card")
                if card:
                    card.screenshot(path=f"{OUTPUT_DIR}/match_{i + 1}.png", scale="device")
                    print(f"Match {i + 1} image saved.")

            browser.close()

        day_leader = self.get_daily_leader(summary_list)
        if day_leader:
            return f"{day_leader['player']} ({day_leader['team']}) – {day_leader['displayValue']}"
        return "No games processed."

# if __name__ == "__main__":
#     main()