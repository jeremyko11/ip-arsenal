with open('C:/Users/jeremyko11/WorkBuddy/Claw/ip-arsenal/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')
line = lines[861]
idx = line.find('onclick=')
snippet = line[idx:idx+70]
print("Current file repr:")
print(repr(snippet))
print()
# Decode character by character
print("Characters:")
for i, c in enumerate(snippet):
    if c == '\\' or c == "'":
        print(f"  {i}: {repr(c)} ord={ord(c)}")
    if i > 45:
        break
