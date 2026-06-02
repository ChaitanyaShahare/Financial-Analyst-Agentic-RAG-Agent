#!/usr/bin/env python3
"""Extract and display notebook contents."""
import json
from pathlib import Path

notebook_path = Path("notebook/Lab_6.4_Financial_Analyst_Agent.ipynb")

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)
    
print(f"Total cells: {len(nb['cells'])}\n")

for i, cell in enumerate(nb['cells']):
    print(f"\n{'='*80}")
    print(f"CELL {i} ({cell['cell_type'].upper()})")
    print(f"{'='*80}")
    
    src = ''.join(cell['source'])
    print(src)
    
print("\n" + "="*80)
print("END OF NOTEBOOK")
print("="*80)
