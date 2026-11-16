import time
import requests

BASE = "https://api-seller.uzum.uz/api/seller-openapi"


class UzumClient:
    def __init__(self, api_key: str):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": api_key, "Accept": "application/json"})

    def _get(self, path, **params):
        for attempt in range(4):
            r = self.s.get(BASE + path, params=params, timeout=30)
            if r.status_code != 429:
                break
            time.sleep(2 * (attempt + 1))
        if r.status_code >= 400:
            raise RuntimeError(f"Uzum API {r.status_code}: {r.text[:300]}")
        return r.json()

    def shops(self):
        return self._get("/v1/shops")

    def products(self, shop_id, page=0, size=20):
        return self._get(f"/v1/product/shop/{shop_id}", page=page, size=size)

    def orders(self, shop_ids, status=None, page=0, size=10):
        params = {"shopIds": shop_ids, "page": page, "size": size}
        if status:
            params["status"] = status
        return self._get("/v2/fbs/orders", **params)

    def order_count(self, shop_ids, status=None):
        params = {"shopIds": shop_ids}
        if status:
            params["status"] = status
        return self._get("/v2/fbs/orders/count", **params)

    def stocks(self):
        return self._get("/v1/fbs/sku/stocks")
