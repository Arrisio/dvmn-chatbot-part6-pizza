from typing import Optional, Union
from dataclasses import dataclass
import anyio
import asyncio
from async_property import async_cached_property, AwaitLoader
from pydantic import BaseModel, HttpUrl, UUID4, PrivateAttr
from uuid import uuid4
from loguru import logger

import moltin_api

@dataclass
class Product(AwaitLoader):
    id: Union[int, str]
    name: str
    description: str
    price: float
    display_price: str
    moltin_id: uuid4 = None

    _moltin_product_data: dict = None


    @async_cached_property
    async def image_link(self) -> str:
        logger.debug('downloading image')
        return await moltin_api.get_product_main_image_link(self._moltin_product_data)

        # loop.a
        # with anyio.create_task_group() as tg:
        #     r = tg.r
        # return r


