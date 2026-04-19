# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取文件
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

# 打印每个字符
print("onclick snippet characters (positions 28-43):")
for i, c in enumerate(snippet[28:44], start=28):
    print(f"  [{i:2d}] char={repr(c):6s}  ord={ord(c):3d}")

print()
# Now fix: the broken sequence is:
# Positions 28-41: \'\'+r.id+\'\''\'
# That is: \ ' ' + r . i d + ' \ ' '
# We need:   \ ' " + r . i d + " \ '
# Which is:  \ '  "  + r . i d +  "  \ '
# In file chars: \ '  "  + r . i d +  "  \ '

# The broken pattern
broken = snippet[28:42]  # \'\'+r.id+\'\''\ (15 chars)
print(f"Broken pattern: {repr(broken)}")
print(f"Broken pattern chars: {[c for c in broken]}")

# The correct pattern
correct = "\\'\"'+r.id+'\"\\'"  # This is: \' " + r . i d + " \'
print(f"Correct pattern: {repr(correct)}")
print(f"Correct pattern chars: {[c for c in correct]}")

# Verify they're the same length
print(f"Broken len: {len(broken)}, Correct len: {len(correct)}")
