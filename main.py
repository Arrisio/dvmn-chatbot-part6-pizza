from datetime import datetime, timedelta

from aiogram.types import LabeledPrice
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from geopy import Point

from schemas import DeliveryType
from delivery_tools import DELIVERY_VARIANTS

from aiogram import Dispatcher, Bot, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart
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
import delivery_tools
from settings import Settings


def format_tg_message(message_template: str, **kwarg) -> str:
    for param_name, param_value in kwarg.items():
        message_template = message_template.replace(
            "{" + param_name + "}", str(param_value).replace(">", "&#62;").replace("<", "&#60")
        )
    return message_template


# settings объявляется здесь, т.к. требуется для создания объектов bot и dp, которые нужны для регистрации хандлеров
settings = Settings()
bot = Bot(settings.TG_BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = RedisStorage2(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=settings.REDIS_DB
)
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler(event_loop=dp.loop)


class OrderState(StatesGroup):
    WAITING_ADDRESS = State()
    WAITING_CHOOSING_DELIVERY_TYPE = State()


cb_add_to_cart = CallbackData("add_to_cart", "pizza_id")
cb_show_product_details = CallbackData("show_product_details", "pizza_id")
cb_remove_item_from_cart = CallbackData("remove_item_from_cart", "pizza_item_id")
cb_goto_main_menu = "goto_main_menu"
cb_goto_cart = "goto_cart"
cb_send_invoice = "send_invoice"
cb_request_coordinates = "request_coordinates"
cb_delivery_type = CallbackData(
    "cb_delivery_type",
    "delivery_type",
)


async def show_pizza_list(message: types.Message):
    await message.answer(
        "Список товаров",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                *chunked(
                    [
                        InlineKeyboardButton(
                            text=pizza.name,
                            callback_data=cb_show_product_details.new(pizza_id=pizza.id),
                        )
                        for pizza in await moltin_api.get_product_list()
                    ],
                    settings.MAX_BUTTONS_IN_ROW,
                ),
                [InlineKeyboardButton(text="Корзина", callback_data=cb_goto_cart)],
            ],
        ),
    )


@dp.message_handler(CommandStart(), state="*")
async def handle_start(message: types.Message, state: FSMContext):
    await state.finish()
    await show_pizza_list(message=message)


@dp.callback_query_handler(text=cb_goto_main_menu)
async def show_pizza_list_cb(call: CallbackQuery, state: FSMContext):
    await show_pizza_list(call.message)
    await call.answer()


@dp.callback_query_handler(cb_show_product_details.filter())
async def show_pizza_details(call: CallbackQuery, callback_data: dict, state: FSMContext):
    pizza = await moltin_api.get_product_details(product_id=callback_data["pizza_id"])

    await call.message.answer_photo(
        photo=await moltin_api.get_product_main_image_link(pizza.image_file_id),
        caption=format_tg_message(
            "<b>{pizza_name}</b>\nЦена: {pizza_display_price}\n<i>{pizza_description}</i>",
            pizza_name=pizza.name,
            pizza_display_price=pizza.display_price,
            pizza_description=pizza.description,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Положить в корзину", callback_data=cb_add_to_cart.new(pizza_id=pizza.id)
                    ),
                ],
                [
                    InlineKeyboardButton(text="Корзина", callback_data=cb_goto_cart),
                    InlineKeyboardButton(text="Назад", callback_data=cb_goto_main_menu),
                ],
            ],
        ),
    )
    await call.answer()


@dp.callback_query_handler(cb_add_to_cart.filter())
async def add_to_cart(call: CallbackQuery, callback_data: dict):
    try:
        await moltin_api.add_product_item_to_cart(user_id=call.from_user.id, product_id=callback_data["pizza_id"])
        await call.message.answer("Пицца добавлена!")
        await show_pizza_list(message=call.message)
    except moltin_api.AddToCartException:
        await call.message.answer(
            "При добавлении товара в корзину произошла ошибка. Попробуйте позже или обратитесь в поддержку по тел. xxx"
        )
    finally:
        await call.answer()


@dp.callback_query_handler(text=cb_goto_cart)
async def show_cart_items(call: CallbackQuery):
    cart = await moltin_api.get_cart_items(user_id=call.from_user.id)

    cart_items_description = "\n".join(
        [
            format_tg_message(
                "<b>{pizza_name}</b>\nКоличество: {pizza_description}\n{pizza_quantity} в корзине на сумму {pizza_display_cost}",
                pizza_name=pizza.name,
                pizza_description=pizza.description,
                pizza_quantity=pizza.quantity,
                pizza_display_cost=pizza.display_cost,
            )
            for pizza in cart.pizza_cart_items
        ]
    )
    cart_items_description += f"\n\n------------------\n<b>К оплате: {cart.display_price}</b>"

    await call.message.answer(
        cart_items_description,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                *chunked(
                    [
                        InlineKeyboardButton(
                            text=f"Убрать из корзины {pizza_item.name}",
                            callback_data=cb_remove_item_from_cart.new(pizza_item_id=pizza_item.id),
                        )
                        for pizza_item in cart.pizza_cart_items
                    ],
                    settings.MAX_BUTTONS_IN_ROW,
                ),
                [
                    InlineKeyboardButton(text="В меню", callback_data=cb_goto_main_menu),
                    InlineKeyboardButton(text="Оплатить", callback_data=cb_request_coordinates),
                ],
            ]
        ),
    )
    await call.answer()


@dp.callback_query_handler(cb_remove_item_from_cart.filter())
async def remove_pizza_item_from_cart(
    call: CallbackQuery,
    callback_data: dict,
):
    await moltin_api.remove_item_from_cart(user_id=call.from_user.id, item_id=callback_data["pizza_item_id"])
    await call.message.answer("Пиццу убрали из корзины")
    await call.answer()


@dp.callback_query_handler(text=cb_request_coordinates)
async def request_customer_coordinates(
    call: CallbackQuery,
):
    await call.answer()
    await OrderState.WAITING_ADDRESS.set()

    await call.message.answer("В ответном сообщении пришлите свой адрес или координаты(с сотового)")


@dp.message_handler(content_types=types.ContentType.LOCATION, state=OrderState.WAITING_ADDRESS)
async def handle_incoming_coordinates(message: types.Message, state: FSMContext):
    nearest_pizzeria, distance = await delivery_tools.get_nearest_pizzeria_and_distance(
        point=Point(latitude=message.location.latitude, longitude=message.location.longitude)
    )
    variants = delivery_tools.get_delivery_variants(delivery_distance=distance)
    await message.answer(
        "выберите вариант доставки",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        variant.name,
                        callback_data=cb_delivery_type.new(delivery_type=variant.type),
                    )
                ]
                for variant in variants
            ]
        ),
    )
    await OrderState.next()


@dp.message_handler(state=OrderState.WAITING_ADDRESS)
async def handle_incoming_address(message: types.Message, state: FSMContext):

    if not (customer_location := delivery_tools.get_location_by_address_string(address_string=message.text)):
        await message.answer("не могу найти локацию")
        return

    nearest_pizzeria, distance = await delivery_tools.get_nearest_pizzeria_and_distance(point=customer_location.point)

    await state.update_data(
        pizzeria_address=nearest_pizzeria.location.address,
        customer_longitude=customer_location.point.longitude,
        customer_latitude=customer_location.point.latitude,
    )
    await OrderState.next()

    variants = delivery_tools.get_delivery_variants(delivery_distance=distance)
    await message.answer(
        "выберите вариант доставки",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        variant.name,
                        callback_data=cb_delivery_type.new(delivery_type=variant.type),
                    )
                ]
                for variant in variants
            ]
        ),
    )


@dp.callback_query_handler(cb_delivery_type.filter(), state=OrderState.WAITING_CHOOSING_DELIVERY_TYPE)
async def send_invoice(
    call: CallbackQuery,
    callback_data: dict,
    state: FSMContext,
):
    await call.answer()

    try:
        delivery_type = DELIVERY_VARIANTS[callback_data.get("delivery_type")]
    except KeyError:
        await call.message.answer("Ошибка получения варианта доставки. Попробуйте снова")
        return

    data = await state.get_data()
    if delivery_type.type == DeliveryType.PICKUP.value:
        await call.message.answer(
            format_tg_message(
                "Вы можете забрать пиццу самостоятельно по адресу\n{pizzeria_address}",
                pizzeria_address=data["pizzeria_address"],
            )
        )
        await state.finish()
        return

    cart = await moltin_api.get_cart_items(user_id=call.from_user.id)
    prices = [
        LabeledPrice(label=pizza_item.name, amount=int(pizza_item.cost * 100)) for pizza_item in cart.pizza_cart_items
    ]
    courier_message_text = "<code>Сообщение курьеру</code>\n" + "\n".join(
        [f"{pizza_item.name} - {pizza_item.quantity} шт." for pizza_item in cart.pizza_cart_items]
    )
    courier_message_text += f"\nИтого к оплате (за пиццу): {cart.display_price}\n"

    if delivery_type.price > 0:
        prices.append(LabeledPrice(label=delivery_type.name, amount=int(delivery_type.price * 100)))
        courier_message_text += f"\nза доставку: {delivery_type.price}р.\n"

    await bot.send_message(settings.COURIER_TG_ID, courier_message_text)
    await bot.send_location(
        chat_id=call.from_user.id, longitude=data["customer_longitude"], latitude=data["customer_latitude"]
    )

    await bot.send_invoice(
        call.from_user.id,
        title="Оплата пиццы",
        description="Ваша пицца",
        provider_token=settings.PAYMENT_PROVIDER_TOKEN,
        currency="rub",
        is_flexible=False,
        prices=prices,
        payload="some-invoice-payload-for-our-internal-use",
    )

    scheduler.add_job(
        notify_customer_about_fuckup,
        "date",
        kwargs={"user_id": call.from_user.id},
        run_date=datetime.now() + timedelta(hours=1),
    )


@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(pre_checkout_query_id=pre_checkout_query.id, ok=True)
    await bot.send_message(
        chat_id=pre_checkout_query.from_user.id,
        text="кушайте не обляпайтесь",
    )
    await state.finish()


async def notify_customer_about_fuckup(user_id):
    await bot.send_message(
        chat_id=user_id,
        text="""Приятного аппетита! *место для рекламы*
*сообщение что делать если пицца не пришла*""",
    )


async def on_startup(dp):
    await dp.bot.send_message(settings.TG_BOT_ADMIN_ID, "Бот Запущен и готов к работе!")


if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp, on_startup=on_startup)
