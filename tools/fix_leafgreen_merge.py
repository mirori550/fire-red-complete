#!/usr/bin/env python3
"""Relax the LeafGreen encounter merger so duplicate FireRed-exclusive slots may be reused.

This preserves at least one occurrence of every FireRed-exclusive species while
allowing LeafGreen exclusives to be added to tables such as Safari Zone Center
water encounters, where every available slot may otherwise be version-exclusive.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tools/apply_fire_red_complete.py"
text = path.read_text(encoding="utf-8")
old = '''                    for idx in range(len(fr_mons) - 1, -1, -1):
                        current = fr_mons[idx]["species"]
                        if current in FR_KANTO_EXCLUSIVES:
                            continue
                        if counts[current] > 1:
                            candidate = idx
                            break
'''
new = '''                    for idx in range(len(fr_mons) - 1, -1, -1):
                        current = fr_mons[idx]["species"]
                        # A duplicated FireRed-exclusive slot is safe to reuse:
                        # at least one copy of that species remains obtainable.
                        if current in FR_KANTO_EXCLUSIVES and counts[current] <= 1:
                            continue
                        if counts[current] > 1:
                            candidate = idx
                            break
'''
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise RuntimeError("LeafGreen merger patch target not found")
path.write_text(text, encoding="utf-8")
print("LeafGreen encounter merge safety rule updated.")
