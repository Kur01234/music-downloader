from typing import Dict, List
from dataclasses import dataclass
from collections import defaultdict
from urllib.parse import urlparse

from ..utils import cli_function

from ...objects import Country
from ...utils import config, write_config
from ...utils.config import youtube_settings
from ...connection import Connection


@dataclass
class Instance:
    """
    Attributes which influence the quality of an instance:
    
    - users
    """
    name: str
    uri: str
    regions: List[Country]
    users: int = 0
    
    def __str__(self) -> str:
        return f"{self.name} with {self.users} users."
    
    
class FrontendInstance:
    SETTING_NAME = "placeholder"
    
    def __init__(self) -> None:
        self.region_instances: Dict[Country, List[Instance]] = defaultdict(list)
        self.all_instances: List[Instance] = []
        
    def add_instance(self, instance: Instance):
        self.all_instances.append(instance)
        
        youtube_lists = youtube_settings["youtube_url"]
        existing_netlocs = set(tuple(url.netloc for url in youtube_lists))

        parsed_instance = urlparse(instance.uri)
        instance_netloc = parsed_instance.netloc
        
        if instance_netloc not in existing_netlocs:
            youtube_lists.append(parsed_instance)
            youtube_settings.__setitem__("youtube_url", youtube_lists, is_parsed=True)
        
        for region in instance.regions:
            self.region_instances[region].append(instance)
        
    def fetch(self, silent: bool = False):
        if not silent:
            print(f"Downloading {type(self).__name__} instances...")
            
    def set_instance(self, instance: Instance):
        youtube_settings.__setitem__(self.SETTING_NAME,  instance.uri)
    
    def _choose_country(self) -> List[Instance]:
        print("Input the country code, an example would be \"US\"")
        print('\n'.join(f'{region.name} ({region.alpha_2})' for region in self.region_instances))
        print()
        
        
        available_instances = set(i.alpha_2 for i in self.region_instances)
        
        chosen_region = ""
        
        while chosen_region not in available_instances:
            chosen_region = input("nearest country: ").strip().upper()
        
        return self.region_instances[Country.by_alpha_2(chosen_region)]
    
    def choose(self, silent: bool = False):
        instances = self.all_instances if silent else self._choose_country()
        instances.sort(key=lambda x: x.users, reverse=True)
        
        if silent:
            self.set_instance(instances[0])
            return
        
        # output the options
        print("Choose your instance (input needs to be a digit):")
        for i, instance in enumerate(instances):
            print(f"{i}) {instance}")
        
        print()
        
        # ask for index
        index = ""
        while not index.isdigit() or int(index) >= len(instances):
            index = input("> ").strip()
        
        instance = instances[int(index)]
        print()
        print(f"Setting the instance to {instance}")
        
        self.set_instance(instance)

    
class Invidious(FrontendInstance):
    SETTING_NAME = "invidious_instance"
    
    def __init__(self) -> None:
        self.connection = Connection(host="https://api.invidious.io/")
        self.endpoint = "https://api.invidious.io/instances.json"
        
        super().__init__()

        
    def _process_instance(self, all_instance_data: dict):
        instance_data = all_instance_data[1]
        stats = instance_data["stats"]
        
        if not instance_data["api"]:
            return
        if instance_data["type"] != "https":
            return 
        
        region = instance_data["region"]
        
        instance = Instance(
            name=all_instance_data[0],
            uri=instance_data["uri"],
            regions=[Country.by_alpha_2(region)],
            users=stats["usage"]["users"]["total"]
        )
        
        self.add_instance(instance)
    
    def fetch(self, silent: bool):
        r = self.connection.get(self.endpoint)
        if r is None:
            return

        for instance in r.json():
            self._process_instance(all_instance_data=instance)
            

class Piped(FrontendInstance):
    SETTING_NAME = "piped_instance"
    
    def __init__(self) -> None:
        self.connection = Connection(host="https://raw.githubusercontent.com")
        
        super().__init__()
        
    def process_instance(self, instance_data: str):
        cells = instance_data.split(" | ")
        
        instance = Instance(
            name=cells[0].strip(),
            uri=cells[1].strip(),
            regions=[Country.by_emoji(flag) for flag in cells[2].split(", ")]
        )
        
        self.add_instance(instance)
        
    def fetch(self, silent: bool = False):  
        r = self.connection.get("https://raw.githubusercontent.com/wiki/TeamPiped/Piped-Frontend/Instances.md")
        if r is None:
            return
        
        process = False
        
        for line in r.content.decode("utf-8").split("\n"):
            line = line.strip()
            
            if line != "" and process:
                self.process_instance(line)
            
            if line.startswith("---"):
                process = True


class FrontendSelection:
    def __init__(self):
        self.invidious = Invidious()
        self.piped = Piped()
    
    def choose(self, silent: bool = False):
        self.invidious.fetch(silent)
        self.invidious.choose(silent)
        
        self.piped.fetch(silent)
        self.piped.choose(silent)


@cli_function
def set_frontend(silent: bool = False):
    shell = FrontendSelection()
    shell.choose(silent=silent)
    
    return 0
    