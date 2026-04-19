# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 updateRecentUI 函数
func_name = "function updateRecentUI()"
idx = content.find(func_name)

# 找到函数结束
brace_count = 0
in_func = False
func_start = -1
for i in range(idx, len(content)):
    c = content[i]
    if c == '{':
        brace_count += 1
        in_func = True
        if func_start == -1:
            func_start = i
    elif c == '}':
        brace_count -= 1
        if brace_count == 0 and in_func:
            func_end = i
            break

func_body = content[func_start:func_end+1]
onclick_idx = func_body.find('onclick=')
snippet = func_body[onclick_idx:onclick_idx+80]

# 分析字节
print("Raw file bytes (positions 28-50):")
for i in range(28, min(50, len(snippet))):
    c = snippet[i]
    print(f"  [{i:2d}] {repr(c):8s}  ord={ord(c):3d}  {'BACKSLASH' if c == chr(92) else 'QUOTE' if c == chr(39) else 'DBLQUOT' if c == chr(34) else 'other'}")

print()
# What JavaScript sees:
# The onclick attribute value (after HTML parsing) is the string:
# openMaterialDrawer(\''+r.id+'\''\')
# Let's see what this evaluates to
js_snippet = snippet[onclick_idx+9:onclick_idx+9+20]  # +9 to skip onclick="
print(f"JS snippet: {repr(js_snippet)}")
print("This JS string would evaluate to:")
for c in js_snippet:
    if c == chr(92):
        print("  BACKSLASH")
    elif c == chr(39):
        print("  QUOTE (string delimiter)")
    elif c == chr(34):
        print("  DBLQUOTE")
    else:
        print(f"  {c}")

# What we NEED the JS to be:
# openMaterialDrawer('"+r.id+"')
# i.e.: \'  "  + r . i d +  "  \'
# So: \'  "  + r . i d +  "  \'  \')
print()
print("What we need: openMaterialDrawer('\"+r.id+\"'\\')")
print("i.e. chars: backslash-quote, doublequote, +r.id+, doublequote, backslash-quote, paren, paren, dblquote")
