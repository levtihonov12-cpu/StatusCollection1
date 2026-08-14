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
    ask_desc = State()
    ask_photo = State()


def has_admin_rights(user_id: int) -> bool:
    return user_id in ADMINS


@router.message(Command("cancel"))
async def stop_admin_action(msg: Message, fsm: FSMContext):
    await fsm.clear()
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


@router.callback_query(F.data == "adm_add_prod")
async def start_new_product_flow(cb: CallbackQuery, fsm: FSMContext):
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
async def select_category_for_product(cb: CallbackQuery, fsm: FSMContext):
    cid = int(cb.data.split("_")[3])
    await fsm.update_data(category_id=cid)
    await fsm.set_state(ProductCreationSteps.ask_name)
    await cb.message.answer("Как назовем новый товар?")
    await cb.answer()


@router.message(ProductCreationSteps.ask_name)
async def input_product_name(msg: Message, fsm: FSMContext):
    await fsm.update_data(prod_name=msg.text.strip())
    await fsm.set_state(ProductCreationSteps.ask_price)
    await msg.answer("Теперь укажите стоимость (только цифры, в рублях):")


@router.message(ProductCreationSteps.ask_price)
async def input_product_price(msg: Message, fsm: FSMContext):
    try:
        val = int(msg.text.strip())
    except ValueError:
        await msg.answer("Нужно ввести целое число. Попробуйте еще раз (например: 2500):")
        return
    await fsm.update_data(prod_price=val)
    await fsm.set_state(ProductCreationSteps.ask_color)
    await msg.answer("Какого цвета эта вещь? (Если не важно, просто отправьте '-')")


@router.message(ProductCreationSteps.ask_color)
async def input_product_color(msg: Message, fsm: FSMContext):
    c = msg.text.strip()
    await fsm.update_data(prod_color=None if c == "-" else c)
    await fsm.set_state(ProductCreationSteps.ask_material)
    await msg.answer("Из какого материала сделано? (Или '-' если без разницы)")


@router.message(ProductCreationSteps.ask_material)
async def input_product_material(msg: Message, fsm: FSMContext):
    m = msg.text.strip()
    await fsm.update_data(prod_material=None if m == "-" else m)
    await fsm.set_state(ProductCreationSteps.ask_desc)
    await msg.answer("Напишите подробное описание для карточки товара:")


@router.message(ProductCreationSteps.ask_desc)
async def input_product_description(msg: Message, fsm: FSMContext):
    await fsm.update_data(prod_desc=msg.text.strip())
    await fsm.set_state(ProductCreationSteps.ask_photo)
    await msg.answer("Отправьте фотографию товара. Если фото пока нет, отправьте '-'")


@router.message(ProductCreationSteps.ask_photo, F.photo)
async def save_product_photo(msg: Message, fsm: FSMContext):
    file_uid = msg.photo[-1].file_id
    await fsm.update_data(prod_img=file_uid)
    await complete_product_addition(msg, fsm)


@router.message(ProductCreationSteps.ask_photo)
async def skip_product_photo(msg: Message, fsm: FSMContext):
    await fsm.update_data(prod_img=None)
    await complete_product_addition(msg, fsm)


async def complete_product_addition(msg: Message, fsm: FSMContext):
    gathered = await fsm.get_data()
    await fsm.clear()
    try:
        new_prod = await api_client.api.add_new_product(
            category_id=gathered["category_id"],
            name=gathered["prod_name"],
            price=gathered["prod_price"],
            color=gathered.get("prod_color"),
            material=gathered.get("prod_material"),
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