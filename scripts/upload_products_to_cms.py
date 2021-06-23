import asyncio
import sys
import httpx
import anyio

from loguru import logger
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
    logger.configure(**{
        "handlers": [
            {
                "sink": sys.stdout,
                "level": "DEBUG",
                "format": "<level>{level: <8} {time:YYYY-MM-DD HH:mm:ss.SSS}</level>|<cyan>{name:<12}</cyan>:<cyan>{function:<24}</cyan>:<cyan>{line}</cyan> - <level>{message:>32}</level> |{extra}",
            },
        ],
    })
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())