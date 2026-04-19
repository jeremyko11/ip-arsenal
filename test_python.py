# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Test what chr(92)+chr(39) gives
s1 = chr(92) + chr(39)
print(f"chr(92)+chr(39) = {repr(s1)}, len={len(s1)}, chars={[c for c in s1]}")

# What I want is: \' in the file (backslash, single-quote)
# In Python: chr(92) + chr(39) = \' (2 chars)

# The correct onclick we need (from file positions 28-41, 14 chars):
# '\"+r.id+"\')  = single-quote, dquote, +, r, ., i, d, +, dquote, squote, \, )
# That's: chr(39)+chr(34)+'+r.id+'+chr(34)+chr(39)+chr(92)+chr(41)
correct = chr(39)+chr(34)+'+r.id+'+chr(34)+chr(39)+chr(92)+chr(41)
print(f"correct: {repr(correct)}, len={len(correct)}, chars={[c for c in correct]}")

# But this has chr(92) = backslash! We don't want backslash!
# We need: '\"+r.id+"\')
# Which is: chr(39)+chr(34)+'+r.id+'+chr(34)+chr(39)+chr(41)
# That's: quote, dquote, +, r.i d, +, dquote, squote, close-paren = 11 chars
# Wait, that's 8 + 6 = 11 chars. We need 14 chars.

# Let me think again. The FULL onclick attribute (42 chars):
# onclick="openMaterialDispatcher(\'"+r.id+"\')
# = 9 + 19 + 13 + 1 = 42
# The JS expression (positions 9-41) is 32 chars:
# openMaterialDispatcher(\'"+r.id+"\')
# The argument to openMaterialDispatcher (positions 28-40) is 13 chars:
# \'\"+r.id+\"\')
# = \' (2) + \" (2) + +r.id+ (6) + \' (2) + ) (1) = 13

# To call openMaterialDispatcher('test123'), the argument needs to be the STRING 'test123'
# As a JS STRING value (for the onclick), this is written as: \'test123\'
# Which is: \' + test123 + \' = chr(92)chr(39) + test123 + chr(92)chr(39)

# For the dynamic r.id case:
# The JS string needs to be: \' + r.id + \' = chr(92)chr(39)+r.id+chr(92)chr(39)
# When JS evaluates this: chr(92)chr(39) = \'
# So the STRING VALUE is: 'test123'

# In the HTML file (as attribute value), this is written as:
# \'\"+r.id+\"\')
# Where \' is backslash-single-quote (2 chars in file)

# Wait, but in the HTML attribute value (double-quoted), the JS string delimiters
# should be single quotes ' !
# So the JS code in the onclick is: openMaterialDispatcher('"+r.id+"')
# Where ' are just regular single quotes (1 char each in the file)

# When HTML parser reads onclick="openMaterialDispatcher('"+r.id+"')",
# it gives the JS code: openMaterialDispatcher('"+r.id+"')
# JS evaluates: ' + r.id + ' = 'test123'
# Result: openMaterialDispatcher('test123') - CORRECT!

# So the correct HTML onclick is:
# onclick="openMaterialDispatcher('"+r.id+"')"
# In the file (raw chars): onclick="openMaterialDispatcher('"+r.id+"')

# Let me construct this character by character
correct_html = (
    'onclick="'
    'openMaterialDispatcher('
    "'"  # single quote
    '"+r.id+"'  # this is a string containing "+r.id+" - but wait, + is not in quotes!
    "'"  # single quote
    ')"'
)
# Wait, in Python '",' would end the string!
# Let me use chr():
correct_html = ''.join([
    'onclick="',
    'openMaterialDispatcher(',
    chr(39),  # single quote
    '"+r.id+"',
    chr(39),  # single quote
    ')"'
])
print(f"correct_html: {repr(correct_html)}, len={len(correct_html)}")

# Now check against the actual file
with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

func_idx = content.find("function updateRecentUI()")
oc = content.find('onclick=', func_idx)
actual = content[oc:oc+80]

print(f"\nActual: {repr(actual[:50])}")
print(f"correct_html matches: {actual.startswith(correct_html)}")
