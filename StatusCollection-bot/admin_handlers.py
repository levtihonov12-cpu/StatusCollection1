import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMINS
import api_client
import keyboards as kb

router = Router()

STATUS_TRANSLATION = {
    "new": "Новый",
    "processing": "В обработке",
    "completed": "Завершён",
    "cancelled": "Отменён",
}


class ProductCreationSteps(StatesGroup):
    ask_name = State()
    ask_price = State()
    ask_color = State()
    ask_material = State()
    ask_country = State()
    ask_desc = State()
    ask_photo = State()


def has_admin_rights(user_id: int) -> bool:
    return user_id in ADMINS


@router.message(Command("cancel"))
async def stop_admin_action(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Текущее действие отменено.")


@router.message(Command("admin"))
async def open_admin_panel(msg: Message):
    if not has_admin_rights(msg.from_user.id):
        await msg.answer("У вас нет прав для доступа к этому разделу.")
        return
    await msg.answer("Добро пожаловать в панель управления 👑", reply_markup=kb.get_admin_panel_kb())


@router.callback_query(F.data == "adm_menu")
async def return_to_admin_menu(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Доступ закрыт.", show_alert=True)
        return
    await cb.message.edit_text("Панель управления 👑", reply_markup=kb.get_admin_panel_kb())
    await cb.answer()


@router.callback_query(F.data == "adm_hide")
async def close_admin_panel(cb: CallbackQuery):
    await cb.message.edit_text("Админ-панель свернута.")
    await cb.answer()


@router.callback_query(F.data == "adm_orders")
async def list_all_orders(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    try:
        all_orders = await api_client.api.fetch_all_orders()
    except Exception as err:
        logging.error(f"Сбой при выгрузке заказов: {err}")
        await cb.message.edit_text("Не получилось подгрузить заказы.")
        await cb.answer()
        return

    if not all_orders:
        await cb.message.edit_text("В базе пока нет ни одного заказа.", reply_markup=kb.get_admin_panel_kb())
        await cb.answer()
        return

    await cb.message.edit_text("Список всех актуальных заказов:", reply_markup=kb.get_admin_orders_kb(all_orders))
    await cb.answer()


async def display_order_details(target_msg, order_id: int):
    try:
        all_orders = await api_client.api.fetch_all_orders()
    except Exception:
        await target_msg.edit_text("Ошибка связи с сервером.")
        return

    order = next((o for o in all_orders if o["id"] == order_id), None)
    if not order:
        await target_msg.edit_text("Такой заказ не найден.", reply_markup=kb.get_admin_panel_kb())
        return

    st_text = STATUS_TRANSLATION.get(order['status'], order['status'])
    lines = [
        f"🧾 Детали заказа #{order['id']}",
        f"Текущий статус: {st_text}",
        f"Клиент: {order['customer_name']}",
        f"Общая сумма: {order['total_price']} ₽",
        f"Контакт: {order['phone']}",
        f"Адрес: {order['address']}",
        "",
        "Что входит в заказ:"
    ]

    for item in order["items"]:
        try:
            prod = await api_client.api.fetch_product_details(item["product_id"])
            item_name = prod["name"]
        except Exception:
            item_name = f"Товар с ID {item['product_id']}"
        lines.append(f"• {item_name} — {item['price']} ₽ × {item['quantity']}")

    await target_msg.edit_text("\n".join(lines), reply_markup=kb.get_admin_order_actions_kb(order_id))


@router.callback_query(F.data.startswith("adm_view_ord_"))
async def show_specific_order(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    oid = int(cb.data.split("_")[3])
    await display_order_details(cb.message, oid)
    await cb.answer()


@router.callback_query(F.data.startswith("adm_set_status_"))
async def update_order_current_status(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    parts = cb.data.split("_")
    oid = int(parts[3])
    new_st = parts[4]

    try:
        await api_client.api.change_order_status(oid, new_st)
    except Exception as err:
        logging.error(f"Не удалось поменять статус: {err}")
        await cb.answer("Ошибка обновления статуса!", show_alert=True)
        return

    await display_order_details(cb.message, oid)
    await cb.answer("Статус заказа успешно изменен.")


@router.callback_query(F.data == "adm_del_prod")
async def show_products_to_delete(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    try:
        prods = await api_client.api.fetch_products()
    except Exception as err:
        logging.error(f"Ошибка получения списка товаров: {err}")
        await cb.answer()
        return

    if not prods:
        await cb.message.edit_text("В каталоге пока нет товаров.", reply_markup=kb.get_admin_panel_kb())
        await cb.answer()
        return

    await cb.message.edit_text(
        "Нажмите на товар, который нужно удалить из базы:",
        reply_markup=kb.get_admin_delete_products_kb(prods),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm_remove_prod_"))
async def execute_product_deletion(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    pid = int(cb.data.split("_")[3])
    try:
        await api_client.api.remove_product(pid)
    except Exception as err:
        logging.error(f"Сбой при удалении товара: {err}")
        await cb.answer("Не получилось удалить товар", show_alert=True)
        return

    prods = await api_client.api.fetch_products()
    if prods:
        await cb.message.edit_text(
            "Товар успешно стерт из базы. Выберите следующий:",
            reply_markup=kb.get_admin_delete_products_kb(prods),
        )
    else:
        await cb.message.edit_text("База товаров полностью очищена.", reply_markup=kb.get_admin_panel_kb())
    await cb.answer("Готово, товар удален.")



@router.callback_query(F.data == "adm_reviews")
async def show_reviews_management(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    try:
        reviews = await api_client.api.fetch_all_reviews()
    except Exception as err:
        logging.error(f"Ошибка при загрузке отзывов: {err}")
        await cb.message.edit_text("Не удалось загрузить отзывы.")
        await cb.answer()
        return

    if not reviews:
        await cb.message.edit_text(
            "В базе пока нет ни одного отзыва.",
            reply_markup=kb.get_admin_panel_kb()
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        "⭐ Список всех отзывов.\n\n"
        "Нажмите на отзыв, чтобы удалить его:",
        reply_markup=kb.get_admin_reviews_kb(reviews)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm_del_review_"))
async def execute_review_deletion(cb: CallbackQuery):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    review_id = int(cb.data.split("_")[3])
    try:
        await api_client.api.delete_review(review_id)
    except Exception as err:
        logging.error(f"Сбой при удалении отзыва: {err}")
        await cb.answer("Не получилось удалить отзыв", show_alert=True)
        return

    try:
        reviews = await api_client.api.fetch_all_reviews()
    except Exception as err:
        logging.error(f"Ошибка при обновлении списка отзывов: {err}")
        await cb.message.edit_text("Отзыв удален, но не удалось обновить список.", reply_markup=kb.get_admin_panel_kb())
        await cb.answer()
        return

    if reviews:
        await cb.message.edit_text(
            "✅ Отзыв успешно удален.\n\nВыберите следующий:",
            reply_markup=kb.get_admin_reviews_kb(reviews)
        )
    else:
        await cb.message.edit_text(
            "✅ Отзыв удален.\n\nВсе отзывы удалены из базы.",
            reply_markup=kb.get_admin_panel_kb()
        )
    await cb.answer("Готово, отзыв удален.")


@router.callback_query(F.data == "adm_add_prod")
async def start_new_product_flow(cb: CallbackQuery, state: FSMContext):
    if not has_admin_rights(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    cats = await api_client.api.fetch_categories()
    await cb.message.edit_text(
        "Сначала выберите категорию, к которой будет относиться новая вещь:",
        reply_markup=kb.get_admin_categories_kb(cats),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("adm_pick_cat_"))
async def select_category_for_product(cb: CallbackQuery, state: FSMContext):
    cid = int(cb.data.split("_")[3])
    await state.update_data(category_id=cid)
    await state.set_state(ProductCreationSteps.ask_name)
    await cb.message.answer("Как назовем новый товар?")
    await cb.answer()


@router.message(ProductCreationSteps.ask_name)
async def input_product_name(msg: Message, state: FSMContext):
    await state.update_data(prod_name=msg.text.strip())
    await state.set_state(ProductCreationSteps.ask_price)
    await msg.answer("Теперь укажите стоимость (только цифры, в рублях):")


@router.message(ProductCreationSteps.ask_price)
async def input_product_price(msg: Message, state: FSMContext):
    try:
        val = int(msg.text.strip())
    except ValueError:
        await msg.answer("Нужно ввести целое число. Попробуйте еще раз (например: 2500):")
        return
    await state.update_data(prod_price=val)
    await state.set_state(ProductCreationSteps.ask_color)
    await msg.answer("Какого цвета эта вещь? (Если не важно, просто отправьте '-')")


@router.message(ProductCreationSteps.ask_color)
async def input_product_color(msg: Message, state: FSMContext):
    c = msg.text.strip()
    await state.update_data(prod_color=None if c == "-" else c)
    await state.set_state(ProductCreationSteps.ask_material)
    await msg.answer("Из какого материала сделано? (Или '-' если без разницы)")

@router.message(ProductCreationSteps.ask_country)
async def input_product_country(msg: Message, state: FSMContext):
    b = msg.text.strip()
    await state.update_data(prod_country=None if b == "-" else b)
    await state.set_state(ProductCreationSteps.ask_desc)
    await msg.answer("Напишите страну производитель товара:")

@router.message(ProductCreationSteps.ask_material)
async def input_product_material(msg: Message, state: FSMContext):
    m = msg.text.strip()
    await state.update_data(prod_material=None if m == "-" else m)
    await state.set_state(ProductCreationSteps.ask_desc)
    await msg.answer("Напишите подробное описание для карточки товара:")


@router.message(ProductCreationSteps.ask_desc)
async def input_product_description(msg: Message, state: FSMContext):
    await state.update_data(prod_desc=msg.text.strip())
    await state.set_state(ProductCreationSteps.ask_photo)
    await msg.answer("Отправьте фотографию товара. Если фото пока нет, отправьте '-'")


@router.message(ProductCreationSteps.ask_photo, F.photo)
async def save_product_photo(msg: Message, state: FSMContext):
    file_uid = msg.photo[-1].file_id
    await state.update_data(prod_img=file_uid)
    await complete_product_addition(msg, state)


@router.message(ProductCreationSteps.ask_photo)
async def skip_product_photo(msg: Message, state: FSMContext):
    await state.update_data(prod_img=None)
    await complete_product_addition(msg, state)


async def complete_product_addition(msg: Message, state: FSMContext):
    gathered = await state.get_data()
    await state.clear()
    try:
        new_prod = await api_client.api.add_new_product(
            category_id=gathered["category_id"],
            name=gathered["prod_name"],
            price=gathered["prod_price"],
            color=gathered.get("prod_color"),
            material=gathered.get("prod_material"),
            country=gathered.get("prod_country"),
            description=gathered.get("prod_desc"),
            image_url=gathered.get("prod_img"),
        )
    except Exception as err:
        logging.error(f"Ошибка при добавлении новой позиции: {err}")
        await msg.answer("Не получилось сохранить товар в базе.")
        return

    await msg.answer(
        f"🎉 Отлично! Вещь «{new_prod['name']}» успешно добавлена (Ее ID: {new_prod['id']}).",
        reply_markup=kb.get_admin_panel_kb(),
    )