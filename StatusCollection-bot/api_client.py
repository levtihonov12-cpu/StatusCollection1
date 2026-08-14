import httpx

API_BASE_URL = "http://127.0.0.1:8000"


async def get_categories():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/categories")
        response.raise_for_status()
        return response.json()


async def get_products(category_id=None):
    params = {}
    if category_id is not None:
        params["category_id"] = category_id

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/products", params=params)
        response.raise_for_status()
        return response.json()


async def get_product(product_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/products/{product_id}")
        response.raise_for_status()
        return response.json()


async def register_user(telegram_id: int, username=None, first_name=None, last_name=None):
    payload = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/api/users/register", json=payload)
        response.raise_for_status()
        return response.json()


async def create_order(telegram_id: int, customer_name: str, phone: str, address: str, items: list):
    payload = {
        "telegram_id": telegram_id,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "items": items,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/api/orders", json=payload)
        response.raise_for_status()
        return response.json()


async def get_orders(telegram_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/orders",
            params={"telegram_id": telegram_id}
        )
        response.raise_for_status()
        return response.json()


async def create_product(category_id, name, price, color=None, material=None, description=None, image_url=None):
    payload = {
        "category_id": category_id,
        "name": name,
        "price": price,
        "color": color,
        "material": material,
        "description": description,
        "image_url": image_url,
        "is_available": True,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/api/products", json=payload)
        response.raise_for_status()
        return response.json()


async def delete_product(product_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/api/products/{product_id}")
        response.raise_for_status()
        return response.json()


async def get_all_orders():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/orders/all")
        response.raise_for_status()
        return response.json()


async def update_order_status(order_id: int, status: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/orders/{order_id}/status",
            json={"status": status}
        )
        response.raise_for_status()
        return response.json()