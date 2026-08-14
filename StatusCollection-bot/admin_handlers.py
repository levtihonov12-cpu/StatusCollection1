import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
import api_client
import keyboards as kb

router = Router()

STATUS_RU = {
    "new": "Новый",
    "processing": "В обработке",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


class AddProductStates(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_color = State()
    waiting_material = State()
    waiting_description = State()
    waiting_image = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Доступ запрещён.")
        return
    await message.answer("Админ-панель:", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("Админ-панель:", reply_markup=kb.admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(callback: CallbackQuery):
    await callback.message.edit_text("Админ-панель закрыта.")
    await callback.answer()

@router.callback_query(F.data == "admin:orders")
async def cb_admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        orders = await api_client.get_all_orders()
    except Exception as e:
        logging.error(f"Ошибка загрузки заказов: {e}")
        await callback.message.edit_text("Не удалось загрузить заказы.")
        await callback.answer()
        return
    if not orders:
        await callback.message.edit_text("Заказов пока нет.", reply_markup=kb.admin_menu_kb())
        await callback.answer()
        return
    await callback.message.edit_text("Все заказы:", reply_markup=kb.admin_orders_kb(orders))
    await callback.answer()


async def render_order(message, order_id: int):
    orders = await api_client.get_all_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    if order is None:
        await message.edit_text("Заказ не найден.", reply_markup=kb.admin_menu_kb())
        return
    lines = [
        f"Заказ #{order['id']}",
        f"Статус: {STATUS_RU.get(order['status'], order['status'])}",
        f"Имя: {order['customer_name']}",
        f"Сумма: {order['total_price']} ₽",
        f"Телефон: {order['phone']}",
        f"Адрес: {order['address']}",
        "",
        "Состав заказа:",
    ]
    for item in order["items"]:
        try:
            product = await api_client.get_product(item["product_id"])
            name = product["name"]
        except Exception:
            name = f"Товар #{item['product_id']}"
        lines.append(f"{name} — {item['price']} ₽ × {item['quantity']}")
    await message.edit_text("\n".join(lines), reply_markup=kb.admin_order_kb(order_id))


@router.callback_query(F.data.startswith("admin:order:"))
async def cb_admin_order(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    order_id = int(callback.data.split(":")[2])
    await render_order(callback.message, order_id)
    await callback.answer()

@router.callback_query(F.data.startswith("admin:status:"))
async def cb_admin_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    order_id = int(parts[2])
    new_status = parts[3]
    try:
        await api_client.update_order_status(order_id, new_status)
    except Exception as e:
        logging.error(f"Ошибка обновления статуса: {e}")
        await callback.answer("Не удалось обновить статус", show_alert=True)
        return
    await render_order(callback.message, order_id)
    await callback.answer("Статус обновлён")


@router.callback_query(F.data == "admin:delete_product")
async def cb_admin_delete_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    products = await api_client.get_products()
    if not products:
        await callback.message.edit_text("Товаров нет.", reply_markup=kb.admin_menu_kb())
        await callback.answer()
        return
    await callback.message.edit_text(
        "Выбери товар для удаления:",
        reply_markup=kb.admin_delete_products_kb(products),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:del:"))
async def cb_admin_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    try:
        await api_client.delete_product(product_id)
    except Exception as e:
        logging.error(f"Ошибка удаления товара: {e}")
        await callback.answer("Не удалось удалить товар", show_alert=True)
        return
    products = await api_client.get_products()
    if products:
        await callback.message.edit_text(
            "Товар удалён. Выбери следующий:",
            reply_markup=kb.admin_delete_products_kb(products),
        )
    else:
        await callback.message.edit_text("Товаров нет.", reply_markup=kb.admin_menu_kb())
    await callback.answer("Товар удален")

@router.callback_query(F.data == "admin:add_product")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    categories = await api_client.get_categories()
    await callback.message.edit_text(
        "Выбери категорию для нового товара:",
        reply_markup=kb.admin_categories_kb(categories),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:addcat:"))
async def cb_admin_addcat(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[2])
    await state.update_data(category_id=category_id)
    await state.set_state(AddProductStates.waiting_name)
    await callback.message.answer("Введи название товара:")
    await callback.answer()


@router.message(AddProductStates.waiting_name)
async def process_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductStates.waiting_price)
    await message.answer("Введи цену (число, в рублях):")


@router.message(AddProductStates.waiting_price)
async def process_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("Цена должна быть числом. Например: 1499")
        return
    await state.update_data(price=price)
    await state.set_state(AddProductStates.waiting_color)
    await message.answer("Введи цвет одежды (или отправь -, если нет):")


@router.message(AddProductStates.waiting_color)
async def process_product_color(message: Message, state: FSMContext):
    color = message.text.strip()
    await state.update_data(color=None if color == "-" else color)
    await state.set_state(AddProductStates.waiting_material)
    await message.answer("Введи материал одежды (или отправь -, если нет):")


@router.message(AddProductStates.waiting_material)
async def process_product_material(message: Message, state: FSMContext):
    material = message.text.strip()
    await state.update_data(material=None if material == "-" else material)
    await state.set_state(AddProductStates.waiting_description)
    await message.answer("Введи описание товара:")


@router.message(AddProductStates.waiting_description)
async def process_product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProductStates.waiting_image)
    await message.answer("Пришли фото товара (или отправь -, если фото нет):")

@router.message(AddProductStates.waiting_image, F.photo)
async def process_product_image(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(image_url=file_id)
    await finish_add_product(message, state)


@router.message(AddProductStates.waiting_image)
async def process_product_no_image(message: Message, state: FSMContext):
    await state.update_data(image_url=None)
    await finish_add_product(message, state)


async def finish_add_product(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    try:
        product = await api_client.create_product(
            category_id=data["category_id"],
            name=data["name"],
            price=data["price"],
            color=data.get("color"),
            material=data.get("material"),
            description=data.get("description"),
            image_url=data.get("image_url"),
        )
    except Exception as e:
        logging.error(f"Ошибка создания товара: {e}")
        await message.answer("Не удалось добавить товар.")
        return
    await message.answer(
        f"✅ Товар «{product['name']}» добавлен (ID {product['id']}).",
        reply_markup=kb.admin_menu_kb(),
    )
    #metal gemstone