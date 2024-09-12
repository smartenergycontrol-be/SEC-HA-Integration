import aiohttp
import logging
import urllib.parse

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
                    headers={"Authorization": self.api_key},
                ) as response:
                    if response.status == 200:
                        _LOGGER.debug(
                            "Successfully authenticated with the Smart Energy Control API."
                        )
                        return True
                    else:
                        _LOGGER.info(
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
        _args = []
        for arg in args:
            _LOGGER.info(arg)
            _arg = arg.split("=")
            if len(_arg) == 2:
                _arg[1] = urllib.parse.quote(_arg[1])
                _arg = "=".join(_arg)
            elif _arg[0] == "show_prices":
                _arg = f"{_arg[0]}=yes"
            else:
                _arg = _arg[0]
            _args.append(_arg)
        # print(f"Fetching {self.base_url}?{'&'.join(args)}")
        # args = [urllib.parse.quote(arg) for arg in args]
        _LOGGER.info(f"{self.base_url}?{'&'.join(_args)}")
        async with self.session.get(
            f"{self.base_url}?{'&'.join(_args)}",
            headers={"Authorization": self.api_key},
        ) as response:
            return await response.json()

    async def fetch_keys(self):
        """Fetch only key names."""
        data = {}
        current_times = await self.get_current_time()
        data = await self.fetch_data(
            f"maand={current_times["maand"]}",
            f"jaar={current_times["jaar"]}",
        )
        data = data.get("data", {})
        return [x["name"] for _, x in data.items()]

    async def fetch_data_only(self, *args, show_prices=False, zip_code="2060"):
        """Fetch only data without metadata."""
        data = {}
        sp = ""
        if show_prices:
            sp = f"show_prices=yes&postcode={zip_code}"

        current_times = await self.get_current_time()
        data = await self.fetch_data(
            f"maand={current_times["maand"]}",
            f"jaar={current_times["jaar"]}",
            *args,
            sp,
        )
        return data.get("data", {})

    async def get_current_time(self):
        "Get current year and month."
        # print(f"Fetching {self.base_url[:-5]}/month")
        async with self.session.get(
            f"{self.base_url[:-5]}/month",
            headers={"Authorization": self.api_key},
        ) as response:
            return await response.json()
