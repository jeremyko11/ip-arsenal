# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("function updateRecentUI()")
oc = content.find('onclick=', idx)
snippet = content[oc:oc+80]

# Find where the onclick value starts and ends
# onclick=" starts at 0
# openMaterialDrawer( starts at 9
# The problematic part starts at 28

# Print chars 28-43
print("Chars 28-43:")
for i in range(28, 44):
    c = snippet[i]
    print(f"  [{i:2d}] {repr(c):10s} ord={ord(c):3d}")

# The full onclick value (positions 0-41 based on my analysis):
# But let's find the closing "
end_quote = snippet.find('"', 42)
print(f"\nClosing quote at position: {end_quote}")
print(f"Full onclick value (0 to {end_quote}): {repr(snippet[:end_quote])}")

# Now, the onclick JavaScript expression should evaluate to:
# openMaterialDispatcher('test123')
# So the JS expression in the onclick should be:
# openMaterialDispatcher('"+r.id+"')
# Which is: openMaterialDispatcher( + ' + "+r.id+" + ' + )
# = openMaterialDispatcher('"+r.id+"')

# In the HTML file (as raw chars), this is:
# openMaterialDispatcher('"+r.id+"')
# Wait, in HTML attribute (double-quoted), the JS code is just written as-is
# So: onclick="openMaterialDispatcher('"+r.id+"')"
# And the JS expression is: openMaterialDispatcher('"+r.id+"')

# Let's verify: this JS expression evaluates to openMaterialDispatcher('test123') ✓

# The broken version is: onclick="openMaterialDispatcher(\'"+r.id+"\')"
# Where the \' is backslash-quote in the file
# And \" is also backslash-quote

# The fix: change \' to just ' (single quote)
# And change \" to just ' (single quote)
# So: onclick="openMaterialDispatcher('"+r.id+"')"

# In raw chars:
# Current broken: \'\"+r.id+\"\') = 14 chars (backslash, quote, dquote, +r.id+, dquote, backslash, quote, close-paren)
# We need: '"+r.id+"') = 11 chars (squote, dquote, +r.id+, squote, close-paren)

# Current broken
broken = snippet[28:42]
print(f"\nBroken (pos 28-42, {len(broken)} chars): {repr(broken)}")
print(f"Broken ord: {[ord(c) for c in broken]}")

# What we need - careful with Python string interpolation
needed = "'"+chr(43)+"r.id"+chr(43)+"')"
print(f"\nNeeded (11 chars): {repr(needed)}")
print(f"Needed ord: {[ord(c) for c in needed]}")
