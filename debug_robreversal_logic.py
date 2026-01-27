
import pandas as pd
import numpy as np
from dataclasses import dataclass

# Mock params
p = {
    'max_stop_loss': 35.0,
    'tick_size': 0.25,
    'take_profit': 35.0
}

def check_short_logic():
    print("--- Checking Short Logic ---")
    
    # Scenario: Huge Bearish Channel
    # Setup Bar (i): 
    # High = 100
    # Low = 40
    # Open = 50
    # Close = 80 (Bullish)
    
    # Entry = Low - tick = 39.75
    # Raw SL = High - Entry = 100 - 39.75 = 60.25
    # Max SL = 35.0
    # Expected SL = Entry + 35 = 74.75
    
    H = 100.0
    L = 40.0
    ts_tick = 0.25
    
    pending_short_entry = L - ts_tick
    
    actual_sl_price = H
    raw_sl = H - pending_short_entry
    
    print(f"Entry: {pending_short_entry}")
    print(f"High: {H}")
    print(f"Raw SL Dist: {raw_sl}")
    
    if raw_sl > p['max_stop_loss']:
        actual_sl_price = pending_short_entry + p['max_stop_loss']
        print(f"Capped SL triggered. New SL Price: {actual_sl_price}")
    else:
        print(f"Raw SL used: {actual_sl_price}")
        
    pending_short_sl = actual_sl_price
    
    # Sizing Calc
    dist = pending_short_sl - pending_short_entry
    print(f"Sizing Dist: {dist}")
    
    # Execution Simulation
    # Next Bar (i+1)
    # Open = 90 (Gap Up!)
    # Low = 85
    # High = 110
    
    O = 90.0
    active_sl = pending_short_sl
    
    print(f"\nNext Bar Open: {O}")
    print(f"Active SL: {active_sl}")
    
    # Gap Check
    # Short: If O >= active_sl
    if O >= active_sl:
        print(f"Gap SL Hit! Exec Price: {O}")
        realized_loss = O - pending_short_entry
        print(f"Realized Loss: {realized_loss}")
    else:
        print("No Gap SL.")
        
    # Check what if O < active_sl but High hits it?
    O2 = 60.0 # Open inside range
    H2 = 80.0 # Hits SL (74.75)
    
    if O2 < active_sl:
        print(f"\nScenario 2 (Intrabar): Open {O2}, High {H2}")
        if H2 >= active_sl:
            print(f"Intrabar SL Hit! Exec Price: {active_sl}")
            realized_loss = active_sl - pending_short_entry
            print(f"Realized Loss: {realized_loss}")

if __name__ == "__main__":
    check_short_logic()
