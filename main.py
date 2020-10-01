from pymongo import MongoClient
import requests
import yaml
import pprint
import time


class Config:
    def __init__(self, path="config.yml"):
        self.path = path
        self.config = self.get_config()
        self.key = self.config["key"]

    def get_config(self):
        config_file = open(self.path)
        config = yaml.load(config_file, Loader=yaml.FullLoader)
        return config


class Database:
    def __init__(self, location: str = "localhost", port: int = 27017):
        """Set default location and port"""
        self.location = location
        self.port = port
        self.connect()

    def connect(self):
        """Make client, database, and collection"""
        self.client = MongoClient(self.location, self.port)
        self.database = self.client.blue_allience
        self.raw = self.database.raw
        self.calculated = self.database.calculated


class Puller:
    def __init__(self, url: str):
        self.config = Config()
        self.url = url
        self.full_url = f"https://www.thebluealliance.com/api/v3/{self.url}"
        self.request_headers = {"X-TBA-Auth-Key": self.config.key}

    def request(self):
        request = requests.get(self.full_url, headers=self.request_headers)
        return request.json()


def team(team_num):
    database = Database()

    url = f"team/frc{team_num}/matches/2017"
    puller = Puller(url)
    matches_data = puller.request()

    all_data = []

    for match_data in matches_data:
        blue_document = {}
        red_document = {}

        if (breakdown := match_data.get("score_breakdown")) is not None:
            if (alliances := breakdown.get("alliances")) is not None:
                blue_breakdown = breakdown["blue"]
                red_breakdown = breakdown["red"]

                blue_team_keys = alliances["blue"]
                red_team_keys = alliances["red"]

                blue_document["team_keys"] = blue_team_keys
                red_document["team_keys"] = red_team_keys

                blue_document.update(blue_breakdown)
                red_document.update(red_breakdown)


teams_nums = [1678, 254, 116, 118, 253]

for team_num in teams_nums:
    team(team_num)
