import logging
from datetime import datetime
from typing import Optional, List

import httpx

from schemas import Pizza as Product, PizzaCartItem as CartItem, Cart
from settings import MoltinSettings

# наличие всех параметров MoltenSettings обязательно для работы этого модуля. Поэтому считаю оправданным объявлени settings в этом месте
settings = MoltinSettings()

logger = logging.getLogger(__name__)

MOLTIN_AUTH_DATA: dict = {}
MOLTIN_SESSION: httpx.AsyncClient = httpx.AsyncClient(http2=True, base_url=settings.MOLTIN_URL)


async def refresh_auth_data():
    global MOLTIN_AUTH_DATA
    response = await MOLTIN_SESSION.post(
        url="/oauth/access_token",
        data={"client_id": settings.MOLTIN_CLIENT_ID, "grant_type": "implicit"},
    )
    response.raise_for_status()
    MOLTIN_AUTH_DATA = response.json()
    logger.info(f"molten auth data successfully refreshed {MOLTIN_AUTH_DATA}")


class MoltenAuth(httpx.Auth):
    async def async_auth_flow(self, request, token_expires_preservation_sec=10):
        global MOLTIN_AUTH_DATA

        if (
            not MOLTIN_AUTH_DATA
            or datetime.utcfromtimestamp(MOLTIN_AUTH_DATA["expires"] - token_expires_preservation_sec)
            < datetime.utcnow()
        ):
            await refresh_auth_data()

        request.headers["Authorization"] = f"Bearer {MOLTIN_AUTH_DATA['access_token']}"
        response = yield request

        if response.status_code == 401:
            logger.error("auth receive 401 code. trying again...")
            await refresh_auth_data()

            request.headers["Authorization"] = f"Bearer {MOLTIN_AUTH_DATA['access_token']}"
            yield request


async def create_product(
    name: str,
    price: float,
    description: str,
    sku: Optional[str] = None,
    slug: Optional[str] = None,
    mange_stock: Optional[bool] = False,
    commodity_type: Optional[str] = "physical",
    status: Optional[str] = "live",
):
    """
    https://documentation.elasticpath.com/commerce-cloud/docs/api/catalog/products/create-a-product.html
    """

    response = await MOLTIN_SESSION.post(
        f"/v2/products",
        auth=MoltenAuth(),
        json={
            "type": "product",
            "name": name,
            "sku": sku,
            "slug": slug,
            "description": description,
            "status": status,
            "commodity_type": commodity_type,
            "mange_stock": mange_stock,
            "price": [{"amount": price, "currency": "RUB", "includes_tax": True}],
        },
    )
    response.raise_for_status()
    logger.debug("product list received")
    return response.json()["data"]


async def get_product_list() -> list[Product]:
    response = await MOLTIN_SESSION.get(
        f"/v2/products",
        auth=MoltenAuth(),
    )
    """
        https://documentation.elasticpath.com/commerce-cloud/docs/api/catalog/products/get-all-products.html
    """
    logger.debug("product list received")
    return [
        Product(
            id=product["id"],
            name=product["name"],
            description=product["description"],
            price=product["price"][0]["amount"],
            display_price=product["meta"]["display_price"]["with_tax"]["formatted"],
            _image_file_id=product["relationships"].get("main_image", {}).get("data", {}).get("id"),
        )
        for product in response.json()["data"]
    ]


async def get_product_details(product_id: str) -> Product:
    response = await MOLTIN_SESSION.get(
        f"/v2/products/{product_id}",
        auth=MoltenAuth(),
    )
    """
        https://documentation.elasticpath.com/commerce-cloud/docs/api/catalog/products/get-all-products.html
    """
    logger.debug("product list received")
    response.raise_for_status()
    product = response.json()["data"]
    return Product(
        id=product["id"],
        name=product["name"],
        description=product["description"],
        price=product["price"][0]["amount"],
        display_price=product["meta"]["display_price"]["with_tax"]["formatted"],
        _image_file_id=product["relationships"].get("main_image", {}).get("data", {}).get("id"),
    )


async def get_product_main_image_link(main_image_id: str) -> str:
    response = await MOLTIN_SESSION.get(
        url=f"https://api.moltin.com/v2/files/{main_image_id}",
        auth=MoltenAuth(),
    )
    response.raise_for_status()
    logger.debug("product image link received")
    return response.json()["data"]["link"]["href"]


class AddToCartException(Exception):
    pass


async def add_product_item_to_cart(user_id: str, product_id: str):
    try:
        response = await MOLTIN_SESSION.post(
            f"/v2/carts/{user_id}/items",
            auth=MoltenAuth(),
            json={"data": {"id": product_id, "type": "cart_item", "quantity": 1}},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as err:
        logger.error(err)
        raise AddToCartException


async def get_cart_items(user_id: str) -> Cart:
    response = await MOLTIN_SESSION.get(
        f"/v2/carts/{user_id}/items",
        auth=MoltenAuth(),
    )
    response.raise_for_status()

    result = response.json()
    return Cart(
        user_id=user_id,
        display_price=result["meta"]["display_price"]["with_tax"]["formatted"],
        price=result["meta"]["display_price"]["with_tax"]["amount"],
        pizza_cart_items=[
            CartItem(
                id=item["id"],
                pizza_id=item["product_id"],
                description=item["description"],
                quantity=item["quantity"],
                cost=item["value"]["amount"],
                display_cost=item["meta"]["display_price"]["with_tax"]["value"]["formatted"],
                unit_price=item["unit_price"]["amount"],
                name=item["name"],
                image_file_link=item.get("image", {}).get("href"),
            )
            for item in result["data"]
        ],
    )


async def remove_item_from_cart(user_id: str, item_id: str):
    response = await MOLTIN_SESSION.delete(
        f"/v2/carts/{user_id}/items/{item_id}",
        auth=MoltenAuth(),
    )
    response.raise_for_status()


class CreateCustomerException(Exception):
    pass


async def create_customer(customer_id: str, customer_name: str, customer_email: str):
    try:
        response = await MOLTIN_SESSION.post(
            url=f"/v2/customers/{customer_id}",
            auth=MoltenAuth(),
            json={
                "data": {
                    "type": "customer",
                    "name": customer_name,
                    "email": customer_email,
                }
            },
        )
        if not response.status_code != 409:  # 409 возвращается, если клиент уже существует, что не является ошибкой
            response.raise_for_status()
    except httpx.HTTPStatusError as err:
        logger.error(err)
        raise CreateCustomerException


async def get_flow_entries(flow_slug) -> List[dict]:
    response = await MOLTIN_SESSION.get(url=f"/v2/flows/{flow_slug}/entries", auth=MoltenAuth())
    response.raise_for_status()
    return response.json()["data"]
