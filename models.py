# The Data Classes
from dataclasses import dataclass

@dataclass
class FlareTunnel:
    name: str;
    description: str;
    localhost: str;
    flarelink: str;
    accesslink: str;

    