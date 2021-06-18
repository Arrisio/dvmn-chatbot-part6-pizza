import logging

from aiogram import Dispatcher, Bot, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher.filters import Regexp
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData
from more_itertools import chunked

import moltin_api
from settings import Settings

logger = logging.getLogger(__name__)

# settings объявляется здесь, т.к. требуется для создания объектов bot и dp, которые нужны для регистрации хандлеров
settings = Settings()
bot = Bot(settings.TG_BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = RedisStorage2(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=settings.REDIS_DB
)

dp = Dispatcher(bot, storage=storage)

class ApplicationState(StatesGroup):
    WAITING_EMAIL = State()


cb_add_to_cart = CallbackData("add_to_cart", "product_id")
cb_show_product_details = CallbackData("show_product_details", "product_id")
cb_remove_item_from_cart = CallbackData("remove_item_from_cart", "item_id")
cb_goto_main_menu = "goto_main_menu"
cb_goto_cart = "goto_cart"
cb_pay = "pay"


async def show_product_list(message: types.Message):
    product_list = await moltin_api.get_product_list()
    logger.debug("product list received")
    await message.answer(
        "Список товаров",
        reply_markup=InlineKeyboardMarkup(
            row_width=2,
            inline_keyboard=list(
                chunked(
                    [
                        InlineKeyboardButton(
                            text=product["name"],
                            callback_data=cb_show_product_details.new(product_id=product["id"]),
                        )
                        for product in product_list
                    ],
                    settings.MAX_BUTTONS_IN_ROW,
                )
            )
            + [[InlineKeyboardButton(text="Корзина", callback_data=cb_goto_cart)]],
        ),
    )


@dp.message_handler(CommandStart(), state="*")
async def handle_start(message: types.Message, state: FSMContext):
    await state.finish()
    await show_product_list(message=message)


@dp.callback_query_handler(text=cb_goto_main_menu)
async def show_product_list_cb(call: CallbackQuery, state: FSMContext):
    await show_product_list(call.message)
    await call.answer()


@dp.callback_query_handler(cb_show_product_details.filter())
async def show_product_details(call: CallbackQuery, callback_data: dict, state: FSMContext):
    logger.info(f"start showing product details | callback_data={callback_data}")

    product = await moltin_api.get_product_details(callback_data["product_id"])
    product_description = f"""<b>{product.get("name")}</b>\nЦена: {product['meta']['display_price']['with_tax']['formatted']}\n<i>{product.get("description")}</i>"""

    image_link = await moltin_api.get_product_main_image_link(product)

    await call.message.answer_photo(
        photo=image_link,
        caption=product_description,
        reply_markup=InlineKeyboardMarkup(
            row_width=2,
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1 кг", callback_data=cb_add_to_cart.new(product_id=product["id"])),
                    InlineKeyboardButton(text="5 кг", callback_data=cb_add_to_cart.new(product_id=product["id"])),
                    InlineKeyboardButton(text="10 кг", callback_data=cb_add_to_cart.new(product_id=product["id"])),
                ],
                [
                    InlineKeyboardButton(text="Показать корзину", callback_data=cb_goto_cart),
                    InlineKeyboardButton(text="К списку товаров", callback_data=cb_goto_main_menu),
                ],
            ],
        ),
    )
    await call.answer()


@dp.callback_query_handler(cb_add_to_cart.filter())
async def add_to_cart(
    call: CallbackQuery,
    callback_data: dict,
    state: FSMContext,
):
    logger.debug(f"start adding to cart | callback_data={callback_data}")
    try:
        await moltin_api.add_product_item_to_cart(user_id=call.from_user.id, product_id=callback_data["product_id"])
        await call.message.answer("товар добавлен")
        await show_product_list(message=call.message)
    except moltin_api.AddToCartException:
        await call.message.answer(
            "При добавлении товара в корзину произошла ошибка. Попробуйте позже или обратитесь в поддержку по тел. xxx"
        )
    finally:
        await call.answer()


@dp.callback_query_handler(text=cb_goto_cart)
async def show_cart_items(call: CallbackQuery):
    logger.debug("start adding to cart")
    cart_items = await moltin_api.get_cart_items(call.from_user.id)

    cart_items_description = "\n".join(
        [f"""<b>{item.get("name")}</b>\nКоличество: {item['quantity']}""" for item in cart_items]
    )
    cart_items_description += f"\n\n<b>Итого: {await moltin_api.get_cart_price(call.from_user.id)}</b>"

    logger.debug("cart items received")
    await call.message.answer(
        cart_items_description,
        reply_markup=InlineKeyboardMarkup(
            row_width=6,
            inline_keyboard=list(
                chunked(
                    [
                        InlineKeyboardButton(
                            text=f'Убрать из корзины {item["name"]}',
                            callback_data=cb_remove_item_from_cart.new(item_id=item["id"]),
                        )
                        for item in cart_items
                    ],
                    settings.MAX_BUTTONS_IN_ROW,
                )
            )
            + [
                [
                    InlineKeyboardButton(text="В меню", callback_data=cb_goto_main_menu),
                    InlineKeyboardButton(text="Оплатить", callback_data=cb_pay),
                ]
            ],
        ),
    )
    await call.answer()


@dp.callback_query_handler(cb_remove_item_from_cart.filter())
async def remove_item_from_cart(
    call: CallbackQuery,
    callback_data: dict,
):
    logger.debug(f"start removing item from cart | callback_data={callback_data}")

    await moltin_api.remove_item_from_cart(call.from_user.id, callback_data["item_id"])
    await call.message.answer("товар товар убран")
    await call.answer()


@dp.callback_query_handler(text=cb_pay)
async def pay(call: CallbackQuery):
    logger.debug("start pay")
    await ApplicationState.WAITING_EMAIL.set()
    await call.message.answer("Для оплаты пришлите ваш email")


@dp.message_handler(Regexp(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"), state=ApplicationState.WAITING_EMAIL)
async def receive_email(message: types.Message, state: FSMContext):
    try:
        await moltin_api.create_customer(
            customer_id=message.from_user.id, customer_email=message.text, customer_name=message.text
        )

        await message.answer(f"Вы прислали мне эту почту {message.text}")

    except moltin_api.CreateCustomerException:
        await message.answer(
            f"При записи вашего адреса произошла ошибка, но мы все равно впарим вам нашу рыбу, не беспокойтесь"
        )
    finally:
        await state.finish()
        await message.answer(f"Показать список товаров /start")


@dp.message_handler(state=ApplicationState.WAITING_EMAIL)
async def answer_if_sent_email_is_not_ok(message: types.Message):
    await message.answer(f"Присланный вами email некорректен")


async def on_startup(dp):
    await dp.bot.send_message(settings.TG_BOT_ADMIN_ID, "Бот Запущен и готов к работе!")


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
    )

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler(event_loop=dp.loop)
    scheduler.start()
    scheduler.add_job(lambda x: print(x), 'interval', kwargs={'x': '22'}, seconds=2, )
    scheduler.add_job(lambda x: print(x), 'interval', kwargs={'x': '33'}, seconds=3, )

    logger.info("telegram service started")
    executor.start_polling(dp, on_startup=on_startup)
    logger.info("service service stopped")
