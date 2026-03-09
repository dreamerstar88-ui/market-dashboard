import sys
sys.path.append('.')
import FinanceDataReader as fdr
import traceback

try:
    print("Testing KOSPI (KS11)...")
    df = fdr.DataReader('KS11')
    print(df.tail())
except Exception as e:
    print(f"KS11 Error: {e}")
    traceback.print_exc()

try:
    print("\nTesting KOSDAQ (KQ11)...")
    df = fdr.DataReader('KQ11')
    print(df.tail())
except Exception as e:
    print(f"KQ11 Error: {e}")
    traceback.print_exc()
