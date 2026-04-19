# Test Python escaping
print(repr('\\'))          # backslash in single-quoted
print(repr("'"))           # single quote
print(repr("\\"))          # backslash
print(repr("a'b"))         # embedded quote
print(repr("a" + chr(92) + "b"))  # chr(92) = backslash
print("---")
# JS \' in file means: backslash-quote (escaped quote)
# In Python file, to write \' we need to put \' in the source
# Let's see what we get with Python's own escaping
s1 = chr(92) + "'"  # backslash + quote
print("s1 (chr(92)+quote):", repr(s1))
s2 = "\\" + "'"  # backslash + quote
print("s2 (backslash+quote):", repr(s2))
# \' in a Python string? Python would see \' as escaped quote...
# But we want to produce the characters: \ and '
# That is: chr(92) followed by "'"
# In a Python file string, to get \ and ' we write: chr(92)+"'"
# or we write: "\\'"? Let's see
s3 = "\\'"
print("s3 (backslash+quote via \\\\'):", repr(s3), "len:", len(s3))

