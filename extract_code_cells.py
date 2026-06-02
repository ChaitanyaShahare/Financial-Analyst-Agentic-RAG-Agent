#!/usr/bin/env python3
"""Extract code cells from notebook."""
import json
from pathlib import Path

notebook_path = Path("notebook/Lab_6.4_Financial_Analyst_Agent.ipynb")

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

code_cells = []
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        code_cells.append({
            'index': i,
            'source': ''.join(cell['source'])
        })

# Save code cells to a Python file
output_code = "# Extracted from notebook\n" + "="*80 + "\n\n"
for cell in code_cells:
    output_code += f"# CELL {cell['index']}\n"
    output_code += f"# {'-'*76}\n"
    output_code += cell['source'] + "\n\n"

print(f"Found {len(code_cells)} code cells")
with open("notebook_code_extracted.py", 'w', encoding='utf-8') as f:
    f.write(output_code)
print("Saved to: notebook_code_extracted.py")
