# Test what Python produces for the Edit tool new_string
r = type('R', (), {'id': 'TEST123'})()

# What I want in the HTML file:
# onclick="openMaterialDrawer('"+r.id+"')"

# In the Edit tool new_string, I use a Python string literal
# The Python source code I pass to Edit tool is:
# NEW_STRING = 'onclick="openMaterialDrawer(\'"+r.id+"'\')"'

# Let's see what that Python source would produce:
# \' in Python source = \' (backslash-quote, not ending string)
# But we already established \' in single-quoted Python = \' = backslash followed by... wait

# Let me try it:
NEW_STRING = 'onclick="openMaterialDrawer(\'"+r.id+"'\')"'
print("NEW_STRING repr:", repr(NEW_STRING))
print("NEW_STRING value:", NEW_STRING)
