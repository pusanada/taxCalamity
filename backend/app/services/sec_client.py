import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

class SECClient:
    """
    Asynchronous client for interacting with the Securities and Exchange Commission (SEC) Thailand Open APIs.
    Enforces basic rate-limiting (maximum 5 requests per second) to stay compliant with SEC API policies.
    """
    
    BASE_URL = "https://api.sec.or.th"
    
    def __init__(self):
        self.factsheet_key = settings.SEC_FUND_FACTSHEET_KEY
        self.daily_info_key = settings.SEC_FUND_DAILY_INFO_KEY
        self.rate_limit_delay = 0.25  # 4 requests per second safety limit
        self.last_request_lock = asyncio.Lock()
        
    async def _request(
        self, 
        endpoint: str, 
        key: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> Any:
        """
        Sends an HTTP GET request to the SEC API with rate-limiting and authorization headers.
        """
        if not key:
            raise ValueError("SEC API subscription key is not configured.")
            
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Accept": "application/json"
        }
        
        async with self.last_request_lock:
            # Enforce request throttling delay
            await asyncio.sleep(self.rate_limit_delay)
            
        async with httpx.AsyncClient() as client:
            try:
                logger.debug(f"Calling SEC API: {url} with params={params}")
                response = await client.get(url, headers=headers, params=params, timeout=timeout)
                
                # Check for rate limiting status (429) or other failures
                if response.status_code == 429:
                    logger.warning("SEC API rate limit hit (429). Retrying after brief pause...")
                    await asyncio.sleep(2.0)
                    response = await client.get(url, headers=headers, params=params, timeout=timeout)
                    
                response.raise_for_status()
                
                # Handle 204 No Content or empty responses
                if response.status_code == 204 or not response.content.strip():
                    return {}
                    
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SEC API HTTP error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"SEC API Request error: {str(e)}")
                raise

    # --- Fund Factsheet API Endpoints ---
    
    async def get_amcs(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of all Asset Management Companies (AMCs) in Thailand.
        Endpoint: /FundFactsheet/fund/amc
        """
        return await self._request("FundFactsheet/fund/amc", self.factsheet_key)
        
    async def get_funds_by_amc(self, amc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the list of funds managed by a specific AMC.
        Endpoint: /FundFactsheet/fund/amc/{unique_id}
        """
        return await self._request(f"FundFactsheet/fund/amc/{amc_id}", self.factsheet_key)
        
    async def get_fund_suitability(self, proj_id: str) -> Dict[str, Any]:
        """
        Retrieves the suitability and risk level details of a specific fund.
        Endpoint: /FundFactsheet/fund/{proj_id}/suitability
        """
        try:
            result = await self._request(f"FundFactsheet/fund/{proj_id}/suitability", self.factsheet_key)
            # Response could be a list or a dictionary; handle both gracefully
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch suitability for {proj_id}: {str(e)}")
            return {}
            
    async def get_fund_fee(self, proj_id: str) -> Any:
        """
        Retrieves the fee and expense details of a specific fund.
        Endpoint: /FundFactsheet/fund/{proj_id}/fee
        """
        try:
            result = await self._request(f"FundFactsheet/fund/{proj_id}/fee", self.factsheet_key)
            return result
        except Exception as e:
            logger.warning(f"Failed to fetch fee for {proj_id}: {str(e)}")
            return []

    async def get_fund_policy(self, proj_id: str) -> Dict[str, Any]:
        """
        Retrieves the investment policy and asset class characteristics of a specific fund.
        Endpoint: /FundFactsheet/fund/{proj_id}/policy
        """
        try:
            result = await self._request(f"FundFactsheet/fund/{proj_id}/policy", self.factsheet_key)
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch policy for {proj_id}: {str(e)}")
            return {}

    # --- Fund Daily Info API Endpoints ---
    
    async def get_daily_nav(self, proj_id: str, nav_date: str) -> Dict[str, Any]:
        """
        Retrieves the NAV of a specific fund on a given date (format YYYY-MM-DD or YYYYMMDD).
        Endpoint: /FundDailyInfo/fund/{proj_id}/dailynav/{nav_date}
        """
        # Format date to eliminate hyphens if needed (SEC API uses YYYY-MM-DD or similar depending on operation)
        formatted_date = nav_date.replace("-", "")
        try:
            result = await self._request(f"FundDailyInfo/fund/{proj_id}/dailynav/{formatted_date}", self.daily_info_key)
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch NAV for {proj_id} on {nav_date}: {str(e)}")
            return {}
            
    async def get_fund_dividends(self, proj_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the dividend distribution history of a specific fund.
        Endpoint: /FundDailyInfo/fund/{proj_id}/dividend
        """
        try:
            result = await self._request(f"FundDailyInfo/fund/{proj_id}/dividend", self.daily_info_key)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Failed to fetch dividends for {proj_id}: {str(e)}")
            return []
