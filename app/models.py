from pydantic import BaseModel, validator

from app import MAX_ENGINES, MAX_HEIGHT, MIN_ENGINES, MIN_HEIGHT


class RocketBase(BaseModel):
    num_engines: int
    height: int

    @validator('num_engines')
    def engines_in_range(cls, v):
        if v < MIN_ENGINES:
            raise ValueError('You cant have that many engines!')
        if v > MAX_ENGINES:
            raise ValueError('Too many engines!')
        return v

    @validator('height')
    def height_in_range(cls, v):
        if v < MIN_HEIGHT:
            raise ValueError('Rocket is not tall enough')
        if v > MAX_HEIGHT:
            raise ValueError('Rocket is too tall')
        return v


class Rocket(RocketBase):
    id: str
    fuel: float
    altitude: float = 0
    velocity: float = 0
    crashed: bool = False
    launched: bool = False
    max_altitude: float = 0
