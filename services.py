from schemas import Product
import moltin_api


async def get_product_list() -> list[Product]:
    product_dto_list = await moltin_api.get_product_list()
    p = [Product(**product_dto) for product_dto in product_dto_list]
    return p
