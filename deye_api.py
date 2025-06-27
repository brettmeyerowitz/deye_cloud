import hashlib
import aiohttp
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class DeyeCloudAPI:
    def __init__(self, base_url, app_id, app_secret, email, password, device_id):
        self._base_url = base_url
        self._app_id = app_id
        self._app_secret = app_secret
        self._email = email
        self._password = password
        self._device_id = device_id

        self._token = None
        self._token_expiry = 0  # Epoch time in seconds
        self._session = aiohttp.ClientSession()

    async def close(self):
        await self._session.close()

    async def authenticate(self):
        now = time.time()
        if self._token and self._token_expiry > now:
            return  # Still valid

        logger.info(f"Authenticating with Deye Cloud API {self._base_url} using appId {self._app_id} and email {self._email}")
        
        url = f"{self._base_url}/account/token?appId={self._app_id}"
        hashed_password = hashlib.sha256(self._password.encode("utf-8")).hexdigest().lower()
        payload = {
            "appSecret": self._app_secret,
            "email": self._email,
            "password": hashed_password
        }

        async with self._session.post(url, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            self._token = result["accessToken"]
            self._token_expiry = time.time() + 3600  # Deye tokens last 1 hour

    async def get_headers(self):
        await self.authenticate()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    async def get_realtime_data(self):
        logger.info("Fetching realtime data...")
        url = f"{self._base_url}/device/latest"
        headers = await self.get_headers()
        payload = {"deviceList": [self._device_id]}

        logger.info(f"Fetching realtime data for device {self._device_id} from {url}")
        async with self._session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["deviceDataList"][0]["dataList"]

    async def get_time_of_use(self):
        logger.info("Fetching TOU data...")
        url = f"{self._base_url}/config/tou"
        headers = await self.get_headers()
        payload = {"deviceSn": self._device_id}

        logger.info(f"Fetching TOU data for device {self._device_id} from {url}")
        async with self._session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["timeUseSettingItems"]
