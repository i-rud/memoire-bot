import os
import requests
import tempfile
import base64
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

LOGO = "https://i.ibb.co/vvLV57QX/2025-12-28-13-00-53.jpg"

class WeeklyPerformances:
    def __init__(self):
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
        self.output_dir = "images/weekly"
        os.makedirs(self.output_dir, exist_ok=True)
        self.overlay_logo_url = ""
        self.team_conferences = {
            'ATL': 'east', 'BOS': 'east', 'BKN': 'east', 'CHA': 'east', 'CHI': 'east',
            'CLE': 'east', 'DET': 'east', 'IND': 'east', 'MIA': 'east', 'MIL': 'east',
            'NYK': 'east', 'NY': 'east', 'ORL': 'east', 'PHI': 'east', 'TOR': 'east', 'WAS': 'east',
            'DAL': 'west', 'DEN': 'west', 'GSW': 'west', 'GS': 'west', 'HOU': 'west', 'LAC': 'west',
            'LAL': 'west', 'MEM': 'west', 'MIN': 'west', 'NOP': 'west', 'NO': 'west', 'OKC': 'west',
            'PHX': 'west', 'PHO': 'west', 'POR': 'west', 'SAC': 'west', 'SAS': 'west', 'SA': 'west', 'UTA': 'west'
        }

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

    def parse_date(self, date_str):
        if "." in date_str:
            day, month = date_str.split(".")
            # Assuming current year (2026) for DD.MM format
            return datetime(2026, int(month), int(day))
        else:
            return datetime.strptime(date_str, "%Y%m%d")

    def fetch_and_aggregate(self, end_date_str):
        end_dt = self.parse_date(end_date_str)
        start_dt = end_dt - timedelta(days=7) # To get exactly the window size e.g. 9 to 16 (8 dates)
        
        curr_dt = start_dt
        dates_to_fetch = []
        while curr_dt < end_dt:
            dates_to_fetch.append(curr_dt.strftime("%Y%m%d"))
            curr_dt += timedelta(days=1)

        print(f"Сканируем матчи с {start_dt.strftime('%d.%m')} по {end_dt.strftime('%d.%m')} ({len(dates_to_fetch)} дней)...")

        players = {} # athlete_id -> dict

        for d_str in dates_to_fetch:
            scoreboard = requests.get(f"{self.api_base}/scoreboard?dates={d_str}").json()
            events = scoreboard.get('events', [])
            
            for event in events:
                game_id = event['id']
                summary = requests.get(f"{self.api_base}/summary?event={game_id}").json()
                
                if not summary.get('boxscore', {}).get('teams'): continue

                # Identify Home and Away and Score
                header_comps = summary.get('header', {}).get('competitions', [{}])[0].get('competitors', [])
                home_data, away_data = {}, {}
                for comp in header_comps:
                    t_info = {
                        'abbrev': comp['team']['abbreviation'],
                        'logo': comp['team']['logos'][0]['href'] if comp['team'].get('logos') else "",
                        'score': int(comp.get('score', '0')) if comp.get('score', '0').isdigit() else 0
                    }
                    if comp.get('homeAway') == 'home': home_data = t_info
                    else: away_data = t_info

                for stat_group in summary.get('boxscore', {}).get('players', []):
                    labels = stat_group['statistics'][0]['keys']
                    team_abbrev = stat_group['team']['abbreviation']
                    team_logo = stat_group['team']['logo']

                    # Check Win/Loss
                    team_won = False
                    if team_abbrev == home_data.get('abbrev'):
                        team_won = home_data.get('score', 0) > away_data.get('score', 0)
                    elif team_abbrev == away_data.get('abbrev'):
                        team_won = away_data.get('score', 0) > home_data.get('score', 0)

                    for athlete in stat_group['statistics'][0]['athletes']:
                        stats_data = athlete.get('stats', [])
                        if not stats_data: continue

                        # Missing minutes means DNP
                        if '0' in stats_data and labels[0] == 'minutes' and len(stats_data) == 1:
                            continue
                        
                        stats_dict = dict(zip(labels, stats_data))
                        
                        # Only count if minutes actually > 0
                        mins_val = stats_dict.get('minutes', '0')
                        if mins_val == '0' or mins_val == '-': continue

                        rating = self._calculate_performance_rating(stats_dict)
                        athlete_id = athlete['athlete']['id']

                        if athlete_id not in players:
                            players[athlete_id] = {
                                'name': athlete['athlete']['displayName'],
                                'shortName': athlete['athlete']['shortName'],
                                'headshot': athlete['athlete'].get('headshot', {}).get('href', 'https://a.espncdn.com/i/headshots/nophoto.png'),
                                'gp': 0, 'wins': 0, 'losses': 0,
                                'team_logo': team_logo,
                                'rating_sum': 0.0,
                                'pts': 0, 'reb': 0, 'ast': 0, 'stl': 0, 'blk': 0, 'pm': 0,
                                'fgm': 0, 'fga': 0, 'tfgm': 0, 'tfga': 0
                            }

                        p = players[athlete_id]
                        p['team_logo'] = team_logo # Most recent logo
                        p['team_abbrev'] = team_abbrev
                        p['gp'] += 1
                        if team_won: p['wins'] += 1
                        else: p['losses'] += 1
                        p['rating_sum'] += rating

                        def get_v(k):
                            try:
                                v = stats_dict.get(k, '0')
                                return float(v) if v and v != '-' else 0.0
                            except: return 0.0

                        p['pts'] += get_v('points')
                        p['reb'] += get_v('rebounds')
                        p['ast'] += get_v('assists')
                        p['stl'] += get_v('steals')
                        p['blk'] += get_v('blocks')
                        p['pm'] += get_v('plusMinus')

                        fgs = stats_dict.get('fieldGoalsMade-fieldGoalsAttempted', '0-0').split('-')
                        p['fgm'] += float(fgs[0]) if len(fgs) > 0 else 0.0
                        p['fga'] += float(fgs[1]) if len(fgs) > 1 else 0.0

                        tfgs = stats_dict.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '0-0').split('-')
                        p['tfgm'] += float(tfgs[0]) if len(tfgs) > 0 else 0.0
                        p['tfga'] += float(tfgs[1]) if len(tfgs) > 1 else 0.0

        # Calculate averages
        for p_id, p in players.items():
            gp = p['gp']
            if gp > 0:
                p['avg_rating'] = p['rating_sum'] / gp
                p['ppg'] = round(p['pts'] / gp, 1)
                p['rpg'] = round(p['reb'] / gp, 1)
                p['apg'] = round(p['ast'] / gp, 1)
                p['spg'] = round(p['stl'] / gp, 1)
                p['bpg'] = round(p['blk'] / gp, 1)
                p['total_pm'] = int(p['pm'])
                p['fg_pct'] = round((p['fgm'] / p['fga'] * 100) if p['fga'] > 0 else 0, 1)
                p['tfg_pct'] = round((p['tfgm'] / p['tfga'] * 100) if p['tfga'] > 0 else 0, 1)

        # Sort by average rating and pick top 5 for East and West
        east_players = [p for p in players.values() if p['gp'] >= 3 and self.team_conferences.get(p.get('team_abbrev', ''), 'west') == 'east']
        west_players = [p for p in players.values() if p['gp'] >= 3 and self.team_conferences.get(p.get('team_abbrev', ''), 'west') == 'west']

        top_east = sorted(east_players, key=lambda x: x['avg_rating'], reverse=True)[:5]
        top_west = sorted(west_players, key=lambda x: x['avg_rating'], reverse=True)[:5]
        
        self.generate_cards(top_east, start_dt, end_dt, "east")
        self.generate_cards(top_west, start_dt, end_dt, "west")

    def generate_cards(self, top_players, start_dt, end_dt, conf):
        print(f"Генерация {len(top_players)} недельных карточек для {conf}...")
        
        date_range_str = f"{start_dt.strftime('%B %d')} - {end_dt.strftime('%B %d, %Y')}".upper()
        
        logo_path = os.path.join(os.path.dirname(__file__), 'images', 'weekly', 'potw', f'{conf}.png')
        potw_logo = ""
        try:
            with open(logo_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            potw_logo = f"data:image/png;base64,{encoded_string}"
        except Exception as e:
            print(f"Could not load POTW logo for {conf} at {logo_path}: {e}")
            potw_logo = ""

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)

            for i, p_data in enumerate(top_players):
                # Calculate Score Badge Color
                r_val = float(p_data["avg_rating"])
                score_bg = "#A63A2F" # <= 6: Red
                if r_val >= 9: score_bg = "#0068B9" # 9+: Deep Blue
                elif r_val >= 8: score_bg = "#00929C" # 8-9: Cyan Blue
                elif r_val >= 7: score_bg = "#41A67E" # 7-8: Green
                elif r_val > 6: score_bg = "#BF8B33" # 6-7: Orange
                
                # Grid Stats (All stats shown unconditionally)
                grid_stats = []
                grid_stats.append(f'<div class="stat-col"><span class="s-val badge-val" style="background: {score_bg};">{"%.2f" % r_val}</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["ppg"]}</span><span class="s-lbl">PPG</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["rpg"]}</span><span class="s-lbl">RPG</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["apg"]}</span><span class="s-lbl">APG</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["spg"]}</span><span class="s-lbl">SPG</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["bpg"]}</span><span class="s-lbl">BPG</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["fg_pct"]}</span><span class="s-lbl">FG%</span></div>')
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["tfg_pct"]}</span><span class="s-lbl">3FG%</span></div>')
                
                # Add Total +/-
                pm_val = f"+{p_data['total_pm']}" if p_data['total_pm'] > 0 else str(p_data['total_pm'])
                pm_color = "#41A67E" if p_data['total_pm'] > 0 else ("#A63A2F" if p_data['total_pm'] < 0 else "var(--text-main)")
                grid_stats.append(f'<div class="stat-col"><span class="s-val" style="color: {pm_color};">{pm_val}</span><span class="s-lbl">+/-</span></div>')
                
                grid_stats.append(f'<div class="stat-col"><span class="s-val">{p_data["wins"]}-{p_data["losses"]}</span><span class="s-lbl">W-L</span></div>')

                potw_img_tag = f'<img src="{potw_logo}" class="potw-logo">' if potw_logo else ""

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap" rel="stylesheet">
                    <style>
                        :root {{ 
                            --bg: #f0eee9; 
                            --accent: #2b2624; 
                            --text-main: #2b2624; 
                            --text-muted: #8e8a7e; 
                            --card-bg: #e6e4de;
                        }}
                        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                        body {{ font-family: 'Unbounded', sans-serif; background: #ddd; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
                        
                        .card {{ width: 1000px; background: var(--bg); padding: 30px 40px 40px 40px; display: flex; flex-direction: column; gap: 20px; position: relative; }}
                        .potw-logo {{ position: absolute; top: -35px; right: 20px; width: 240px; height: 240px; object-fit: contain; z-index: 10; opacity: 1; }}

                        .header {{ display: flex; align-items: center; justify-content: space-between; width: 100%; }}
                        .header-left {{ display: flex; align-items: center; gap: 25px; max-width: 680px; }}
                        .photo-wrapper {{ position: relative; flex-shrink: 0; }}
                        .headshot-container {{ width: 150px; height: 150px; border-radius: 50%; background: var(--card-bg); overflow: hidden; position: relative; z-index: 1; }}
                        .headshot-container img {{ width: 100%; height: 100%; object-fit: cover; object-position: top; }}
                        
                        .team-badge {{ position: absolute; bottom: 0; right: 0; width: 55px; height: 55px; background: var(--bg); border-radius: 50%; display: flex; justify-content: center; align-items: center; z-index: 2; padding: 3px; }}
                        .team-badge img {{ width: 100%; height: 100%; object-fit: contain; }}
                        
                        .header-info {{ display: flex; flex-direction: column; gap: 15px; min-width: 0; }}
                        .name-line {{ font-size: 38px; font-weight: 700; color: var(--text-main); line-height: 1.2; word-wrap: break-word; overflow-wrap: break-word; }}
                        .date-header {{ font-size: 22px; font-weight: 600; color: var(--text-muted); letter-spacing: 1px; }}

                        .stats-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 25px 20px; margin-top: 15px; }}
                        .stat-col {{ display: flex; flex-direction: column; gap: 5px; align-items: center; }}
                        .stat-col .s-val {{ font-size: 36px; font-weight: 800; color: var(--text-main); line-height: 1; }}
                        .stat-col .badge-val {{ color: #ffffff; padding: 11px 16px; border-radius: 12px; font-weight: 500; display: inline-flex; justify-content: center; align-items: center; line-height: 1; }}
                        .stat-col .s-lbl {{ font-size: 20px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }}
                    </style>
                </head>
                <body>
                    <div class="card player-card">
                        {potw_img_tag}
                        <div class="header">
                            <div class="header-left">
                                <div class="photo-wrapper">
                                    <div class="headshot-container">
                                        <img src="{p_data['headshot']}" alt="{p_data['name']}">
                                    </div>
                                    <div class="team-badge">
                                        <img src="{p_data['team_logo']}" alt="team">
                                    </div>
                                </div>
                                <div class="header-info">
                                    <div class="name-line">
                                        <span class="name">{p_data['name']}</span>
                                    </div>
                                    <div class="date-header">{date_range_str}</div>
                                </div>
                            </div>
                        </div>

                        <div class="stats-grid">
                            {"".join(grid_stats)}
                        </div>
                    </div>
                </body>
                </html>
                """
                page.set_content(html_content)
                page.wait_for_timeout(500)
                
                safe_name = p_data['name'].replace(' ', '_').replace("'", "")
                page.locator(".player-card").screenshot(path=f"{self.output_dir}/players/top_{conf}_{i+1}_{safe_name}.png")
                print(f"[{conf.upper()} {i+1}] {p_data['name']} сохранен.")

            browser.close()
            print("Все карточки сохранены в images/weekly!")

if __name__ == "__main__":
    wp = WeeklyPerformances()
    wp.fetch_and_aggregate("16.03")
