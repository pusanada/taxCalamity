import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.services.sec_client import SECClient
from backend.app.services.fund_catalog import sync_funds_from_sec, decode_base64_safe
from backend.app.db.models import Fund

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_sec_client_request_headers():
    """
    Verifies that the SEC client attaches the correct subscription keys to headers.
    """
    client = SECClient()
    # Mock settings key values to be sure
    client.factsheet_key = "test_factsheet_key"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await client._request("FundFactsheet/test-endpoint", client.factsheet_key)
        
        assert result == {"status": "ok"}
        mock_get.assert_called_once()
        # Verify headers parameter passed to httpx client
        args, kwargs = mock_get.call_args
        headers = kwargs.get("headers")
        assert headers is not None
        assert headers.get("Ocp-Apim-Subscription-Key") == "test_factsheet_key"

@pytest.mark.anyio
async def test_sec_client_rate_limiting():
    """
    Verifies that consecutive requests have a rate-limiting delay.
    """
    client = SECClient()
    client.rate_limit_delay = 0.05  # speed up test
    client.factsheet_key = "test_key"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        # Call request twice
        start_time = asyncio.get_event_loop().time()
        await client._request("endpoint1", client.factsheet_key)
        await client._request("endpoint2", client.factsheet_key)
        end_time = asyncio.get_event_loop().time()
        
        # The time elapsed should be at least rate_limit_delay
        assert (end_time - start_time) >= 0.05

def test_base64_decoder():
    """
    Tests that the base64 safe decoder handles padding and decodes properly.
    """
    # Test valid base64 (e.g. "Equity" -> "RXF1aXR5")
    assert decode_base64_safe("RXF1aXR5") == "Equity"
    # Test unpadded base64 ("Fixed Income" -> "Rml4ZWQgSW5jb21l")
    assert decode_base64_safe("Rml4ZWQgSW5jb21l") == "Fixed Income"
    # Test invalid base64 (should return original string)
    assert decode_base64_safe("invalid@@@") == "invalid@@@"

@pytest.mark.anyio
async def test_sync_funds_from_sec():
    """
    Mocks SEC API responses and tests the sync_funds_from_sec database seeder.
    """
    mock_amcs = [
        {"unique_id": "AMC_KASIKORN", "name_en": "KASIKORN ASSET MANAGEMENT", "name_th": "บลจ. กสิกรไทย"},
        {"unique_id": "AMC_OTHER", "name_en": "OTHER AMC", "name_th": "บลจ. อื่นๆ"}
    ]
    
    mock_funds = [
        {"proj_id": "M0001", "proj_abbr_name": "K-STAR-SSF", "proj_name_en": "K Star SSF", "proj_name_th": "กองทุนเปิดเคสตาร์ SSF"},
        {"proj_id": "M0002", "proj_abbr_name": "K-GOLD-RMF", "proj_name_en": "K Gold RMF", "proj_name_th": "กองทุนเปิดเคโกลด์ RMF"},
        {"proj_id": "M0003", "proj_abbr_name": "K-ESG-ThaiESG", "proj_name_en": "K ESG ThaiESG", "proj_name_th": "กองทุนเค ESG สะสมทรัพย์"}
    ]
    
    mock_suitability = {"risk_spectrum": "RS6"}
    
    mock_fees = [
        {"fee_type_desc": "ค่าธรรมเนียมและค่าใช้จ่ายรวมทั้งหมด", "actual_value": 1.45, "rate": 2.50}
    ]
    
    mock_policy = {
        "policy_desc": "ตราสารทุน",
        "investment_policy_desc": "RXF1aXR5" # Base64 for "Equity"
    }
    
    # Mock SEC client calls
    with patch("backend.app.services.sec_client.SECClient.get_amcs", new_callable=AsyncMock) as mock_get_amcs, \
         patch("backend.app.services.sec_client.SECClient.get_funds_by_amc", new_callable=AsyncMock) as mock_get_funds, \
         patch("backend.app.services.sec_client.SECClient.get_fund_suitability", new_callable=AsyncMock) as mock_get_suitability, \
         patch("backend.app.services.sec_client.SECClient.get_fund_fee", new_callable=AsyncMock) as mock_get_fee, \
         patch("backend.app.services.sec_client.SECClient.get_fund_policy", new_callable=AsyncMock) as mock_get_policy:
         
        mock_get_amcs.return_value = mock_amcs
        mock_get_funds.return_value = mock_funds
        mock_get_suitability.return_value = mock_suitability
        mock_get_fee.return_value = mock_fees
        mock_get_policy.return_value = mock_policy
        
        # Mock database session
        db_mock = MagicMock()
        # Mock query return values
        db_mock.query().filter().first.return_value = None # Assume no pre-existing funds
        
        result = await sync_funds_from_sec(db_mock)
        
        assert result["status"] == "success"
        assert result["synced_count"] == 3
        
        # Verify database add calls
        assert db_mock.add.call_count == 3
        
        # Verify the details of the first added fund
        first_fund_call = db_mock.add.call_args_list[0]
        fund_obj = first_fund_call[0][0]
        assert isinstance(fund_obj, Fund)
        assert fund_obj.proj_id == "M0001"
        assert fund_obj.name == "K-STAR-SSF (K Star SSF)"
        assert fund_obj.tax_type == "SSF"
        assert fund_obj.risk_level == 6
        assert fund_obj.expense_ratio == 1.45
        assert fund_obj.asset_class == "Equity"
        assert fund_obj.objective == "Equity"
