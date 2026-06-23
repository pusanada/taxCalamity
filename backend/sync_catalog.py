import asyncio
import sys
import os
import logging

# Ensure absolute root path is configured
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from backend.app.db.database import init_db, SessionLocal
from backend.app.services.fund_catalog import sync_funds_from_sec
from backend.app.db.models import Fund

async def main():
    print("=== SEC API FUND CATALOG SYNCHRONIZER ===")
    print("Initializing Database...")
    init_db()
    
    db = SessionLocal()
    try:
        print("\nStarting synchronization with SEC API (this may take up to a minute)...")
        result = await sync_funds_from_sec(db)
        
        print("\n=== SYNCHRONIZATION SUMMARY ===")
        print(f"Status: {result.get('status')}")
        if result.get("status") == "success":
            print(f"Funds successfully synced: {result.get('synced_count')}")
            print(f"Errors encountered: {result.get('errors_count')}")
            
            # Query and display the newly synced funds from local SQLite
            db_funds = db.query(Fund).all()
            print(f"\nTotal funds now cached in database: {len(db_funds)}")
            print("\nSample Synced Funds:")
            for idx, fund in enumerate(db_funds[:5]):
                print(f"  {idx+1}. Code: {fund.name.split(' ')[0]} | Name: {fund.name} | Tax: {fund.tax_type} | Risk: {fund.risk_level} | Fee: {fund.expense_ratio}%")
        else:
            print(f"Sync failed. Error: {result.get('error')}")
            
    except Exception as e:
        print(f"\nError running sync command: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Force stdout to output in UTF-8 to prevent Windows terminal character errors
    import io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
    asyncio.run(main())
