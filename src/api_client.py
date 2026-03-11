import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.utils import setup_logger

logger = setup_logger(__name__)

class APIClient:
    def __init__(self, retries=5, backoff_factor=2):
        self.session = requests.Session()
        
        # Add User-Agent to mimic a browser/standard client
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_data(self, url: str, params: dict = None) -> dict | list | None:
        """
        Fetches data from the given URL.
        Returns the JSON response or None if failed.
        """
        try:
            logger.info(f"Fetching data from: {url}")
            response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            
            try:
                data = response.json()
                logger.info(f"Successfully fetched data from {response.url}")
                return data
            except ValueError:
                logger.error(f"Response from {url} is not valid JSON.")
                return None
                
        except requests.exceptions.HTTPError as errh:
            logger.error(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            logger.error(f"Something went wrong: {err}")
            
        return None
