import sys
sys.path.append('src')
from playoff_bracket import PlayoffBracket

pb = PlayoffBracket()
seeds, series_data = pb.get_data()

print("West Seeds:")
for s, t in seeds['west'].items():
    print(f"Seed {s}: {t['name']} (ID: {t['id']})")

print("\nSeries Data:")
for k, v in series_data.items():
    print(f"{k}: {v}")

def parse(summary, t1, t2):
    return pb._parse_series_score(summary, t1, t2)

print(parse("Series tied 0-0", "Timberwolves", "MIN"))
