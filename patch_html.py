"""Patch HTML to show ARN and test button"""
with open('templates/index.html', encoding='utf-8') as f:
    html = f.read()

# Find and replace the renderCreateResults function
old_fn = '''function renderCreateResults(results) {
  const el = $('createResults');
  if (!results.length) { el.innerHTML = ''; return; }
  let html = '<div class="result-scroll">';
  results.forEach(r => {
    const badge = r.ok
      ? '<span class="badge badge-ok">成功</span>'
      : '<span class="badge badge-err">失败</span>';
    const detail = r.ok
      ? `${escapeHtml(r.name)} · ${escapeHtml(r.region)} · ${escapeHtml(r.model_label || r.model_id)}`
      : `${escapeHtml(r.region)} · ${escapeHtml(r.model_label || r.model_id)} · ${escapeHtml(r.error || '')}`;
    html += `<div class="result-item">${badge}<span>${detail}</span></div>`;
  });
  html += '</div>';
  el.innerHTML = html;
}'''

new_fn = '''function renderCreateResults(results) {
  const el = $('createResults');
  if (!results.length) { el.innerHTML = ''; return; }
  let html = '<div class="table-wrap" style="max-height:380px;margin-top:12px"><table><thead><tr>';
  html += '<th>状态</th><th>区域</th><th>版本</th><th>ARN</th><th style="width:100px">操作</th></tr></thead><tbody>';
  results.forEach((r, i) => {
    const badge = r.ok ? '<span class="badge badge-ok">成功</span>' : '<span class="badge badge-err">失败</span>';
    const arnCell = r.ok
      ? `<span class="truncate" title="${escapeHtml(r.inferenceProfileArn)}" style="font-family:monospace;font-size:11px;display:block;max-width:400px">${escapeHtml(r.inferenceProfileArn)}</span>`
      : `<span style="color:var(--danger);font-size:11px">${escapeHtml(r.error||'')}</span>`;
    const actions = r.ok
      ? `<button class="btn btn-sm" onclick="copyText('${escapeHtml(r.inferenceProfileArn)}')">复制</button>
         <button class="btn btn-sm" id="testBtn${i}" onclick="testArn('${escapeHtml(r.region)}','${escapeHtml(r.inferenceProfileArn)}',${i})">测试</button>`
      : '-';
    html += `<tr><td>${badge}</td><td>${escapeHtml(r.region)}</td><td>${escapeHtml(r.model_label||r.model_id)}</td><td>${arnCell}</td><td id="testCell${i}">${actions}</td></tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
  window._results = results;
}

async function testArn(region, arn, idx) {
  const c = requireCreds();
  if (!c) return;
  const btn = $('testBtn'+idx), cell = $('testCell'+idx);
  if (btn) { btn.disabled = true; btn.textContent = '测试中'; }
  try {
    const d = await fetchJSON('/api/test_profile', {...c, region, inference_profile_arn:arn});
    if (d.ok && d.available) {
      if (cell) cell.innerHTML = '<span class="badge badge-ok">ACTIVE ✓</span>';
    } else {
      const msg = d.status || (d.error ? d.error.substring(0,20) : '不可用');
      if (cell) cell.innerHTML = `<span class="badge badge-warn">${escapeHtml(msg)}</span>`;
    }
  } catch (e) {
    if (cell) cell.innerHTML = '<span class="badge badge-err">错误</span>';
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    const t = document.createElement('div');
    t.textContent = '已复制 ARN';
    t.style.cssText = 'position:fixed;top:20px;right:20px;background:#22c55e;color:#fff;padding:8px 16px;border-radius:6px;font-size:13px;z-index:999;font-weight:600';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 1800);
  });
}'''

if old_fn in html:
    html = html.replace(old_fn, new_fn)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('OK: HTML patched with ARN display and test function')
else:
    print('ERROR: old function not found')
    print('Searching for partial match...')
    if 'function renderCreateResults(results)' in html:
        print('Function signature found but body different')
    else:
        print('Function not found at all')
