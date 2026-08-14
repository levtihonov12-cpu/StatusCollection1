import httpx

_BASE_URL = "http://127.0.0.1:8000"

class ApiClient:
    def __init__(self, base_url: str = _BASE_URL):
        self.base_url = base_url

    async def _request(self, method: str, endpoint: str, **kwargs):
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{self.base_url}{endpoint}"
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

    async def fetch_categories(self):
        return await self._request("GET", "/api/categories")

    async def fetch_products(self, category_id: int = None):
        params = {"category_id": category_id} if category_id else {}
        return await self._request("GET", "/api/products", params=params)

    async def fetch_product_details(self, product_id: int):
        return await self._request("GET", f"/api/products/{product_id}")

    async def register_telegram_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
        payload = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        }
        return await self._request("POST", "/api/users/register", json=payload)

    async def create_new_order(self, telegram_id: int, customer_name: str, phone: str, address: str, items: list):
        payload = {
            "telegram_id": telegram_id,
            "customer_name": customer_name,
            "phone": phone,
            "address": address,
            "items": items,
        }
        return await self._request("POST", "/api/orders", json=payload)

    async def fetch_user_orders(self, telegram_id: int):
        return await self._request("GET", "/api/orders", params={"telegram_id": telegram_id})

    async def add_new_product(self, category_id, name, price, color=None, material=None, description=None, country=None, image_url=None):
        payload = {
            "category_id": category_id,
            "name": name,
            "price": price,
            "color": color,
            "material": material,
            "description": description,
            "country": country,
            "image_url": image_url,
            "is_available": True,
        }
        return await self._request("POST", "/api/products", json=payload)

    async def remove_product(self, product_id: int):
        return await self._request("DELETE", f"/api/products/{product_id}")

    async def fetch_all_orders(self):
        return await self._request("GET", "/api/orders/all")

    async def change_order_status(self, order_id: int, status: str):
        return await self._request("POST", f"/api/orders/{order_id}/status", json={"status": status})

api = ApiClient()