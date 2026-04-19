# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

func_idx = content.find("function updateRecentUI()")
oc = content.find('onclick=', func_idx)

snippet = content[oc:oc+80]

# BROKEN at 28-41 (14 chars):
# = chr(92), chr(39), chr(34), chr(43), 'r.id', chr(43), chr(34), chr(39), chr(92), chr(41), chr(34)
# = backslash, quote, dquote, +, r.id, +, dquote, quote, backslash, close-paren, dquote

# CORRECT at 28-40 (13 chars):
# = chr(39), chr(34), chr(43), 'r.id', chr(43), chr(39), chr(41), chr(34)
# = quote, dquote, +, r.id, +, quote, close-paren, dquote

# Build the broken 14-char string
broken = chr(92)+chr(39)+chr(34)+'+r.id+'+chr(34)+chr(39)+chr(92)+chr(41)+chr(34)
print(f"Broken: {repr(broken)}, len={len(broken)}")

# Build the correct 13-char string (without the final closing quote - it's at position 41)
correct = chr(39)+chr(34)+'+r.id+'+chr(34)+chr(39)+chr(41)+chr(34)
print(f"Correct: {repr(correct)}, len={len(correct)}")

if broken in content:
    print("Found broken!")
    # Replace
    new_content = content.replace(broken, correct, 1)
    with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed!")
else:
    print("Broken not found!")
    # Show what's actually there
    func_idx2 = content.find("function updateRecentUI()")
    oc2 = content.find('onclick=', func_idx2)
    actual = content[oc2:oc2+50]
    print(f"Actual: {repr(actual)}")
