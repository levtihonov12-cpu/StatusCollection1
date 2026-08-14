from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton)

def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👔 Каталог"),
                KeyboardButton(text="🛒 Корзина"),
            ],
            [
                KeyboardButton(text="📦 Мои заказы"),
                KeyboardButton(text="ℹ️ О магазине"),
            ],
        ],
        resize_keyboard=True,
    )

def back_to_catalog_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="catalog"
                )
            ]
        ]
    )


def categories_kb(categories):
    buttons = []
    row = []

    for category in categories:
        row.append(
            InlineKeyboardButton(
                text=category["name"],
                callback_data=f"cat:{category['id']}"
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ В меню",
                callback_data="menu:main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_kb(products):
    buttons = []

    for product in products:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=product["name"],
                    callback_data=f"prod:{product['id']}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="catalog"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_kb(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить в корзину",
                    callback_data=f"add:{product_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="catalog"
                )
            ],
        ]
    )


def cart_kb(is_empty=True):
    buttons = []

    if not is_empty:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Оформить заказ",
                    callback_data="order:start"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🗑 Очистить корзину",
                    callback_data="cart:clear"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ В меню",
                callback_data="menu:main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_order_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data="order:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="order:cancel"
                )
            ],
        ]
    )

def admin_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin:orders")],
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:add_product")],
            [InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin:delete_product")],
            [InlineKeyboardButton(text="⬅️ Закрыть", callback_data="admin:close")],
        ]
    )


def admin_orders_kb(orders):
    buttons = []

    for order in orders[:10]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{order['id']} | {order['total_price']} ₽ | {order['status']}",
                    callback_data=f"admin:order:{order['id']}"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_order_kb(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆕 Новый", callback_data=f"admin:status:{order_id}:new"),
                InlineKeyboardButton(text="⏳ В обработке", callback_data=f"admin:status:{order_id}:processing"),
            ],
            [
                InlineKeyboardButton(text="✅ Завершен", callback_data=f"admin:status:{order_id}:completed"),
                InlineKeyboardButton(text="❌ Отменен", callback_data=f"admin:status:{order_id}:cancelled"),
            ],
            [
                InlineKeyboardButton(text="⬅️ К заказам", callback_data="admin:orders")
            ],
        ]
    )


def admin_categories_kb(categories):
    buttons = []

    for category in categories:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=category["name"],
                    callback_data=f"admin:addcat:{category['id']}"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_delete_products_kb(products):
    buttons = []

    for product in products[:15]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {product['name']}",
                    callback_data=f"admin:del:{product['id']}"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)