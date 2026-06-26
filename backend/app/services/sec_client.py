import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from backend.app.config import settings

logger = logging.getLogger(__name__)


class SECClient:
    """Async client for the SEC Thailand Open API **v2** (Mutual Fund Factsheet).

    The SEC migrated to a new platform: all mutual-fund endpoints live under
    `/v2/fund/...`, share a single `Ocp-Apim-Subscription-Key`, and return a
    `{message, page_size, next_cursor, items: [...]}` envelope with cursor-based
    pagination. This client is a thin wrapper over the three endpoints the fund
    catalog needs (general-info profiles, factsheet risk-spectrum, factsheet
    fees); classification/enrichment lives in fund_catalog.sync_funds_from_sec.
    """

    BASE_URL = "https://api.sec.or.th"
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self):
        self.factsheet_key = settings.SEC_FUND_FACTSHEET_KEY
        self.rate_limit_delay = 0.25  # ~4 req/s, within SEC's stated policy
        self._lock = asyncio.Lock()

    async def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> Dict[str, Any]:
        if not self.factsheet_key:
            raise ValueError("SEC API subscription key is not configured.")
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = {"Ocp-Apim-Subscription-Key": self.factsheet_key, "Accept": "application/json"}
        last_err = None
        for attempt in range(retries):
            # Throttle to respect the SEC rate limit.
            async with self._lock:
                await asyncio.sleep(self.rate_limit_delay)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=headers, params=params, timeout=timeout)
                if resp.status_code in self.RETRY_STATUSES:
                    last_err = f"HTTP {resp.status_code}"
                    logger.warning(f"SEC API {resp.status_code} on {endpoint} (attempt {attempt + 1}) — retrying")
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                if resp.status_code == 204 or not resp.content.strip():
                    return {}
                return resp.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SEC API HTTP error on {endpoint}: {e.response.status_code} - {e.response.text[:200]}")
                raise
            except Exception as e:
                last_err = str(e)
                logger.warning(f"SEC API request error on {endpoint} (attempt {attempt + 1}): {last_err}")
                await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"SEC API request failed after {retries} attempts: {last_err}")

    async def fetch_profiles_page(self, next_cursor: str = "") -> Tuple[List[Dict[str, Any]], str]:
        """One page of `/v2/fund/general-info/profiles` — fund general info:
        `proj_id`, `proj_name_th/en`, `proj_abbr_name`, `policy_desc` (asset class),
        and `fund_class_tax_incentive_type` (SSF / Thai ESG flag). Returns
        (items, next_cursor); an empty next_cursor means no more pages."""
        params = {"next_cursor": next_cursor} if next_cursor else None
        data = await self._get("v2/fund/general-info/profiles", params=params)
        return (data.get("items") or []), (data.get("next_cursor") or "")

    async def get_risk_spectrum(self, proj_id: str) -> List[Dict[str, Any]]:
        """`/v2/fund/factsheet/risk-spectrum?proj_id=` — monthly risk history;
        each item has `risk_spectrum` like "RS6" and an `end_date`."""
        data = await self._get("v2/fund/factsheet/risk-spectrum", params={"proj_id": proj_id})
        return data.get("items") or []

    async def get_fees(self, proj_id: str) -> List[Dict[str, Any]]:
        """`/v2/fund/factsheet/fees?proj_id=` — fee rows with `fee_type_desc`,
        `rate`, and `actual_value`."""
        data = await self._get("v2/fund/factsheet/fees", params={"proj_id": proj_id})
        return data.get("items") or []
