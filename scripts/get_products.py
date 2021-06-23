import asyncio
import sys

import anyio
from services import get_pizza_list
from loguru import logger

async def main():
    product_list = await get_pizza_list()
    print(product_list)
    # print(product_list[0].get_image_link())
    # print(await product_list[0].get_image_link())
    # print(await product_list[0].get_image_link())
    logger.debug('start image1')
    print(product_list[0].image_link)
    print(await product_list[0].image_link)
    logger.debug('fimish image1')
    logger.debug('start image2')
    print(await product_list[0].image_link)
    logger.debug('fimish image2')
    # print(product_list[0].get_image_link())



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