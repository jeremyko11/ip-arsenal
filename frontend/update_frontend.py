# -*- coding: utf-8 -*-
"""前端增强脚本 - 只能运行一次"""
import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

MARKER_CSS = '/* ─── IPA增强: Hover+KB ─── */'
if MARKER_CSS in content:
    print('Already updated, skipping')
    exit(0)

# 1. 添加 CSS - 在最后一个 </style> 之前
css_addition = '''
/* ─── IPA增强: Hover+KB ─── */
.material-preview-tooltip {
  position: fixed; z-index: 9999; max-width: 400px; max-height: 300px;
  background: var(--bg); border: 1px solid var(--border2); border-radius: 12px;
  padding: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  overflow-y: auto; font-size: 13px; line-height: 1.6; pointer-events: none; display: none;
}
.material-preview-tooltip .preview-category { font-size: 11px; color: var(--accent); font-weight: 600; margin-bottom: 8px; text-transform: uppercase; }
.material-preview-tooltip .preview-content { color: var(--text); white-space: pre-wrap; }
.material-preview-tooltip .preview-meta { margin-top: 10px; font-size: 11px; color: var(--text3); }
.material-preview-tooltip .preview-hooks { display: flex; gap: 4px; margin-top: 8px; flex-wrap: wrap; }
.material-preview-tooltip .hook-tag { background: rgba(124,92,252,0.1); color: var(--accent); padding: 2px 8px; border-radius: 10px; font-size: 10px; }
.mat-card.selected { outline: 2px solid var(--accent); }
'''

# 找到最后一个 </style>
last_style_pos = content.rfind('</style>')
content = content[:last_style_pos] + css_addition + '</style>' + content[last_style_pos + len('</style>'):]

# 2. 添加最近使用 - 在 materialsState 定义之后
recent_addition = '''
// ─── IPA增强: RECENT ───
const MAX_RECENT = 10;
let _recentItems = JSON.parse(localStorage.getItem('iparsenal_recent') || '[]');
function addToRecent(item) {
  _recentItems = _recentItems.filter(function(r) { return r.id !== item.id; });
  _recentItems.unshift({ id: item.id, title: (item.content || '').slice(0, 60), category: item.category, ts: Date.now() });
  if (_recentItems.length > MAX_RECENT) _recentItems = _recentItems.slice(0, MAX_RECENT);
  localStorage.setItem('iparsenal_recent', JSON.stringify(_recentItems));
  updateRecentUI();
}
function updateRecentUI() {
  var el = document.getElementById('recent-items');
  if (!el) return;
  if (!_recentItems.length) { el.innerHTML = '<div class="nav-section">最近使用</div><div class="nav-item" style="color:var(--text3)">暂无记录</div>'; return; }
  el.innerHTML = '<div class="nav-section">最近使用</div>' + _recentItems.map(function(r) {
    return '<div class="nav-item" onclick="openMaterialDrawer(\\'' + r.id + '\')"><span class="cat-dot ' + r.category + '"></span>' + (r.title || '').slice(0, 30) + '</div>';
  }).join('');
}
function openMaterialDrawer(id) {
  var item = (materialsState.items || []).find(function(m) { return m.id === id; });
  if (!item) return;
  document.getElementById('drawer-content').innerHTML = renderDrawerContent(item);
  document.getElementById('drawer-panel').classList.add('open');
  addToRecent(item);
}
'''

content = content.replace(
    "let materialsState = { page: 1, total: 0, category: '', q: '', source_id: '', starred: -1, review_only: 0, items: [] };",
    "let materialsState = { page: 1, total: 0, category: '', q: '', source_id: '', starred: -1, review_only: 0, items: [] };\n" + recent_addition,
    1
)

# 3. 添加键盘快捷键 - 在 basket event listener 之后
kb_addition = '''
// ─── IPA增强: KEYBOARD ───
var _selectedIndex = -1;
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  var items = materialsState.items || [];
  if (!items.length) return;
  if (e.key === 'j' || e.key === 'ArrowDown') {
    e.preventDefault();
    _selectedIndex = Math.min(_selectedIndex + 1, items.length - 1);
    scrollToMaterial(_selectedIndex);
  } else if (e.key === 'k' || e.key === 'ArrowUp') {
    e.preventDefault();
    _selectedIndex = Math.max(_selectedIndex - 1, 0);
    scrollToMaterial(_selectedIndex);
  } else if (e.key === 's') {
    e.preventDefault();
    if (_selectedIndex >= 0 && items[_selectedIndex]) starMaterial(items[_selectedIndex].id);
  } else if (e.key === 'c') {
    e.preventDefault();
    if (_selectedIndex >= 0 && items[_selectedIndex]) copyMaterial(items[_selectedIndex].id);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (_selectedIndex >= 0 && items[_selectedIndex]) openMaterialDrawer(items[_selectedIndex].id);
  } else if (e.key === 'Escape') {
    closeModal(); closeDrawer();
  }
});
function scrollToMaterial(idx) {
  var cards = document.querySelectorAll('.mat-card');
  cards.forEach(function(el) { el.classList.remove('selected'); });
  if (cards[idx]) { cards[idx].classList.add('selected'); cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' }); }
}
'''

content = content.replace("});\n\nfunction toggleBasket()", "});\n" + kb_addition + "\nfunction toggleBasket()", 1)

# 4. 添加悬停预览 HTML 和 JS - 在真正的 </body> 之前
# 找到最后一个 </body> 标签（而不是 iframe 里面的）
preview_html = '\n<!-- IPA增强: PREVIEW_HTML -->\n<div id="material-preview-tooltip" class="material-preview-tooltip">\n  <div class="preview-category" id="ppt-category"></div>\n  <div class="preview-content" id="ppt-content"></div>\n  <div class="preview-meta" id="ppt-meta"></div>\n  <div class="preview-hooks" id="ppt-hooks"></div>\n</div>\n'

preview_js = '''<script>
// ─── IPA增强: PREVIEW_JS ───
var _previewTimer = null;
document.addEventListener('mouseover', function(e) {
  var card = e.target.closest('.mat-card');
  if (!card || card.closest('.basket-panel') || card.closest('#drawer-panel')) return;
  var id = card.dataset.id;
  if (!id) return;
  clearTimeout(_previewTimer);
  _previewTimer = setTimeout(function() { showPreview(id, card); }, 400);
});
document.addEventListener('mouseout', function(e) {
  var card = e.target.closest('.mat-card');
  if (card) { clearTimeout(_previewTimer); hidePreview(); }
});
function showPreview(id, card) {
  var item = (materialsState.items || []).find(function(m) { return m.id === id; });
  if (!item) return;
  document.getElementById('ppt-category').textContent = (item.category || '').toUpperCase();
  document.getElementById('ppt-content').textContent = (item.content || '').slice(0, 200);
  var meta = JSON.parse(item.metadata || '{}');
  document.getElementById('ppt-meta').textContent = (meta.risk ? '\u26a0 ' + meta.risk : '') + ' | ' + (meta.scene ? '\ud83c\udf1f ' + meta.scene : '') + ' | \u4f7f\u7528 ' + (item.use_count || 0) + ' \u6b21';
  var hooks = meta.hooks || [];
  document.getElementById('ppt-hooks').innerHTML = hooks.map(function(h) { return '<span class="hook-tag">' + h + '</span>'; }).join('');
  var tooltip = document.getElementById('material-preview-tooltip');
  var rect = card.getBoundingClientRect();
  tooltip.style.display = 'block';
  tooltip.style.left = Math.min(rect.left, window.innerWidth - 420) + 'px';
  var topPos = rect.bottom + 8;
  tooltip.style.top = (topPos + 300 > window.innerHeight ? Math.max(0, rect.top - 310) : topPos) + 'px';
}
function hidePreview() { document.getElementById('material-preview-tooltip').style.display = 'none'; }
document.addEventListener('DOMContentLoaded', updateRecentUI);
</script>\n'''

# 找到真正的最后一个 </body>
last_body_pos = content.rfind('</body>')
content = content[:last_body_pos] + preview_html + preview_js + '</body>' + content[last_body_pos + len('</body>'):]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated successfully!')
print('Size:', len(content))
print('</body> count:', content.count('</body>'))
