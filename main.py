from pymongo import MongoClient
import requests
import yaml


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


class DataSetup:
    def __init__(self, teams):
        self.teams = teams
        self.db = Database()
        self.db.database.drop_collection("raw")

    def save_raw_matches_data(self, matches_data):
        for match_data in matches_data:
            blue_document = {}
            red_document = {}

            if (breakdown := match_data.get("score_breakdown")) is not None:
                if (alliances := match_data.get("alliances")) is not None:
                    blue_breakdown = breakdown["blue"]
                    red_breakdown = breakdown["red"]

                    blue_team_keys = alliances["blue"]["team_keys"]
                    red_team_keys = alliances["red"]["team_keys"]

                    blue_document["teams"] = blue_team_keys
                    red_document["teams"] = red_team_keys

                    blue_document.update(blue_breakdown)
                    red_document.update(red_breakdown)

                    self.db.raw.insert_many(
                        [blue_document, red_document]
                    )

    def pull_data_from_team(self, team_num):
        url = f"team/{team_num}/matches/2017"
        puller = Puller(url)
        matches_data = puller.request()
        self.save_raw_matches_data(matches_data)

    def setup_data(self):
        self.db.database.drop_collection("raw")

        for team_num in self.teams:
            print(team_num)
            self.pull_data_from_team(team_num)


class Calculations:
    def __init__(self, team_num):
        self.team_num = team_num
        self.db = Database()
        self.data = self.get_data_for_teams()
        self.write()

    def get_data_for_teams(self):
        return [x for x in self.db.raw.find({"teams":{"$in":[self.team_num]}})]

    def get_averages(self):
        averages = {"team": self.team_num}
        data_fields = [
            "autoFuelHigh",
            "autoFuelLow",
            "autoFuelPoints",
            "autoPoints"
        ]
        for field in data_fields:
            calc = self.get_average(self.data, field)
            averages[field] = calc
        return averages

    def get_average(self, data: list, field: str):
        total = 0
        for tim in data:
            total += tim[field]
        return total / len(data)

    def write(self):
        self.db.calculated.insert_one(self.get_averages())


if __name__ == "__main__":
    db = Database()
    event_key = input("Event key: ")
    puller = Puller(f"event/{event_key}/teams/keys")
    teams = puller.request()
    print(teams)

    setup_data = input("Setup data: [Y/n]: ")
    if setup_data.upper() == "Y":
        setup = DataSetup(teams)
        setup.setup_data()

    calc_data = input("Calculate data: [Y/n]: ")
    if calc_data.upper() == "Y":
        db.database.drop_collection("calculated")
        for x in teams:
            print(x)
            Calculations(x)
