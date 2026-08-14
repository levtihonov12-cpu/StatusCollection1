import asyncio
import logging


from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from admin_handlers import router as admin_router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup


from config import BOT_TOKEN
import api_client
import keyboards as kb


logging.basicConfig(level=logging.INFO)

fallback_router = Router()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(admin_router)
dp.include_router(fallback_router)



carts = {}

STATUS_RU = {
    "new": "Новый",
    "processing": "В обработке",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


class OrderStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()


def get_cart(user_id: int):
    return carts.setdefault(user_id, {})


def add_to_cart(user_id: int, product_id: int):
    cart = get_cart(user_id)
    cart[product_id] = cart.get(product_id, 0) + 1


def clear_cart(user_id: int):
    carts.pop(user_id, None)


async def get_cart_text(user_id: int):
    cart = get_cart(user_id)

    if not cart:
        return "Корзина пустая."

    lines = []
    total = 0

    for product_id, quantity in cart.items():
        try:
            product = await api_client.get_product(product_id)
        except Exception:
            continue

        total += product["price"] * quantity
        lines.append(f"{product['name']} — {product['price']} ₽ × {quantity}")

    lines.append("")
    lines.append(f"Итого: {total} ₽")

    return "\n".join(lines)


def format_product(product: dict):
    return (
        f"{product['name']}\n\n"
        f"Цена: {product['price']} ₽\n"
        f"Цвет: {product.get('color') }\n"
        f"Материал: {product.get('material') }\n\n"
        f"{product.get('description') or 'Описание отсутствует'}"
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    try:
        await api_client.register_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    except Exception as e:
        logging.error(f"Не удалось зарегистрировать пользователя: {e}")

    await message.answer(
        "Hello world! вы попали в магазин одежды Status Collection.\n"
        "Выбери раздел:",
        reply_markup=kb.main_menu_kb(),
    )


@dp.message(F.text == "/cancel")
async def cancel_state(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=kb.main_menu_kb(),
    )


@dp.message(F.text == "👔 Каталог")
async def show_catalog(message: Message):
    try:
        categories = await api_client.get_categories()
    except Exception as e:
        logging.error(f"Ошибка загрузки категорий: {e}")
        await message.answer("Не удалось загрузить каталог. Проверь, что бэкенд запущен.")
        return

    await message.answer(
        "Выбери категорию:",
        reply_markup=kb.categories_kb(categories),
    )


@dp.message(F.text == "🛒 Корзина")
async def show_cart(message: Message):
    cart = get_cart(message.from_user.id)
    text = await get_cart_text(message.from_user.id)

    await message.answer(
        text,
        reply_markup=kb.cart_kb(is_empty=len(cart) == 0),
    )


@dp.message(F.text == "📦 Мои заказы")
async def show_orders(message: Message):
    try:
        orders = await api_client.get_orders(message.from_user.id)
    except Exception as e:
        logging.error(f"Ошибка загрузки заказов: {e}")
        await message.answer("Не удалось загрузить заказы.")
        return

    if not orders:
        await message.answer("У тебя пока нет заказов.")
        return

    lines = []

    for order in orders:
        status = STATUS_RU.get(order["status"], order["status"])
        lines.append(
            f"Заказ #{order['id']}\n"
            f"Статус: {status}\n"
            f"Сумма: {order['total_price']} ₽\n"
            f"Товаров: {len(order['items'])}\n"
        )

    await message.answer("Твои заказы:\n\n" + "\n".join(lines))


@dp.message(F.text == "ℹ️ О магазине")
async def about(message: Message):
    await message.answer(
        "премиум одежда от Status Collection в Telegram.\n"
        "Здесь можно посмотреть самые лучшие вещи которые идеально подобранны под каждого и оформить заказ."
    )


@dp.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery):
    try:
        categories = await api_client.get_categories()
    except Exception as e:
        logging.error(f"Ошибка загрузки категорий: {e}")
        await callback.message.edit_text("Не удалось загрузить каталог.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выбери категорию:",
        reply_markup=kb.categories_kb(categories),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Главное меню:",
        reply_markup=kb.main_menu_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])

    try:
        products = await api_client.get_products(category_id=category_id)
        categories = await api_client.get_categories()
        category_name = next(
            (c["name"] for c in categories if c["id"] == category_id),
            "Категория"
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки товаров: {e}")
        await callback.message.edit_text("Не удалось загрузить товары.")
        await callback.answer()
        return

    if not products:
        await callback.message.edit_text(
            f"В категории «{category_name}» пока нет товаров.",
            reply_markup=kb.back_to_catalog_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Категория: {category_name}\nВыбери товар:",
        reply_markup=kb.products_kb(products),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("prod:"))
async def cb_product(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])

    try:
        product = await api_client.get_product(product_id)
    except Exception as e:
        logging.error(f"Ошибка загрузки товара: {e}")
        await callback.message.edit_text("Не удалось загрузить товар.")
        await callback.answer()
        return
    if product.get("image_url"):
        try:
            await callback.message.answer_photo(product["image_url"])
        except Exception as e:
            logging.error(f"Не удалось отправить фото: {e}")
    await callback.message.edit_text(
        format_product(product),
        reply_markup=kb.product_kb(product_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    add_to_cart(callback.from_user.id, product_id)
    await callback.answer("Товар добавлен в корзину", show_alert=True)


@dp.callback_query(F.data == "cart:clear")
async def cb_clear_cart(callback: CallbackQuery):
    clear_cart(callback.from_user.id)
    await callback.message.edit_text(
        "Корзина очищена.",
        reply_markup=kb.cart_kb(is_empty=True),
    )
    await callback.answer()


@dp.callback_query(F.data == "order:start")
async def cb_order_start(callback: CallbackQuery, state: FSMContext):
    cart = get_cart(callback.from_user.id)

    if not cart:
        await callback.answer("Корзина пустая", show_alert=True)
        return

    await state.set_state(OrderStates.waiting_name)
    await callback.message.answer("Введи имя получателя:")
    await callback.answer()


@dp.callback_query(F.data == "order:confirm")
async def cb_order_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(callback.from_user.id)

    if not cart:
        await callback.answer("Корзина пустая", show_alert=True)
        await state.clear()
        return

    items = [
        {"product_id": product_id, "quantity": quantity}
        for product_id, quantity in cart.items()
    ]

    try:
        order = await api_client.create_order(
            telegram_id=callback.from_user.id,
            customer_name=data.get("customer_name", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            items=items,
        )
    except Exception as e:
        logging.error(f"Ошибка создания заказа: {e}")
        await callback.message.answer("Не удалось оформить заказ. Попробуй ещё раз.")
        await state.clear()
        return

    clear_cart(callback.from_user.id)
    await state.clear()

    await callback.message.answer(
        f"✅ Заказ #{order['id']} оформлен!\n"
        f"Сумма: {order['total_price']} ₽\n"
        "Мы свяжемся с тобой для подтверждения.",
        reply_markup=kb.main_menu_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "order:cancel")
async def cb_order_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "Заказ отменён.",
        reply_markup=kb.main_menu_kb(),
    )
    await callback.answer()


@dp.message(OrderStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(customer_name=message.text.strip())
    await state.set_state(OrderStates.waiting_phone)
    await message.answer("Введи номер телефона:")


@dp.message(OrderStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(OrderStates.waiting_address)
    await message.answer("Введи адрес доставки:")


@dp.message(OrderStates.waiting_address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    data = await state.get_data()

    cart = get_cart(message.from_user.id)

    lines = []
    total = 0

    for product_id, quantity in cart.items():
        try:
            product = await api_client.get_product(product_id)
        except Exception:
            continue

        total += product["price"] * quantity
        lines.append(f"{product['name']} — {product['price']} ₽ × {quantity}")

    text = (
        "Проверь заказ:\n\n"
        + "\n".join(lines)
        + f"\n\nИтого: {total} ₽\n\n"
        f"Имя: {data['customer_name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Адрес: {data['address']}\n\n"
        "Подтвердить заказ?"
    )

    await message.answer(text, reply_markup=kb.confirm_order_kb())


@fallback_router.message()
async def unknown(message: Message):
    await message.answer(
        "Я пока понимаю только кнопки меню.",
        reply_markup=kb.main_menu_kb(),
    )

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())