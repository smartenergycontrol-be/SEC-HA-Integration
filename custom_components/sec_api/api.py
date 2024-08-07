import aiohttp
import logging
from datetime import timedelta, datetime

_LOGGER = logging.getLogger(__name__)


class MyApi:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = None
        self.data = {}

    async def validate_connection(self) -> bool:
        """Validate the API connection and authentication."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                ) as response:
                    if response.status == 200:
                        _LOGGER.debug(
                            "Successfully authenticated with the Smart Energy Control API."
                        )
                        return True
                    else:
                        _LOGGER.debug(
                            "Failed to authenticate with the Smart Energy Control API. Status code: %s",
                            response.status,
                        )
                        return False
        except Exception as e:
            _LOGGER.error("Error validating API connection: %s", e)
            return False

    async def start_session(self):
        """Start the aiohttp session."""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_data(self, *args):
        """Fetch data from the API."""
        print(f"Fetching {self.base_url}?{'&'.join(args)}")
        async with self.session.get(
            f"{self.base_url}?{'&'.join(args)}",
            headers={"Authorization": f"Bearer {self.api_key}"},
        ) as response:
            return await response.json()

    async def fetch_keys(self):
        """Fetch only key names."""
        data = {}
        i = 0
        while len(data) == 0:
            data = await self.fetch_data(
                f"maand={self.get_current_month(i)}", f"jaar={self.get_current_year()}"
            )
            data = data.get("data", {})
            i -= 1
        return [x["name"] for _, x in data.items()]

    async def fetch_data_only(self, *args, show_prices=False):
        """Fetch only data without metadata."""
        data = {}
        sp = ""
        if show_prices:
            sp = "show_prices=yes&postcode=2060"
        i = 0
        while len(data) == 0 and i >= -11:
            data = await self.fetch_data(
                f"maand={self.get_current_month(i)}",
                f"jaar={self.get_current_year()}",
                *args,
                sp,
            )
            data = data.get("data", {})
            i -= 1
        return data

    def get_current_month(self, step=0):
        """Return the current month."""
        months = {
            1: "jan",
            2: "feb",
            3: "maa",
            4: "apr",
            5: "mei",
            6: "jun",
            7: "jul",
            8: "aug",
            9: "sep",
            10: "okt",
            11: "nov",
            12: "dec",
        }

        current_month_number = datetime.now().month

        try:
            return months[current_month_number + step]
        except KeyError:
            return "jul"

    def get_current_year(self, step=0):
        """Return the current year."""
        return datetime.now().year + step
