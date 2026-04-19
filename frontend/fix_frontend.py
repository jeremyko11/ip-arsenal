# -*- coding: utf-8 -*-
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert CSS before /* ─── Misc ─── */
style_marker = '/* ─── Misc ────────────────────────────────────────────── */'
pos = content.find(style_marker)
if pos == -1:
    print('CSS marker not found!')
    exit(1)

css = '''/* ─── IPA增强 ─── */
.material-preview-tooltip {
  position: fixed; z-index: 9999; max-width: 400px; max-height: 300px;
  background: var(--bg); border: 1px solid var(--border2); border-radius: 12px;
  padding: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  font-size: 13px; line-height: 1.6; pointer-events: none; display: none;
}
.material-preview-tooltip .preview-category { font-size: 11px; color: var(--accent); font-weight: 600; margin-bottom: 8px; }
.material-preview-tooltip .preview-content { color: var(--text); white-space: pre-wrap; }
.material-preview-tooltip .preview-meta { margin-top: 10px; font-size: 11px; color: var(--text3); }
.material-preview-tooltip .preview-hooks { display: flex; gap: 4px; margin-top: 8px; }
.material-preview-tooltip .hook-tag { background: rgba(124,92,252,0.1); color: var(--accent); padding: 2px 8px; border-radius: 10px; font-size: 10px; }
.mat-card.selected { outline: 2px solid var(--accent); }

'''
content = content[:pos] + css + content[pos:]

# 2. Add recent items after materialsState
state_marker = "let materialsState = { page: 1, total: 0, category: '', q: '', source_id: '', starred: -1, review_only: 0, items: [] };"
pos = content.find(state_marker)
if pos == -1:
    print('materialsState not found!')
    exit(1)

recent = '''
// IPA增强: 最近使用
const MAX_RECENT=10;
let _recentItems=JSON.parse(localStorage.getItem('iparsenal_recent')||'[]');
function addToRecent(item){_recentItems=_recentItems.filter(function(r){return r.id!==item.id;});_recentItems.unshift({id:item.id,title:(item.content||'').slice(0,60),category:item.category,ts:Date.now()});if(_recentItems.length>MAX_RECENT)_recentItems=_recentItems.slice(0,MAX_RECENT);localStorage.setItem('iparsenal_recent',JSON.stringify(_recentItems));updateRecentUI();}
function updateRecentUI(){var el=document.getElementById('recent-items');if(!el)return;if(!_recentItems.length){el.innerHTML='<div class="nav-section">最近使用</div><div class="nav-item" style="color:var(--text3)">暂无记录</div>';return;}el.innerHTML='<div class="nav-section">最近使用</div>'+_recentItems.map(function(r){return'<div class="nav-item" onclick="openMaterialDrawer(\\\''+r.id+'\\\')"><span class="cat-dot '+r.category+'"></span>'+(r.title||'').slice(0,30)+'</div>';}).join('');}
function openMaterialDrawer(id){var item=(materialsState.items||[]).find(function(m){return m.id===id;});if(!item)return;document.getElementById('drawer-content').innerHTML=renderDrawerContent(item);document.getElementById('drawer-panel').classList.add('open');addToRecent(item);}
'''
content = content[:pos+len(state_marker)] + '\n' + recent + content[pos+len(state_marker):]

# 3. Add keyboard shortcuts
kb_marker = '});\n\nfunction toggleBasket()'
pos = content.find(kb_marker)
if pos == -1:
    print('toggleBasket not found!')
    exit(1)

kb = '''
// IPA增强: 键盘快捷键
var _selIdx=-1;
document.addEventListener('keydown',function(e){
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA')return;
  var items=materialsState.items||[];
  if(!items.length)return;
  if(e.key==='j'||e.key==='ArrowDown'){e.preventDefault();_selIdx=Math.min(_selIdx+1,items.length-1);scrollToMaterial(_selIdx);}
  else if(e.key==='k'||e.key==='ArrowUp'){e.preventDefault();_selIdx=Math.max(_selIdx-1,0);scrollToMaterial(_selIdx);}
  else if(e.key==='s'){e.preventDefault();if(_selIdx>=0&&items[_selIdx])starMaterial(items[_selIdx].id);}
  else if(e.key==='c'){e.preventDefault();if(_selIdx>=0&&items[_selIdx])copyMaterial(items[_selIdx].id);}
  else if(e.key==='Enter'){e.preventDefault();if(_selIdx>=0&&items[_selIdx])openMaterialDrawer(items[_selIdx].id);}
  else if(e.key==='Escape'){closeModal();closeDrawer();}
});
function scrollToMaterial(idx){var cards=document.querySelectorAll('.mat-card');cards.forEach(function(el){el.classList.remove('selected');});if(cards[idx]){cards[idx].classList.add('selected');cards[idx].scrollIntoView({behavior:'smooth',block:'center'});}}
'''
content = content[:pos+2] + kb + content[pos+2:]

# 4. Add preview at end before </body>
preview = '''<div id="material-preview-tooltip" class="material-preview-tooltip" style="display:none">
  <div class="preview-category" id="ppt-category"></div>
  <div class="preview-content" id="ppt-content"></div>
  <div class="preview-meta" id="ppt-meta"></div>
  <div class="preview-hooks" id="ppt-hooks"></div>
</div>
<script>
(function(){
var pt=document.getElementById('material-preview-tooltip');
var _t=null;
document.addEventListener('mouseover',function(e){
  var card=e.target.closest('.mat-card');
  if(!card||card.closest('.basket-panel')||card.closest('#drawer-panel'))return;
  var id=card.dataset.id;if(!id)return;
  clearTimeout(_t);_t=setTimeout(function(){
    var item=(materialsState.items||[]).find(function(m){return m.id===id;});
    if(!item)return;
    document.getElementById('ppt-category').textContent=(item.category||'').toUpperCase();
    document.getElementById('ppt-content').textContent=(item.content||'').slice(0,200);
    var m=JSON.parse(item.metadata||'{}');
    document.getElementById('ppt-meta').textContent=(m.risk?'\u26a0 '+m.risk:'')+' | '+(m.scene?'\ud83c\udf1f '+m.scene:'')+' | \u4f7f\u7528 '+(item.use_count||0)+' \u6b21';
    var h=m.hooks||[];
    document.getElementById('ppt-hooks').innerHTML=h.map(function(x){return'<span class="hook-tag">'+x+'</span>'}).join('');
    var r=card.getBoundingClientRect();
    pt.style.display='block';
    pt.style.left=Math.min(r.left,window.innerWidth-420)+'px';
    var tp=r.bottom+8;
    pt.style.top=(tp+300>window.innerHeight?Math.max(0,r.top-310):tp)+'px';
  },400);
});
document.addEventListener('mouseout',function(e){
  var card=e.target.closest('.mat-card');
  if(card){clearTimeout(_t);pt.style.display='none';}
});
document.addEventListener('DOMContentLoaded',updateRecentUI);
})();
</script>
'''
last_body = content.rfind('</body>')
content = content[:last_body] + preview + '\n</body>'

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done! Size:', len(content))
print('</body> count:', content.count('</body>'))
