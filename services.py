from typing import Optional

from geopy import Location, Point, distance, geocoders

import moltin_api
from schemas import Pizza, Pizzeria, Cart, Delivery, DeliveryType
from settings import Settings


async def get_pizzeria_list():
    pizzeria_entries = await moltin_api.get_flow_entries(flow_slug="pizzeria")
    return [
        Pizzeria(
            alias=pizzeria["Alias"],
            location=Location(
                address=pizzeria["Address"],
                point=Point(latitude=pizzeria["Latitude"], longitude=pizzeria["Longitude"]),
                raw="",
            ),
        )
        for pizzeria in pizzeria_entries
    ]


def get_location_by_address_string(
    address_string,
    geocoder: geocoders.Yandex = geocoders.Yandex(api_key=Settings().YANDEX_GEOCODER_APIKEY),
) -> Location:
    return geocoder.geocode(query=address_string, exactly_one=True)


async def get_nearest_pizzeria_and_distance(point: Point) -> tuple[Pizzeria, float]:
    pizzeria_list = await get_pizzeria_list()
    return min(
        [(pizzeria, distance.distance(pizzeria.location.point, point).km) for pizzeria in pizzeria_list],
        key=lambda x: x[1],
    )


DELIVERY_VARIANTS = {
    DeliveryType.PICKUP.value: Delivery(type=DeliveryType.PICKUP.value, price=0, name="Забрать самостоятельно"),
    DeliveryType.FREE_COURIER_DELIVERY.value: Delivery(
        type=DeliveryType.FREE_COURIER_DELIVERY.value, price=0, name="Бесплатная доставка курьером"
    ),
    DeliveryType.COURIER_DELIVERY_FOR_100.value: Delivery(
        type=DeliveryType.COURIER_DELIVERY_FOR_100.value, price=100, name="Доставка курьером за 100р."
    ),
    DeliveryType.COURIER_DELIVERY_FOR_300.value: Delivery(
        type=DeliveryType.COURIER_DELIVERY_FOR_300.value, price=300, name="Доставка курьером за 300р."
    ),
}


def get_delivery_variants(delivery_distance: float):
    if delivery_distance < 0.5:
        return [
            DELIVERY_VARIANTS[DeliveryType.PICKUP.value],
            DELIVERY_VARIANTS[DeliveryType.FREE_COURIER_DELIVERY.value],
        ]

    if delivery_distance < 5:
        return [DELIVERY_VARIANTS[DeliveryType.COURIER_DELIVERY_FOR_100.value]]

    if delivery_distance < 20:
        return [DELIVERY_VARIANTS[DeliveryType.COURIER_DELIVERY_FOR_300.value]]

    return [DELIVERY_VARIANTS[DeliveryType.PICKUP.value]]
