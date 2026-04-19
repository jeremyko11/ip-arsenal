# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# The correct onclick we need in the HTML file:
correct = "onclick=\"openMaterialDrawer('\"+r.id+\"')\""
print("correct:", correct)

# What Python string literal (single-quoted) produces this?
# Using double-quoted Python string to avoid confusion:
test1 = "onclick=\"openMaterialDrawer('\"+r.id+\"')\""
print("test1 (double-quoted):", test1)
print("test1 == correct:", test1 == correct)

