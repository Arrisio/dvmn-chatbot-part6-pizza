from dataclasses import dataclass
from enum import Enum

import geopy


@dataclass
class Pizza:
    id: str
    name: str
    description: str
    price: float
    display_price: str

    image_file_id: str


@dataclass
class Pizzeria:
    alias: str
    location: geopy.Location


@dataclass
class PizzaCartItem:
    id: str
    pizza_id: str
    name: str
    description: str
    cost: float
    display_cost: str
    quantity: int
    unit_price: float
    image_file_link: str


@dataclass
class Cart:
    user_id: str
    pizza_cart_items: list[PizzaCartItem]
    price: float
    display_price: str


class DeliveryType(Enum):
    PICKUP = "PICKUP"
    FREE_COURIER_DELIVERY = "FREE_COURIER_DELIVERY"
    COURIER_DELIVERY_FOR_100 = "COURIER_DELIVERY_FOR_100"
    COURIER_DELIVERY_FOR_300 = "COURIER_DELIVERY_FOR_300"


@dataclass
class Delivery:
    type: DeliveryType
    name: str
    price: float

