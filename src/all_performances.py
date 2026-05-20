import os
import requests
import tempfile
from datetime import datetime
from playwright.sync_api import sync_playwright

LOGO = "https://i.ibb.co/vvLV57QX/2025-12-28-13-00-53.jpg"

class PerformanceSummary:
    def __init__(self):
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
        self.output_dir = "images/performances"
        os.makedirs(self.output_dir, exist_ok=True)
        # playin: https://i.ibb.co/pvJ0sZbw/tg-image-3440809921.png
        # playoffs: https://i.ibb.co/JjQQV6qN/tg-image-799289939.png 
        self.overlay_logo_url = "https://i.ibb.co/JjQQV6qN/tg-image-799289939.png"

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

        # 1. Modified Game Score (optimized for performance cards)
        gs = pts + 0.4*fgm - 0.5*fga - 0.3*(fta-ftm) + 0.7*orb + 0.3*drb + stl + 0.7*ast + 0.7*blk - 0.4*pf - tov

        # 2. PM Impact (balanced weight: 0.4, normalized by minutes)
        pm_impact = 0.15 * pm * (mins / 48.0)

        raw_score = gs + pm_impact

        # 4. Mapping (Recalibrated milestones for better top-end headroom)
        milestones = [
            (-15.0, 1.0),
            (-5.0, 3.0), 
            (0.0, 5.0), 
            (8.0, 6.5), 
            (15.0, 7.5), 
            (25.0, 8.5), 
            (35.0, 9.0), 
            (45.0, 9.6), 
            (65.0, 10.0)
        ]
        
        if raw_score <= milestones[0][0]: return 1.0
        if raw_score >= milestones[-1][0]: return 10.0

        for i in range(len(milestones) - 1):
            x1, y1 = milestones[i]
            x2, y2 = milestones[i+1]
            if x1 <= raw_score <= x2:
                # Linear interpolation between milestones
                val = y1 + (raw_score - x1) * (y2 - y1) / (x2 - x1)
                return round(val, 2)
        
        return 1.0

    def _process_display_data(self, p, rating, stats_dict):
        s = stats_dict
        # Parse basic stats safely
        def parse_stat(key):
            try:
                val = s.get(key, '0')
                if not val or val == '-': return 0
                return int(val) if str(val).isdigit() else 0
            except: return 0

        pts = parse_stat('points')
        reb = parse_stat('rebounds')
        ast = parse_stat('assists')
        stl = parse_stat('steals')
        blk = parse_stat('blocks')
        tov = parse_stat('turnovers')
        mins = parse_stat('minutes')
        pf = parse_stat('fouls')
        pm = s.get('plusMinus', '0')

        # Complex stats
        fg_str = s.get('fieldGoalsMade-fieldGoalsAttempted', '0-0').replace('-', '/')
        fgm, fga = 0, 0
        if '/' in fg_str:
            parts = fg_str.split('/')
            fgm, fga = int(parts[0]), int(parts[1])
        fg_pct = round((fgm/fga * 100) if fga > 0 else 0, 1)

        tg_str = s.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '0-0').replace('-', '/')
        ft_str = s.get('freeThrowsMade-freeThrowsAttempted', '0-0').replace('-', '/')
        fta = int(ft_str.split('/')[1]) if '/' in ft_str else 0
        
        # Advanced stats
        ts_denom = (2 * (fga + 0.44 * fta))
        ts_pct = round((pts / ts_denom * 100) if ts_denom > 0 else 0, 1)
        
        # Color coding for +/-
        pm_color = "#2b2624"
        if pm and pm != '0':
            if pm.startswith('+'): pm_color = "#41A67E"
            elif pm.startswith('-'): pm_color = "#A63A2F"

        # Color coding for Score Badge
        try: r_val = float(rating)
        except: r_val = 0.0
            
        score_bg = "#A63A2F"
        if r_val >= 9: score_bg = "#0068B9"
        elif r_val >= 8: score_bg = "#00929C"
        elif r_val >= 7: score_bg = "#41A67E"
        elif r_val > 6: score_bg = "#BF8B33"

        short_name = p["shortName"]

        # Dynamic Primary Stats
        top_stats = [{'val': pts, 'lbl': 'pts'}]
        # Order dictates priority on tie: reb > blk > stl > ast
        candidates = [{'val': reb, 'lbl': 'reb'}, {'val': blk, 'lbl': 'blk'}, {'val': stl, 'lbl': 'stl'}, {'val': ast, 'lbl': 'ast'}]
        qualifying = sorted([c for c in candidates if c['val'] >= 3], key=lambda x: x['val'], reverse=True)
        top_stats.extend(qualifying[:2])
        if len(top_stats) < 3 and fg_pct >= 50.0: top_stats.append({'val': f"{fg_pct}%", 'lbl': 'fg%'})
        
        primary_stats_html = "".join([f'<div class="big-stat"><span class="val">{st["val"]}</span><span class="lbl">{st["lbl"]}</span></div>' for st in top_stats[:3]])

        return {
            'pts': pts, 'reb': reb, 'ast': ast, 'stl': stl, 'blk': blk,
            'mins': mins, 'pm': pm, 'pm_color': pm_color, 'fg_pct': fg_pct,
            'rating': rating, 'score_bg': score_bg, 'short_name': short_name,
            'primary_stats_html': primary_stats_html, 'ts_pct': ts_pct
        }

    def _generate_html(self, p, data, date_str, team_logo, home_data, away_data):
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            formatted_date = date_obj.strftime("%B %d, %Y").upper()
        except:
            formatted_date = date_str

        home_score = int(home_data.get('score', 0) or 0)
        away_score = int(away_data.get('score', 0) or 0)
        home_bold = "font-weight: 900;" if home_score > away_score else "font-weight: 400; opacity: 0.5;"
        away_bold = "font-weight: 900;" if away_score > home_score else "font-weight: 400; opacity: 0.5;"

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
                        --divider: rgba(0,0,0,0.1);
                    }}
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{ font-family: 'Unbounded', sans-serif; background: #ddd; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
                    
                    .card {{
                        width: 1000px;
                        background: var(--bg);
                        padding: 30px 40px 40px 40px;
                        border-radius: 0;
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                        position: relative;
                    }}

                    .date-header {{
                        font-family: 'Unbounded', sans-serif;
                        font-size: 18px;
                        font-weight: 600;
                        color: var(--text-muted);
                        letter-spacing: 1px;
                        margin-bottom: -5px;
                    }}

                    .header {{
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        width: 100%;
                    }}
                    .header-left {{
                        display: flex;
                        align-items: center;
                        gap: 25px;
                    }}
                    .photo-wrapper {{
                        position: relative;
                        flex-shrink: 0;
                    }}
                    .headshot-container {{
                        width: 150px;
                        height: 150px;
                        border-radius: 50%;
                        background: var(--card-bg);
                        overflow: hidden;
                        flex-shrink: 0;
                        position: relative;
                        z-index: 1;
                    }}
                    .headshot-container img {{
                        width: 100%;
                        height: 100%;
                        object-fit: cover;
                        object-position: top;
                    }}
                    .team-badge {{
                        position: absolute;
                        bottom: 0;
                        right: 0;
                        width: 55px;
                        height: 55px;
                        background: var(--bg);
                        border-radius: 50%;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        z-index: 2;
                        padding: 3px;
                    }}
                    .team-badge img {{
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                    }}
                    .header-info {{
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                    }}
                    .name-line {{
                        display: flex;
                        align-items: center;
                        gap: 15px;
                        font-size: 32px;
                        font-weight: 700;
                        color: var(--text-main);
                    }}
                    .name-line .score-badge {{ 
                        background: {data['score_bg']}; 
                        color: #fff; 
                        padding: 8px 12px;
                        border-radius: 10px; 
                        font-size: 28px; 
                        font-weight: 500;
                        line-height: 1;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    
                    .primary-stats {{
                        display: flex;
                        gap: 20px;
                        align-items: baseline;
                    }}
                    .big-stat {{
                        display: flex;
                        align-items: baseline;
                        gap: 5px;
                    }}
                    .big-stat .val {{ font-size: 56px; font-weight: 900; letter-spacing: 0px; color: var(--text-main); line-height: 1; }}
                    .big-stat .lbl {{ font-size: 22px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }}

                    .middle-row {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        width: 100%;
                        position: relative;
                    }}
                    .watermark {{
                        position: absolute;
                        left: 50%;
                        transform: translateX(-50%);
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        opacity: 1;
                    }}
                    .watermark img {{
                        height: 35px;
                        width: auto;
                        object-fit: contain;
                    }}
                    .watermark span {{
                        font-family: 'Unbounded', sans-serif;
                        font-size: 24px;
                        font-weight: 600;
                        color: var(--text-main);
                        text-transform: lowercase;
                        letter-spacing: 0.5px;
                    }}
                    .matchup-score {{
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        padding: 12px 16px;
                        border-radius: 30px;
                    }}
                    .matchup-logo {{
                        width: 45px;
                        height: 45px;
                        object-fit: contain;
                    }}
                    .score-text {{
                        font-family: 'Unbounded', sans-serif;
                        font-size: 24px;
                        font-weight: 700;
                        color: var(--text-main);
                    }}

                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(7, 1fr);
                        gap: 20px 10px;
                        margin-top: 20px;
                    }}
                    .stat-col {{
                        display: flex;
                        flex-direction: column;
                        gap: 5px;
                        align-items: center;
                    }}
                    .stat-col .s-val {{
                        font-size: 32px;
                        font-weight: 800;
                        color: var(--text-main);
                        line-height: 1;
                    }}
                    .stat-col .s-lbl {{
                        font-size: 22px;
                        font-weight: 700;
                        color: var(--text-muted);
                        align-items: center;
                    }}

                    .overlay-logo {{
                        position: absolute;
                        top: 10px;
                        right: 40px;
                        width: 150px;
                        object-fit: contain;
                        z-index: 100;
                    }}
                </style>
            </head>
            <body>
                <div class="card player-card">
                    {f'<img src="{self.overlay_logo_url}" class="overlay-logo">' if self.overlay_logo_url else ''}
                    <div class="header">
                        <div class="header-left">
                            <div class="photo-wrapper">
                                <div class="headshot-container">
                                    <img src="{p['headshot']}" alt="{p['name']}">
                                </div>
                                <div class="team-badge">
                                    <img src="{team_logo}" alt="team">
                                </div>
                            </div>
                            <div class="header-info">
                                <div class="name-line">
                                    <span class="name">{data['short_name']}</span>
                                    <div class="score-badge">{"%.2f" % data['rating']}</div>
                                </div>
                                <div class="primary-stats">
                                    {data['primary_stats_html']}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="middle-row">
                        <div class="date-header">{formatted_date}</div>
                        <div class="watermark">
                            <img src="{LOGO}" alt="logo">
                            <span>tg/memoirenba</span>
                        </div>
                    <div class="matchup-score">
                        <img src="{home_data['logo']}" class="matchup-logo">
                        <span class="score-text">
                            <span style="{home_bold}">{home_data['score']}</span>
                            <span style="font-weight: 900; color: var(--text-muted); margin: 0 6px; font-size: 14px;"></span>
                            <span style="{away_bold}">{away_data['score']}</span>
                        </span>
                        <img src="{away_data['logo']}" class="matchup-logo">
                    </div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-col"><span class="s-val">{data['mins']}</span><span class="s-lbl">MIN</span></div>
                        <div class="stat-col"><span class="s-val">{data['pts']}</span><span class="s-lbl">PTS</span></div>
                        <div class="stat-col"><span class="s-val">{data['reb']}</span><span class="s-lbl">REB</span></div>
                        <div class="stat-col"><span class="s-val">{data['ast']}</span><span class="s-lbl">AST</span></div>
                        <div class="stat-col"><span class="s-val">{data['stl']}</span><span class="s-lbl">STL</span></div>
                        <div class="stat-col"><span class="s-val">{data['blk']}</span><span class="s-lbl">BLK</span></div>
                        <div class="stat-col"><span class="s-val" style="color: {data['pm_color']};">{data['pm']}</span><span class="s-lbl">+/-</span></div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-col"><span class="s-val">{data['fg_pct']}</span><span class="s-lbl">FG%</span></div>
                        <div class="stat-col"><span class="s-val">{p['stats'].get('fieldGoalsMade-fieldGoalsAttempted', '0/0').replace('-','/')}</span><span class="s-lbl">FG</span></div>
                        <div class="stat-col"><span class="s-val">{p['stats'].get('threePointFieldGoalsMade-threePointFieldGoalsAttempted', '0/0').replace('-','/')}</span><span class="s-lbl">3FG</span></div>
                        <div class="stat-col"><span class="s-val">{p['stats'].get('freeThrowsMade-freeThrowsAttempted', '0/0').replace('-','/')}</span><span class="s-lbl">FTS</span></div>
                        <div class="stat-col"><span class="s-val">{p['stats'].get('turnovers','0')}</span><span class="s-lbl">TO</span></div>
                        <div class="stat-col"><span class="s-val">{p['stats'].get('fouls','0')}</span><span class="s-lbl">PF</span></div>
                        <div class="stat-col"><span class="s-val">{data.get('ts_pct',0)}</span><span class="s-lbl">TS%</span></div>
                    </div>
                </div>
            </body>
            </html>
        """
        return html_content

    def _generate_summary_image(self, players, output_filename, browser_page, date_str):
        # Format date for title (YYYYMMDD to MARCH 13, 2026)
        try:
            d_obj = datetime.strptime(date_str, "%Y%m%d")
            long_date = d_obj.strftime("%B %d, %Y").upper()
        except:
            long_date = date_str

        rows_html = ""
        for i, p in enumerate(players):
            d = p['processed_data']
            # Color coding for +/- (adjusted for light theme)
            pm_val = str(d['pm'])
            pm_color = "#2b2624"
            if pm_val.startswith('+'): pm_color = "#2E7D32" # Darker green for light bg
            elif pm_val.startswith('-'): pm_color = "#C62828" # Darker red for light bg
            
            rows_html += f"""
            <div class="summary-row">
                <div class="rank-badge">#{p['rank']}</div>
                <div class="photo-col">
                    <div class="headshot-container">
                        <img src="{p['headshot']}">
                    </div>
                    <div class="team-badge">
                        <img src="{p['team_logo']}">
                    </div>
                </div>
                <div class="info-col">
                    <div class="name-line">
                        <span class="name">{p['name']}</span>
                        <span class="rating" style="background: {d['score_bg']}; color: #fff;">{"%.2f" % d['rating']}</span>
                    </div>
                    <div class="stats-line">
                        <div class="s-item"><div class="s-v">{d['pts']}</div><div class="s-l">PTS</div></div>
                        <div class="s-item"><div class="s-v">{d['reb']}</div><div class="s-l">REB</div></div>
                        <div class="s-item"><div class="s-v">{d['ast']}</div><div class="s-l">AST</div></div>
                        <div class="s-item"><div class="s-v">{d['stl']}</div><div class="s-l">STL</div></div>
                        <div class="s-item"><div class="s-v">{d['blk']}</div><div class="s-l">BLK</div></div>
                        <div class="s-item"><div class="s-v" style="color: {pm_color}">{d['pm']}</div><div class="s-l">+/-</div></div>
                        <div class="s-item"><div class="s-v">{d['fg_pct']}%</div><div class="s-l">FG%</div></div>
                    </div>
                </div>
            </div>
            """

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@400;700;900&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #f0eee9;
                    --accent: #2b2624;
                    --card-bg: transparent;
                    --text-muted: #8e8a7e;
                }}
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    background: var(--bg); 
                    font-family: 'Unbounded', sans-serif; 
                    width: 1200px;
                    padding: 80px 60px;
                    color: var(--accent);
                }}
                .header {{ 
                    margin-bottom: 60px; 
                    width: 100%;
                    display: flex;
                    justify-content: center;
                }}
                .date-long {{
                    font-size: 20px;
                    font-weight: 600;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .summary-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                }}
                .summary-row {{
                    background: var(--card-bg);
                    padding: 25px 0px;
                    display: flex;
                    align-items: center;
                    gap: 35px;
                    position: relative;
                }}
                .rank-badge {{
                    font-size: 42px;
                    font-weight: 900;
                    color: var(--accent);
                    width: 80px;
                    text-align: center;
                }}
                .photo-col {{
                    position: relative;
                    width: 140px;
                    height: 140px;
                }}
                .headshot-container {{
                    width: 100%;
                    height: 100%;
                    border-radius: 50%;
                    background: rgba(43, 38, 36, 0.04);
                    overflow: hidden;
                    border: none;
                }}
                .headshot-container img {{
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    object-position: top;
                }}
                .team-badge {{
                    position: absolute;
                    bottom: 0px;
                    right: 0px;
                    width: 50px;
                    height: 50px;
                    background: var(--bg);
                    border-radius: 50%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 3px;
                }}
                .team-badge img {{
                    width: 90%; height: 90%; object-fit: contain;
                }}
                .info-col {{
                    flex-grow: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }}
                .name-line {{
                    display: flex;
                    align-items: center;
                    gap: 25px;
                }}
                .name {{
                    font-size: 40px;
                    font-weight: 700;
                    color: var(--accent);
                }}
                .rating {{
                    font-size: 28px;
                    font-weight: 500;
                    padding: 8px 16px;
                    border-radius: 12px;
                    line-height: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .stats-line {{
                    display: flex;
                    justify-content: space-between;
                    padding-right: 50px;
                }}
                .s-item {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    min-width: 85px;
                }}
                .s-v {{
                    font-size: 36px;
                    font-weight: 900;
                    color: var(--accent);
                    line-height: 1;
                }}
                .s-l {{
                    font-size: 16px;
                    font-weight: 700;
                    color: var(--text-muted);
                    margin-top: 6px;
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="date-long">{long_date}</div>
            </div>
            <div class="summary-container">
                {rows_html}
            </div>
        </body>
        </html>
        """
        browser_page.set_viewport_size({'width': 1200, 'height': 800})
        browser_page.set_content(full_html)
        browser_page.wait_for_load_state("networkidle")
        screenshot_path = os.path.join(self.output_dir, output_filename)
        # Screenshot ONLY the body content to avoid excess empty space at the bottom
        browser_page.locator("body").screenshot(path=screenshot_path)
        print(f"Сводка {output_filename} сохранена")

    def fetch_and_generate(self, date_str):
        print(f"Загрузка матчей за {date_str}...")
        scoreboard = requests.get(f"{self.api_base}/scoreboard?dates={date_str}").json()
        all_top_candidates = []
        best_player = None

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)

            for event in scoreboard.get('events', []):
                game_id = event['id']
                summary = requests.get(f"{self.api_base}/summary?event={game_id}").json()
                if not summary.get('boxscore', {}).get('teams'): continue

                header_comps = summary.get('header', {}).get('competitions', [{}])[0].get('competitors', [])
                home_data, away_data = {}, {}
                for comp in header_comps:
                    t_info = {
                        'abbrev': comp['team']['abbreviation'],
                        'name': comp['team']['displayName'],
                        'logo': comp['team']['logos'][0]['href'] if comp['team'].get('logos') else "",
                        'score': comp.get('score', '0')
                    }
                    if comp.get('homeAway') == 'home': home_data = t_info
                    else: away_data = t_info

                for stat_group in summary.get('boxscore', {}).get('players', []):
                    labels = stat_group['statistics'][0]['keys']
                    team_logo = stat_group['team']['logo']
                    team_name = stat_group['team']['displayName']

                    for athlete in stat_group['statistics'][0]['athletes']:
                        stats_data = athlete.get('stats', [])
                        if not stats_data: continue
                        
                        stats_dict = dict(zip(labels, stats_data))
                        rating = self._calculate_performance_rating(stats_dict)
                        processed = self._process_display_data(athlete['athlete'], rating, stats_dict)

                        def get_v(k):
                            try:
                                v = stats_dict.get(k, '0')
                                return int(v) if v and v.isdigit() else 0
                            except: return 0
                        
                        f_pts = get_v('points')
                        f_reb = get_v('rebounds')
                        f_ast = get_v('assists')
                        f_stl = get_v('steals')
                        f_blk = get_v('blocks')
                        f_tov = get_v('turnovers')
                        fps = round(f_pts + 1.2*f_reb + 1.5*f_ast + 3*f_stl + 3*f_blk - f_tov)

                        player_data = {
                            'name': athlete['athlete']['displayName'],
                            'shortName': athlete['athlete']['shortName'],
                            'headshot': athlete['athlete'].get('headshot', {}).get('href', 'https://a.espncdn.com/i/headshots/nophoto.png'),
                            'team_logo': team_logo,
                            'stats': stats_dict,
                            'processed_data': processed,
                            'rating': rating,
                            'fps': fps
                        }

                        if best_player is None or (rating, fps) > (best_player['rating'], best_player['fps']):
                            best_player = {
                                'name': player_data['name'],
                                'team': team_name,
                                'rating': rating,
                                'fps': fps,
                                'pts': f_pts,
                                'reb': f_reb,
                                'ast': f_ast,
                                'stl': f_stl
                            }
                        
                        all_top_candidates.append(player_data)

                        if rating >= 0.0:
                            print(f"Генерация: {player_data['name']} ({rating} score)")
                            html = self._generate_html(player_data, processed, date_str, team_logo, home_data, away_data)
                            page.set_content(html)
                            game_folder = os.path.join(self.output_dir, f"{home_data['abbrev']}_vs_{away_data['abbrev']}")
                            os.makedirs(game_folder, exist_ok=True)
                            safe_name = player_data['name'].replace(' ', '_').replace("'", "")
                            page.locator(".player-card").screenshot(path=f"{game_folder}/{safe_name}.png")

            sorted_candidates = sorted(all_top_candidates, key=lambda x: (x['rating'], x['fps']), reverse=True)
            top_10 = sorted_candidates[:10]
            for i, p in enumerate(top_10): p['rank'] = i + 1

            if len(top_10) > 0:
                print("Генерация сводок TOP-10...")
                if top_10[:5]: self._generate_summary_image(top_10[:5], "00_TOP_1_5.png", page, date_str)
                if top_10[5:10]: self._generate_summary_image(top_10[5:10], "00_TOP_6_10.png", page, date_str)

            browser.close()
            print("Готово!")
            return best_player

    def generate_premium_merge(self, card_path, photo_path):
        """
        Phase 1: Renders only the player photo stretched to 1100x1500.
        No stats, no watermarks, no filters.
        """
        output_path = os.path.join(self.output_dir, "premium_composite.png")
        
        # Absolute paths
        abs_card = os.path.abspath(card_path)
        abs_photo = os.path.abspath(photo_path)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body, html {{
                    margin: 0; padding: 0;
                    width: 1100px; height: 1350px;
                    background: #2b2624;
                    overflow: hidden;
                }}
                .container {{
                    position: relative;
                    width: 1100px; height: 1350px;
                }}
                .bg-photo {{
                    position: absolute;
                    width: 100%; height: 950px;
                    top: 0; left: 0;
                    object-fit: cover;
                    object-position: top center;
                }}
                .gradient-overlay {{
                    position: absolute;
                    top: 650px;
                    left: 0;
                    width: 100%;
                    height: 300px;
                    background: linear-gradient(to top, #2b2624 0%, transparent 100%);
                    z-index: 1;
                }}
                .grain-overlay {{
                    position: absolute;
                    width: 100%; height: 100%;
                    top: 0; left: 0;
                    background: rgba(128, 128, 128, 0.05);
                    filter: url(#grain);
                    opacity: 0.35;
                    mix-blend-mode: overlay;
                    z-index: 2;
                    pointer-events: none;
                }}
                .card-img {{
                    position: absolute;
                    bottom: 50px;
                    left: 50px;
                    width: 1000px;
                    border-radius: 20px;
                    box-shadow: 0 40px 100px rgba(0,0,0,0.8);
                    z-index: 3;
                }}

                .overlay-logo {{
                    position: absolute;
                    top: 50px;
                    right: 50px;
                    width: 140px;
                    height: 140px;
                    object-fit: contain;
                    z-index: 100;
                }}
            </style>
        </head>
        <body>
            <svg style="display: none;">
                <filter id="duotone">
                    <feColorMatrix type="matrix" values=".33 .33 .33 0 0 .33 .33 .33 0 0 .33 .33 .33 0 0 0 0 0 1 0" />
                    <feComponentTransfer color-interpolation-filters="sRGB">
                        <feFuncR type="table" tableValues="0.169 0.941" />
                        <feFuncG type="table" tableValues="0.149 0.933" />
                        <feFuncB type="table" tableValues="0.141 0.914" />
                    </feComponentTransfer>
                </filter>
                <filter id="grain">
                    <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="4" stitchTiles="stitch" />
                    <feColorMatrix type="saturate" values="0" />
                    <feComponentTransfer>
                        <feFuncR type="linear" slope="2" intercept="-0.5" />
                        <feFuncG type="linear" slope="2" intercept="-0.5" />
                        <feFuncB type="linear" slope="2" intercept="-0.5" />
                    </feComponentTransfer>
                </filter>
            </svg>
            <div class="container">
                <img class="bg-photo" src="file://{abs_photo}" />
                <div class="gradient-overlay"></div>
                <img class="card-img" src="file://{abs_card}" />
            </div>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding='utf-8') as tf:
            tf.write(html)
            temp_html_path = tf.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1100, 'height': 1350}, device_scale_factor=2)
                page.goto(f"file://{os.path.abspath(temp_html_path)}", wait_until='networkidle')
                page.wait_for_timeout(500)
                page.screenshot(path=output_path)
                browser.close()
        finally:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
            
        return output_path

# Использование
# if __name__ == "__main__":
#     perf = PerformanceSummary()
#     perf.fetch_and_generate("20260310")