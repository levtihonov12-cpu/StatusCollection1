from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def get_main_reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👔 Каталог"), KeyboardButton(text="🛒 Корзина"),KeyboardButton(text="📦 Мои заказы")],
            [ KeyboardButton(text="ℹ️ О магазине")],
        ],
        resize_keyboard=True,
    )

def build_categories_inline_kb(categories: list):
    rows = []
    temp_row = []
    for cat in categories:
        temp_row.append(InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}"))
        if len(temp_row) == 2:
            rows.append(temp_row)
            temp_row = []
    if temp_row:
        rows.append(temp_row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="nav_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_back_to_catalog_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_catalog")]]
    )

def build_products_inline_kb(products: list):
    rows = [[InlineKeyboardButton(text=p["name"], callback_data=f"prod_{p['id']}")] for p in products]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_catalog")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_product_details_kb(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"basket_add_{product_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_catalog")],
        ]
    )

def get_cart_actions_kb(is_empty: bool = True):
    kb = []
    if not is_empty:
        kb.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout_init")])
        kb.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="basket_clear")])
    kb.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="nav_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_order_confirmation_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="checkout_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="checkout_cancel")],
        ]
    )

def get_admin_panel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="adm_orders")],
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_add_prod")],
            [InlineKeyboardButton(text="🗑 Удалить товар", callback_data="adm_del_prod")],
            [InlineKeyboardButton(text="⬅️ Закрыть", callback_data="adm_hide")],
        ]
    )

def get_admin_orders_kb(orders: list):
    kb = []
    for order in orders[:10]:
        kb.append([InlineKeyboardButton(
            text=f"#{order['id']} | {order['total_price']} ₽ | {order['status']}",
            callback_data=f"adm_view_ord_{order['id']}"
        )])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_order_actions_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆕 Новый", callback_data=f"adm_set_status_{order_id}_new"),
                InlineKeyboardButton(text="⏳ В обработке", callback_data=f"adm_set_status_{order_id}_processing"),
            ],
            [
                InlineKeyboardButton(text="✅ Завершен", callback_data=f"adm_set_status_{order_id}_completed"),
                InlineKeyboardButton(text="❌ Отменен", callback_data=f"adm_set_status_{order_id}_cancelled"),
            ],
            [InlineKeyboardButton(text="⬅️ К заказам", callback_data="adm_orders")],
        ]
    )

def get_admin_categories_kb(categories: list):
    kb = [[InlineKeyboardButton(text=cat["name"], callback_data=f"adm_pick_cat_{cat['id']}")] for cat in categories]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_delete_products_kb(products: list):
    kb = [[InlineKeyboardButton(text=f"🗑 {p['name']}", callback_data=f"adm_remove_prod_{p['id']}")] for p in products[:15]]
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)