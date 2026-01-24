import sys
import os

# Mimic backend setup
sys.path.append(os.path.abspath(os.getcwd()))

try:
    print("Attempting to import FastAPI...")
    from fastapi import FastAPI
    print("FastAPI imported.")
    
    print("Attempting to import strategies...")
    from src.strategies.rob_reversal import RobReversal
    print("RobReversal imported.")
    
    print("Backend check passed!")
except Exception as e:
    print(f"Backend check FAILED: {e}")
    import traceback
    traceback.print_exc()
