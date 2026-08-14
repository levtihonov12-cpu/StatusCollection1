import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN
import api_client
import keyboards as kb

logging.basicConfig(level=logging.INFO)

main_router = Router()
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

from admin_handlers import router as admin_router
dp.include_router(admin_router)
dp.include_router(main_router)

RUSSIAN_STATUSES = {
    "new": "Новый",
    "processing": "В обработке",
    "completed": "Завершён",
    "cancelled": "Отменён",
}

class UserBasket:
    _baskets = {}

    @classmethod
    def get(cls, user_id: int) -> dict:
        return cls._baskets.setdefault(user_id, {})

    @classmethod
    def add_item(cls, user_id: int, product_id: int):
        basket = cls.get(user_id)
        basket[product_id] = basket.get(product_id, 0) + 1

    @classmethod
    def clear(cls, user_id: int):
        cls._baskets.pop(user_id, None)

    @classmethod
    def is_empty(cls, user_id: int) -> bool:
        return not cls._baskets.get(user_id)


class CheckoutSteps(StatesGroup):
    step_name = State()
    step_phone = State()
    step_address = State()


async def generate_cart_summary(user_id: int) -> tuple[str, int]:
    basket = UserBasket.get(user_id)
    if not basket:
        return "Ваша корзина пока пуста.", 0

    text_lines = []
    overall_price = 0

    for prod_id, qty in basket.items():
        try:
            prod = await api_client.api.fetch_product_details(prod_id)
        except Exception:
            continue

        item_total = prod["price"] * qty
        overall_price += item_total
        text_lines.append(f"• {prod['name']} — {prod['price']} ₽ × {qty}")

    text_lines.append(f"\nИтоговая сумма: {overall_price} ₽")
    return "\n".join(text_lines), overall_price


def make_product_card(prod: dict) -> str:
    return (
        f"👕 {prod['name']}\n\n"
        f"💰 Стоимость: {prod['price']} ₽\n"
        f"🎨 Цвет: {prod.get('color', 'не указан')}\n"
        f"🧵 Материал: {prod.get('material', 'не указан')}\n\n"
        f"📝 {prod.get('description') or 'Описание к этому товару отсутствует.'}"
    )


@main_router.message(CommandStart())
async def handle_start(msg: Message):
    try:
        await api_client.api.register_telegram_user(
            telegram_id=msg.from_user.id,
            username=msg.from_user.username,
            first_name=msg.from_user.first_name,
            last_name=msg.from_user.last_name,
        )
    except Exception as err:
        logging.error(f"Ошибка регистрации юзера {msg.from_user.id}: {err}")

    await msg.answer(
        "Привет! Добро пожаловать в бутик Status Collection 👔\n"
        "Выберите нужный раздел в меню ниже:",
        reply_markup=kb.get_main_reply_kb(),
    )


@main_router.message(Command("cancel"))
async def handle_cancel(msg: Message, fsm: FSMContext):
    await fsm.clear()
    await msg.answer("Все текущие действия сброшены.", reply_markup=kb.get_main_reply_kb())


@main_router.message(F.text == "👔 Каталог")
async def open_catalog(msg: Message):
    try:
        cats = await api_client.api.fetch_categories()
    except Exception as err:
        logging.error(f"Проблема с получением категорий: {err}")
        await msg.answer("Сейчас не получается загрузить каталог. Убедитесь, что сервер работает.")
        return

    await msg.answer("Пожалуйста, выберите интересующую категорию:", reply_markup=kb.build_categories_inline_kb(cats))


@main_router.message(F.text == "🛒 Корзина")
async def open_basket(msg: Message):
    empty = UserBasket.is_empty(msg.from_user.id)
    summary, _ = await generate_cart_summary(msg.from_user.id)
    await msg.answer(summary, reply_markup=kb.get_cart_actions_kb(is_empty=empty))


@main_router.message(F.text == "📦 Мои заказы")
async def show_user_orders(msg: Message):
    try:
        orders_list = await api_client.api.fetch_user_orders(msg.from_user.id)
    except Exception as err:
        logging.error(f"Не удалось подтянуть заказы: {err}")
        await msg.answer("Произошла ошибка при загрузке истории заказов.")
        return

    if not orders_list:
        await msg.answer("Вы еще ничего не заказывали.")
        return

    output = ["Ваши последние заказы:\n"]
    for order in orders_list:
        st = RUSSIAN_STATUSES.get(order["status"], order["status"])
        output.append(
            f"🧾 Заказ #{order['id']}\n"
            f"Статус: {st}\n"
            f"К оплате: {order['total_price']} ₽\n"
            f"Позиций в заказе: {len(order['items'])}\n"
            f"{'-'*20}"
        )

    await msg.answer("\n".join(output))


@main_router.message(F.text == "ℹ️ О магазине")
async def shop_info(msg: Message):
    await msg.answer(
        "Status Collection — это премиальный магазин одежды прямо в Telegram.\n"
        "У нас собраны лучшие вещи, которые мы с удовольствием поможем вам подобрать и доставить."
    )


@main_router.callback_query(F.data == "nav_catalog")
async def go_catalog(cb: CallbackQuery):
    try:
        cats = await api_client.api.fetch_categories()
    except Exception as err:
        logging.error(f"Ошибка загрузки каталога: {err}")
        await cb.message.edit_text("Каталог сейчас недоступен.")
        await cb.answer()
        return

    await cb.message.edit_text("Выберите категорию вещей:", reply_markup=kb.build_categories_inline_kb(cats))
    await cb.answer()


@main_router.callback_query(F.data == "nav_main")
async def go_main_menu(cb: CallbackQuery):
    await cb.message.answer("Возвращаемся в главное меню:", reply_markup=kb.get_main_reply_kb())
    await cb.answer()


@main_router.callback_query(F.data.startswith("cat_"))
async def view_category_items(cb: CallbackQuery):
    cat_id = int(cb.data.split("_")[1])
    try:
        items = await api_client.api.fetch_products(category_id=cat_id)
        all_cats = await api_client.api.fetch_categories()
        cat_title = next((c["name"] for c in all_cats if c["id"] == cat_id), "Неизвестная категория")
    except Exception as err:
        logging.error(f"Ошибка при получении товаров: {err}")
        await cb.message.edit_text("Товары сейчас недоступны.")
        await cb.answer()
        return

    if not items:
        await cb.message.edit_text(f"В разделе «{cat_title}» пока пустота.", reply_markup=kb.get_back_to_catalog_kb())
        await cb.answer()
        return

    await cb.message.edit_text(f"Раздел: {cat_title}\n\nКакой товар посмотреть?", reply_markup=kb.build_products_inline_kb(items))
    await cb.answer()


@main_router.callback_query(F.data.startswith("prod_"))
async def view_product_details(cb: CallbackQuery):
    prod_id = int(cb.data.split("_")[1])
    try:
        prod = await api_client.api.fetch_product_details(prod_id)
    except Exception as err:
        logging.error(f"Не удалось получить информацию о товаре: {err}")
        await cb.message.edit_text("Информация о товаре сейчас недоступна.")
        await cb.answer()
        return

    if prod.get("image_url"):
        try:
            await cb.message.answer_photo(prod["image_url"])
        except Exception as err:
            logging.error(f"Не получилось отправить картинку товара: {err}")

    await cb.message.edit_text(make_product_card(prod), reply_markup=kb.get_product_details_kb(prod_id))
    await cb.answer()


@main_router.callback_query(F.data.startswith("basket_add_"))
async def add_item_to_cart(cb: CallbackQuery):
    prod_id = int(cb.data.split("_")[2])
    UserBasket.add_item(cb.from_user.id, prod_id)
    await cb.answer("Отличный выбор! Товар перемещен в корзину.", show_alert=True)


@main_router.callback_query(F.data == "basket_clear")
async def empty_the_basket(cb: CallbackQuery):
    UserBasket.clear(cb.from_user.id)
    await cb.message.edit_text("Вы полностью очистили корзину.", reply_markup=kb.get_cart_actions_kb(is_empty=True))
    await cb.answer()


@main_router.callback_query(F.data == "checkout_init")
async def start_checkout_process(cb: CallbackQuery, fsm: FSMContext):
    if UserBasket.is_empty(cb.from_user.id):
        await cb.answer("Сначала добавьте что-нибудь в корзину!", show_alert=True)
        return

    await fsm.set_state(CheckoutSteps.step_name)
    await cb.message.answer("Пожалуйста, укажите ФИО или имя получателя:")
    await cb.answer()


@main_router.callback_query(F.data == "checkout_confirm")
async def finalize_checkout(cb: CallbackQuery, fsm: FSMContext):
    user_data = await fsm.get_data()
    if UserBasket.is_empty(cb.from_user.id):
        await cb.answer("Корзина пуста, оформлять нечего.", show_alert=True)
        await fsm.clear()
        return

    order_payload = [
        {"product_id": p_id, "quantity": qty}
        for p_id, qty in UserBasket.get(cb.from_user.id).items()
    ]

    try:
        new_order = await api_client.api.create_new_order(
            telegram_id=cb.from_user.id,
            customer_name=user_data.get("c_name", ""),
            phone=user_data.get("c_phone", ""),
            address=user_data.get("c_address", ""),
            items=order_payload,
        )
    except Exception as err:
        logging.error(f"Сбой при создании заказа: {err}")
        await cb.message.answer("Что-то пошло не так при оформлении. Попробуйте повторить позже.")
        await fsm.clear()
        return

    UserBasket.clear(cb.from_user.id)
    await fsm.clear()

    await cb.message.answer(
        f"🎉 Ура! Заказ #{new_order['id']} успешно принят!\n"
        f"Итог: {new_order['total_price']} ₽\n"
        "Наш менеджер скоро свяжется с вами для уточнения деталей.",
        reply_markup=kb.get_main_reply_kb(),
    )
    await cb.answer()


@main_router.callback_query(F.data == "checkout_cancel")
async def abort_checkout(cb: CallbackQuery, fsm: FSMContext):
    await fsm.clear()
    await cb.message.answer("Оформление прервано. Вы возвращены в главное меню.", reply_markup=kb.get_main_reply_kb())
    await cb.answer()


@main_router.message(CheckoutSteps.step_name)
async def input_customer_name(msg: Message, fsm: FSMContext):
    await fsm.update_data(c_name=msg.text.strip())
    await fsm.set_state(CheckoutSteps.step_phone)
    await msg.answer("Теперь оставьте контактный номер телефона:")


@main_router.message(CheckoutSteps.step_phone)
async def input_customer_phone(msg: Message, fsm: FSMContext):
    await fsm.update_data(c_phone=msg.text.strip())
    await fsm.set_state(CheckoutSteps.step_address)
    await msg.answer("И последний шаг — укажите адрес доставки:")


@main_router.message(CheckoutSteps.step_address)
async def input_customer_address(msg: Message, fsm: FSMContext):
    await fsm.update_data(c_address=msg.text.strip())
    collected_data = await fsm.get_data()

    summary_text, _ = await generate_cart_summary(msg.from_user.id)

    final_check = (
        "Давайте проверим данные перед отправкой:\n\n"
        f"{summary_text}\n\n"
        f"👤 Получатель: {collected_data['c_name']}\n"
        f"📞 Телефон: {collected_data['c_phone']}\n"
        f"📍 Куда доставить: {collected_data['c_address']}\n\n"
        "Всё верно и отправляем?"
    )

    await msg.answer(final_check, reply_markup=kb.get_order_confirmation_kb())


@main_router.message()
async def fallback_handler(msg: Message):
    await msg.answer(
        "Я пока умею реагировать только на кнопки внизу экрана или в меню.",
        reply_markup=kb.get_main_reply_kb(),
    )


async def launch_bot():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(launch_bot())