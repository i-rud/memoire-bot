from nba_api.stats.endpoints.playerprofilev2 import PlayerProfileV2

class CareerHighs:
    def __init__(self):
        pass

    def get_career_highs(self, player_id: str):
        player_profile = PlayerProfileV2(player_id=player_id)
        career_highs = player_profile.career_highs.get_data_frame()
        return career_highs

    def generate(self, player_id: str):
        career_highs = self.get_career_highs(player_id)
        print(career_highs)


if __name__ == "__main__":
    career_highs = CareerHighs()
    career_highs.generate("1966")