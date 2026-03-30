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
        #self.overlay_logo_url = "https://content.sportslogos.net/logos/6/981/full/_nba_playoffs_logo_primary_2022_sportslogosnet-4785.png"
        self.overlay_logo_url = ""

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
        pm_impact = 0.4 * pm * (mins / 48.0)

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

    def _generate_html(self, p, date_str, team_logo, home_data, away_data, rating):
        s = p['stats']

        # Parse basic stats safely
        def parse_stat(key):
            try:
                val = s.get(key, '0')
                return int(val) if val and val.isdigit() else 0
            except:
                return 0

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
        tgm, tga = 0, 0
        if '/' in tg_str:
            parts = tg_str.split('/')
            tgm, tga = int(parts[0]), int(parts[1])

        ft_str = s.get('freeThrowsMade-freeThrowsAttempted', '0-0').replace('-', '/')
        ftm, fta = 0, 0
        if '/' in ft_str:
            parts = ft_str.split('/')
            ftm, fta = int(parts[0]), int(parts[1])

        # Advanced stats
        ts_denom = (2 * (fga + 0.44 * fta))
        ts_pct = round((pts / ts_denom * 100) if ts_denom > 0 else 0, 1)
        fps = round(pts + 1.2*reb + 1.5*ast + 3*stl + 3*blk - tov)
        
        # Color coding for +/-
        pm_color = "var(--accent)"
        if pm and pm != '0':
            if pm.startswith('+'): pm_color = "#41A67E"
            elif pm.startswith('-'): pm_color = "#A63A2F"

        # Color coding for Score Badge
        try:
            r_val = float(rating)
        except:
            r_val = 0.0
            
        score_bg = "#A63A2F" # <= 6: Red
        if r_val >= 9: score_bg = "#0068B9" # 9+: Deep Blue
        elif r_val >= 8: score_bg = "#00929C" # 8-9: Cyan Blue
        elif r_val >= 7: score_bg = "#41A67E" # 7-8: Green
        elif r_val > 6: score_bg = "#BF8B33" # 6-7: Orange

        short_name = p["shortName"]

        # Dynamic Primary Stats (PTS always first, then 2 best >=3 from REB/AST/STL/BLK, then FG% fallback)
        top_stats = [{'val': pts, 'lbl': 'pts'}]
        candidates = [
            {'val': reb, 'lbl': 'reb'},
            {'val': ast, 'lbl': 'ast'},
            {'val': stl, 'lbl': 'stl'},
            {'val': blk, 'lbl': 'blk'}
        ]
        qualifying = sorted([c for c in candidates if c['val'] >= 3], key=lambda x: x['val'], reverse=True)
        top_stats.extend(qualifying[:2])
        
        if len(top_stats) < 3 and fg_pct >= 50.0:
            top_stats.append({'val': f"{fg_pct}%", 'lbl': 'fg%'})
        
        primary_stats_html = "".join([
            f'<div class="big-stat"><span class="val">{s["val"]}</span><span class="lbl">{s["lbl"]}</span></div>'
            for s in top_stats[:3]
        ])

        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            formatted_date = date_obj.strftime("%B %d, %Y").upper()
        except:
            formatted_date = date_str

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
                        background: var(--score-bg); 
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
                        background: #e6e2d6;
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
                        height: 150px;
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
                                <div class="name-line" style="--score-bg: {score_bg}">
                                    <span class="name">{short_name}</span>
                                    <div class="score-badge">{"%.2f" % rating}</div>
                                </div>
                                <div class="primary-stats">
                                    {primary_stats_html}
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
                                <span style="font-weight: 900; color: var(--text-muted); margin: 0 4px; font-size: 14px;">VS</span>
                            </span>
                            <img src="{away_data['logo']}" class="matchup-logo">
                        </div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-col"><span class="s-val">{mins}</span><span class="s-lbl">MIN</span></div>
                        <div class="stat-col"><span class="s-val">{pts}</span><span class="s-lbl">PTS</span></div>
                        <div class="stat-col"><span class="s-val">{reb}</span><span class="s-lbl">REB</span></div>
                        <div class="stat-col"><span class="s-val">{ast}</span><span class="s-lbl">AST</span></div>
                        <div class="stat-col"><span class="s-val">{stl}</span><span class="s-lbl">STL</span></div>
                        <div class="stat-col"><span class="s-val">{blk}</span><span class="s-lbl">BLK</span></div>
                        <div class="stat-col"><span class="s-val" style="color: {pm_color};">{pm}</span><span class="s-lbl">+/-</span></div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-col"><span class="s-val">{fg_pct}</span><span class="s-lbl">FG%</span></div>
                        <div class="stat-col"><span class="s-val">{fg_str}</span><span class="s-lbl">FG</span></div>
                        <div class="stat-col"><span class="s-val">{tg_str}</span><span class="s-lbl">3FG</span></div>
                        <div class="stat-col"><span class="s-val">{ft_str}</span><span class="s-lbl">FTS</span></div>
                        <div class="stat-col"><span class="s-val">{tov}</span><span class="s-lbl">TO</span></div>
                        <div class="stat-col"><span class="s-val">{pf}</span><span class="s-lbl">PF</span></div>
                        <div class="stat-col"><span class="s-val">{ts_pct}</span><span class="s-lbl">TS%</span></div>
                    </div>
                </div>
            </body>
            </html>
        """
        return html_content

    def fetch_and_generate(self, date_str):
        print(f"Загрузка матчей за {date_str}...")
        scoreboard = requests.get(f"{self.api_base}/scoreboard?dates={date_str}").json()
        
        best_player = None # To track MVP of the Day

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)

            for event in scoreboard.get('events', []):
                game_id = event['id']
                summary = requests.get(f"{self.api_base}/summary?event={game_id}").json()
                
                if not summary.get('boxscore', {}).get('teams'): continue

                # Identify Home and Away
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

                        # Calculate FPS for tiebreaker and MVP display
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

                        # Tracking best player (MVP)
                        # Comparison: Rating first, then FPS tiebreaker
                        if best_player is None or (rating, fps) > (best_player['rating'], best_player['fps']):
                            best_player = {
                                'name': athlete['athlete']['displayName'],
                                'team': team_name,
                                'rating': rating,
                                'fps': fps,
                                'pts': f_pts,
                                'reb': f_reb,
                                'ast': f_ast,
                                'stl': f_stl
                            }
                        
                        # Generate cards only if they hit the threshold
                        if rating < 6.5: continue

                        player_data = {
                            'name': athlete['athlete']['displayName'],
                            'shortName': athlete['athlete']['shortName'],
                            'headshot': athlete['athlete'].get('headshot', {}).get('href', 'https://a.espncdn.com/i/headshots/nophoto.png'),
                            'stats': stats_dict
                        }


                        print(f"Генерация: {player_data['name']} ({rating} score)")
                        html = self._generate_html(player_data, date_str, team_logo, home_data, away_data, rating)
                        page.set_content(html)
                        
                        game_folder = os.path.join(self.output_dir, f"{home_data['abbrev']}_vs_{away_data['abbrev']}")
                        os.makedirs(game_folder, exist_ok=True)
                        safe_name = player_data['name'].replace(' ', '_').replace("'", "")
                        page.locator(".player-card").screenshot(path=f"{game_folder}/{safe_name}.png")

            browser.close()
            print("Готово!")
            return best_player # Return the MVP identifying info

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
                <div class="grain-overlay"></div>
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