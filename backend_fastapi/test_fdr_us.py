
import FinanceDataReader as fdr

def test_fdr_us():
    print("\nTesting FinanceDataReader for US Stocks...")
    try:
        # Fetch Apple (NASDAQ:AAPL)
        df = fdr.DataReader('NASDAQ:AAPL', '2024-01-01', '2024-01-10')
        if not df.empty:
            print(f"✅ Success: AAPL data fetched ({len(df)} rows)")
            print(df.head(2))
            return True
        else:
            print("❌ Failed: Empty DataFrame for AAPL")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_fdr_us()
