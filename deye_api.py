import hashlib
import aiohttp
import asyncio
import time
import logging

import logging
_LOGGER = logging.getLogger(__name__)

class DeyeCloudAPI:
    def __init__(self, base_url, app_id, app_secret, email, password, device_sn):
        self._base_url = base_url
        self._app_id = app_id
        self._app_secret = app_secret
        self._email = email
        self._password = password
        self._device_sn = device_sn

        self._token = None
        self._token_expiry = 0  # Epoch time in seconds
        self._session = aiohttp.ClientSession()

    async def close(self):
        await self._session.close()

    async def authenticate(self):
        now = time.time()
        if self._token and self._token_expiry > now:
            return

        _LOGGER.debug("Authenticating with: base_url=%s app_id=%s email=%s", self._base_url, self._app_id, self._email)

        url = f"{self._base_url}/account/token?appId={self._app_id}"
        hashed_password = hashlib.sha256(self._password.encode("utf-8")).hexdigest().lower()
        payload = {
            "appSecret": self._app_secret,
            "email": self._email,
            "password": hashed_password
        }

        try:
            async with self._session.post(url, json=payload) as resp:
                resp.raise_for_status()
                result = await resp.json()
                _LOGGER.debug("Authentication response: %s", result)
                if not result.get("accessToken"):
                    raise ValueError("No accessToken returned")

                self._token = result["accessToken"]
                self._token_expiry = time.time() + 3600
        except Exception as e:
            _LOGGER.exception("Authentication failed: %s", e)
            raise

    async def get_headers(self):
        await self.authenticate()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    async def get_realtime_data(self):
        if not self._device_sn:
            raise ValueError("Device Serial Number not set when calling get_realtime_data. Call set_device() first.")
        
        _LOGGER.info("Fetching realtime data...")
        url = f"{self._base_url}/device/latest"
        headers = await self.get_headers()
        payload = {"deviceList": [self._device_sn]}

        _LOGGER.info(f"Fetching realtime data for device {self._device_sn} from {url}")
        async with self._session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["deviceDataList"][0]["dataList"]

    async def get_time_of_use(self):
        if not self._device_sn:
            raise ValueError("Device Serial Number not set when calling get_time_of_use. Call set_device() first.")
        
        _LOGGER.info("Fetching TOU data...")
        url = f"{self._base_url}/config/tou"
        headers = await self.get_headers()
        payload = {"deviceSn": self._device_sn}

        _LOGGER.info(f"Fetching TOU data for device {self._device_sn} from {url}")
        async with self._session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            return result["timeUseSettingItems"]

    async def get_station_list_with_devices(self):
        _LOGGER.info("Fetching station list with devices...")
        url = f"{self._base_url}/station/listWithDevice"
        headers = await self.get_headers()
        payload = {"page": 1, "size": 50}

        async with self._session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            result = await resp.json()
            _LOGGER.debug("Station list response: %s", result)
            return result["stationList"]
