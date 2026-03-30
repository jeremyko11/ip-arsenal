"""给首页快速操作区增加'导入文件夹'按钮"""
path = r'C:\Users\jeremyko11\WorkBuddy\Claw\ip-arsenal\frontend\index.html'

with open(path, encoding='utf-8') as f:
    content = f.read()

old = (
    "    <div class=\"quick-btn\" onclick=\"openAddModal('book')\">\n"
    "      <div class=\"quick-icon\">📖</div>\n"
    "      <div class=\"quick-label\">上传书籍 PDF</div>\n"
    "      <div class=\"quick-desc\">一键提炼全书弹药</div>\n"
    "    </div>\n"
    "    <div class=\"quick-btn\" onclick=\"openAddModal('url')\">"
)

new = (
    "    <div class=\"quick-btn\" onclick=\"openAddModal('book')\">\n"
    "      <div class=\"quick-icon\">📖</div>\n"
    "      <div class=\"quick-label\">上传书籍 PDF</div>\n"
    "      <div class=\"quick-desc\">一键提炼全书弹药</div>\n"
    "    </div>\n"
    "    <div class=\"quick-btn\" onclick=\"openAddModal('folder')\">\n"
    "      <div class=\"quick-icon\">📁</div>\n"
    "      <div class=\"quick-label\">导入文件夹</div>\n"
    "      <div class=\"quick-desc\">批量导入整个书库</div>\n"
    "    </div>\n"
    "    <div class=\"quick-btn\" onclick=\"openAddModal('url')\">"
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('REPLACED OK')
else:
    print('NOT FOUND — dumping nearby lines:')
    idx = content.find("openAddModal('book')")
    print(repr(content[idx-5:idx+300]))
