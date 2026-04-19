# -*- coding: utf-8 -*-
# 直接修复 index.html 中的 updateRecentUI 函数

with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 updateRecentUI 函数的起始和结束
import re

# 查找包含 updateRecentUI 的行
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'function updateRecentUI()' in line:
        print(f"Found at line {i+1}")
        # 找到这个函数的结束大括号
        start = i
        brace_count = 0
        func_start = -1
        for j in range(i, len(lines)):
            for c in lines[j]:
                if c == '{':
                    if func_start == -1:
                        func_start = j
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0 and func_start != -1:
                        print(f"Function ends at line {j+1}")
                        end = j
                        print("Function body (first 200 chars of start line):")
                        print(lines[start][:200])
                        # Find the onclick part
                        for k in range(start, j+1):
                            if 'onclick=' in lines[k]:
                                idx = lines[k].find('onclick=')
                                print(f"onclick at line {k+1}, col {idx}: {lines[k][idx:idx+80]}")
                        break
                if j > i + 5:  # Only check first few lines
                    break
        break

# Also find the addToRecent and openMaterialDrawer functions
for i, line in enumerate(lines):
    if 'function addToRecent' in line or 'function openMaterialDrawer' in line:
        print(f"Line {i+1}: {line[:120]}")
