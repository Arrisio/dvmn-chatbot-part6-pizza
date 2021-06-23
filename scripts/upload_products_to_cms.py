import asyncio
from sys import platform
import httpx

import moltin_api

async def main():

    for pizza in httpx.get("https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json").json():
        await moltin_api.create_product(
            name=pizza['name'],
            description=pizza['description'],
            price=pizza['price'],
            slug=pizza['id'],
            sku=pizza['id'],
        )



if __name__ == '__main__':
    if platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Не работает, т.к. Moltin всегда возвращает 403 ошибку
    asyncio.run(main())