from datetime import datetime, timedelta
from pathlib import Path
import random

import numpy as np
import pandas as pd

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

# ============================================================================
# Generate Inventory Data
# ============================================================================

inventory_data = []

devices = ['ICU-01', 'ICU-02', 'ER-MAIN', 'ER-TRAUMA', 'SURGERY-A', 'PHARMACY']
medications = [
    ('101', 'Acetaminophen 325mg Tab'),
    ('102', 'Ibuprofen 200mg Tab'),
    ('103', 'Morphine 2mg/mL Injection'),
    ('104', 'Fentanyl 50mcg/mL Injection'),
    ('105', 'Ondansetron 4mg Tab'),
    ('106', 'Metoprolol 25mg Tab'),
    ('107', 'Lisinopril 10mg Tab'),
    ('108', 'Insulin Aspart 100unit/mL'),
    ('109', 'Heparin 5000unit/mL Injection'),
    ('110', 'Normal Saline 0.9% 1000mL'),
    ('111', 'Amoxicillin 500mg Cap'),
    ('112', 'Vancomycin 500mg Injection'),
]

# Create inventory entries for each device
for device in devices:
    # Each device has 3-5 drawers
    num_drawers = random.randint(3, 5)
    for drawer in range(1, num_drawers + 1):
        # Each drawer has 2-4 medications
        selected_meds = random.sample(medications, random.randint(2, 4))
        for med_id, med_desc in selected_meds:
            location = f"{drawer}|{random.randint(1, 3)}|{random.randint(1, 5)}"
            
            # Vary par levels by medication type
            if 'Injection' in med_desc:
                min_qty = random.randint(2, 5)
                max_qty = random.randint(min_qty + 5, min_qty + 15)
            elif 'Saline' in med_desc:
                min_qty = random.randint(5, 10)
                max_qty = random.randint(min_qty + 10, min_qty + 20)
            else:
                min_qty = random.randint(10, 20)
                max_qty = random.randint(min_qty + 20, min_qty + 40)
            
            # Some items have orders, some don't
            has_orders = 'Y' if random.random() > 0.3 else 'N'
            
            inventory_data.append({
                'Device': device,
                'Drw|Sub Drw|Pkt': location,
                'Med ID': med_id,
                'Med Description': med_desc,
                'Min': min_qty,
                'Max': max_qty,
                'Active Orders': has_orders
            })

inventory_df = pd.DataFrame(inventory_data)

# ============================================================================
# Generate Usage Data
# ============================================================================

usage_data = []

# Generate 30 days of transaction history
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# For each inventory item, generate realistic transaction history
for _, inv_row in inventory_df.iterrows():
    device = inv_row['Device']
    location = inv_row['Drw|Sub Drw|Pkt']
    med_id = inv_row['Med ID']
    med_desc = inv_row['Med Description']
    min_qty = inv_row['Min']
    max_qty = inv_row['Max']
    
    # Start with initial refill
    current_qty = max_qty
    current_date = start_date
    
    # Add initial refill transaction
    usage_data.append({
        'Device': device,
        'Drw|Sub Drw|Pkt': location,
        'Med ID': med_id,
        'Med Description': med_desc,
        'Transaction Date/Time': current_date,
        'Transaction Type': 'Refill',
        'Beg': 0,
        'End': current_qty,
        'Min': min_qty,
        'Max': max_qty,
        'Active Orders': inv_row['Active Orders']
    })
    
    # Generate removal transactions over time
    # Higher usage for ER, lower for pharmacy
    if 'ER' in device:
        daily_removal_prob = 0.8
        avg_removals_per_day = random.uniform(2, 5)
    elif 'ICU' in device:
        daily_removal_prob = 0.7
        avg_removals_per_day = random.uniform(1, 3)
    elif 'SURGERY' in device:
        daily_removal_prob = 0.6
        avg_removals_per_day = random.uniform(1, 2)
    else:  # PHARMACY
        daily_removal_prob = 0.3
        avg_removals_per_day = random.uniform(0.5, 1.5)
    
    day = start_date
    while day <= end_date:
        # Decide if there are removals today
        if random.random() < daily_removal_prob:
            num_removals = int(np.random.poisson(avg_removals_per_day))
            
            for _ in range(num_removals):
                if current_qty <= 0:
                    break
                
                # Remove 1-3 units typically
                removal_qty = min(random.randint(1, 3), current_qty)
                beg_qty = current_qty
                current_qty -= removal_qty
                
                # Add some time variation during the day
                transaction_time = day + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                usage_data.append({
                    'Device': device,
                    'Drw|Sub Drw|Pkt': location,
                    'Med ID': med_id,
                    'Med Description': med_desc,
                    'Transaction Date/Time': transaction_time,
                    'Transaction Type': 'Remove',
                    'Beg': beg_qty,
                    'End': current_qty,
                    'Min': min_qty,
                    'Max': max_qty,
                    'Active Orders': inv_row['Active Orders']
                })
        
        # Refill if below minimum
        if current_qty <= min_qty:
            refill_qty = max_qty - current_qty
            beg_qty = current_qty
            current_qty = max_qty
            
            transaction_time = day + timedelta(
                hours=random.randint(6, 18),
                minutes=random.randint(0, 59)
            )
            
            usage_data.append({
                'Device': device,
                'Drw|Sub Drw|Pkt': location,
                'Med ID': med_id,
                'Med Description': med_desc,
                'Transaction Date/Time': transaction_time,
                'Transaction Type': 'Refill',
                'Beg': beg_qty,
                'End': current_qty,
                'Min': min_qty,
                'Max': max_qty,
                'Active Orders': inv_row['Active Orders']
            })
        
        day += timedelta(days=1)

usage_df = pd.DataFrame(usage_data)
usage_df = usage_df.sort_values(['Device', 'Drw|Sub Drw|Pkt', 'Med ID', 'Transaction Date/Time'])

# ============================================================================
# Save to Excel files
# ============================================================================

reports_dir = Path(__file__).parent.joinpath('reports')
reports_dir.mkdir(exist_ok=True)

inventory_df.to_excel(reports_dir.joinpath('Inventory.xlsx'), index=False)
usage_df.to_excel(reports_dir.joinpath('Usage.xlsx'), index=False)

print(f"Generated test data:")
print(f"- Inventory: {len(inventory_df)} entries across {len(devices)} devices")
print(f"- Usage: {len(usage_df)} transactions over 30 days")
print(f"\nFiles saved to:")
print(f"  - {reports_dir.joinpath('Inventory.xlsx').relative_to(Path.cwd())}")
print(f"  - {reports_dir.joinpath('Usage.xlsx').relative_to(Path.cwd())}")
print(f"\nSample inventory entries:")
print(inventory_df.head())
print(f"\nSample usage entries:")
print(usage_df.head())
