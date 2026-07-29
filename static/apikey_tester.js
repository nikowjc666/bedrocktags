/**
 * API Key 测试悬浮组件 v2
 * 嵌入方式：页面末尾 <script src="/static/apikey_tester.js"></script>
 * 区域 / 模型均从后端 API 动态加载，风格对齐页面 CSS 变量
 */
(function () {
  /* ── 样式 ─────────────────────────────────────────────── */
  var css = `
#_akt {
  position: fixed; bottom: 20px; right: 20px; width: 420px;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: var(--r, 7px);
  box-shadow: 0 4px 28px rgba(15,23,42,.14);
  z-index: 9999;
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 12px; color: var(--text, #0f172a);
  overflow: hidden; transition: box-shadow .2s;
}
#_akt:hover { box-shadow: 0 8px 36px rgba(15,23,42,.2); }

#_akt-hdr {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 13px;
  background: linear-gradient(135deg, var(--aws-dark, #232f3e) 0%, #1a365d 100%);
  cursor: pointer; user-select: none;
}
#_akt-hdr-l { display: flex; align-items: center; gap: 8px; }
#_akt-hdr-title { font-size: 12px; font-weight: 600; color: #fff; letter-spacing: 0; }
#_akt-status-badge {
  display: none; padding: 1px 7px; border-radius: 10px; font-size: 10px;
  font-weight: 500; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0;
}
#_akt-chevron { color: rgba(255,255,255,.55); font-size: 11px; transition: transform .2s; }
#_akt.collapsed #_akt-chevron { transform: rotate(180deg); }
#_akt.collapsed #_akt-body { display: none; }

#_akt-body {
  padding: 12px; display: flex; flex-direction: column; gap: 9px;
  max-height: 70vh; overflow-y: auto;
  scrollbar-width: thin; scrollbar-color: var(--border2, #cbd5e1) transparent;
}
#_akt-body::-webkit-scrollbar { width: 4px; }
#_akt-body::-webkit-scrollbar-thumb { background: var(--border2, #cbd5e1); border-radius: 2px; }

._akt-row { display: flex; gap: 8px; align-items: flex-end; }
._akt-fg { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
._akt-fg label {
  font-size: 10px; color: var(--t2, #64748b); font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
._akt-fg input, ._akt-fg select, ._akt-fg textarea {
  height: 28px; padding: 0 8px;
  border: 1px solid var(--border, #e2e8f0);
  border-radius: var(--r-sm, 5px);
  font-size: 11px; outline: none;
  background: var(--surface, #fff); color: var(--text, #0f172a);
  font-family: inherit;
  transition: border-color .15s, box-shadow .15s;
  width: 100%; box-sizing: border-box;
}
._akt-fg input:focus, ._akt-fg select:focus, ._akt-fg textarea:focus {
  border-color: var(--pr, #2563eb);
  box-shadow: 0 0 0 2px rgba(37,99,235,.1);
}
._akt-fg input.mono, ._akt-fg textarea.mono {
  font-family: "SF Mono", "Cascadia Code", Consolas, monospace; font-size: 10px;
}
._akt-fg textarea { height: auto; padding: 5px 8px; resize: none; line-height: 1.5; }

._akt-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  height: 30px; padding: 0 14px;
  background: linear-gradient(135deg, var(--pr, #2563eb) 0%, #3b82f6 100%);
  color: #fff; border: none; border-radius: var(--r-sm, 5px);
  font-size: 12px; font-weight: 500; cursor: pointer;
  box-shadow: 0 2px 8px rgba(37,99,235,.3);
  transition: all .15s; font-family: inherit; white-space: nowrap; flex-shrink: 0;
}
._akt-btn:hover { background: linear-gradient(135deg, var(--ph, #1d4ed8) 0%, var(--pr, #2563eb) 100%); }
._akt-btn:active { transform: scale(.97); }
._akt-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }

._akt-divider {
  height: 1px; background: var(--border, #e2e8f0); margin: 2px 0;
}

._akt-result {
  border-radius: var(--r-sm, 5px); font-size: 11px; line-height: 1.6;
  overflow: hidden;
}
._akt-result-ok {
  background: var(--ok-bg, #f0fdf4); border: 1px solid var(--ok-bd, #bbf7d0);
}
._akt-result-er {
  background: var(--er-bg, #fef2f2); border: 1px solid var(--er-bd, #fecaca);
  padding: 8px 10px; color: var(--er, #dc2626);
}
._akt-result-wa {
  background: var(--wa-bg, #fffbeb); border: 1px solid var(--wa-bd, #fde68a);
  padding: 8px 10px; color: var(--wa, #d97706);
}
._akt-result-meta {
  display: flex; gap: 10px; flex-wrap: wrap;
  padding: 7px 10px 5px; border-bottom: 1px solid var(--ok-bd, #bbf7d0);
}
._akt-result-meta span { font-size: 10px; color: var(--t2, #64748b); }
._akt-result-meta strong { color: var(--text, #0f172a); font-weight: 600; }
._akt-result-body { padding: 6px 10px 8px; }
._akt-result-lbl {
  font-size: 9px; color: var(--t3, #94a3b8);
  text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px;
}
._akt-resp {
  font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
  font-size: 11px; line-height: 1.65; white-space: pre-wrap; word-break: break-all;
  color: var(--text, #0f172a);
  max-height: 140px; overflow-y: auto;
  padding: 7px 9px;
  background: var(--surface, #fff); border: 1px solid var(--border, #e2e8f0);
  border-radius: 4px;
  scrollbar-width: thin;
}
._akt-sp {
  display: inline-block; width: 11px; height: 11px;
  border: 2px solid rgba(255,255,255,.3); border-top-color: #fff;
  border-radius: 50%; animation: _akt-spin .7s linear infinite;
}
@keyframes _akt-spin { to { transform: rotate(360deg); } }

._akt-model-select {
  height: 28px; font-size: 11px;
}
`;

  var styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  /* ── HTML ──────────────────────────────────────────────── */
  var html = `
<div id="_akt">
  <div id="_akt-hdr" onclick="_aktToggle()">
    <div id="_akt-hdr-l">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ff9900" stroke-width="2.2">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
      </svg>
      <span id="_akt-hdr-title">api key 测试</span>
      <span id="_akt-status-badge">✓ 成功</span>
    </div>
    <span id="_akt-chevron">▲</span>
  </div>

  <div id="_akt-body">

    <!-- API Key -->
    <div class="_akt-fg">
      <label>bedrock api key &nbsp;<span style="color:var(--t3);font-weight:400">baak_xxx</span></label>
      <input id="_akt-key" type="password" placeholder="baak_xxxxxxxxxxxxxxxxxxxx" class="mono" autocomplete="off">
    </div>

    <!-- 区域 + 模型 -->
    <div class="_akt-row">
      <div class="_akt-fg" style="flex:0 0 150px">
        <label>区域</label>
        <select id="_akt-region" class="_akt-model-select">
          <option value="">加载中...</option>
        </select>
      </div>
      <div class="_akt-fg">
        <label>model id / arn</label>
        <input id="_akt-model" type="text" class="mono"
          placeholder="arn:... 或 anthropic.claude-opus-5"
          oninput="_aktAutoRegion(this.value)">
      </div>
    </div>

    <!-- 快速选择模型 -->
    <div class="_akt-fg">
      <label>快速选择模型</label>
      <select id="_akt-model-quick" class="_akt-model-select" onchange="_aktPickModel(this.value)">
        <option value="">-- 从列表选择 --</option>
      </select>
    </div>

    <!-- Prompt -->
    <div class="_akt-fg">
      <label>prompt</label>
      <textarea id="_akt-prompt" class="mono" rows="2" placeholder="输入 prompt...">hi, reply in one sentence</textarea>
    </div>

    <div class="_akt-row" style="align-items:center">
      <button class="_akt-btn" id="_akt-btn" onclick="_aktSend()" style="flex:1">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        发送测试
      </button>
      <button onclick="_aktClear()" style="height:30px;padding:0 10px;border:1px solid var(--border,#e2e8f0);border-radius:var(--r-sm,5px);background:var(--surface,#fff);color:var(--t2,#64748b);font-size:11px;cursor:pointer;font-family:inherit;transition:all .15s" onmouseover="this.style.borderColor='var(--pr)';this.style.color='var(--pr)'" onmouseout="this.style.borderColor='var(--border,#e2e8f0)';this.style.color='var(--t2,#64748b)'">清空</button>
    </div>

    <div id="_akt-result" style="display:none"></div>

  </div>
</div>
`;

  var wrap = document.createElement('div');
  wrap.innerHTML = html;
  document.body.appendChild(wrap.firstElementChild);

  /* ── 数据加载 ─────────────────────────────────────────── */
  async function loadData() {
    // 加载区域
    try {
      var r = await fetch('/api/regions');
      var j = await r.json();
      if (j.ok && j.regions) {
        var sel = document.getElementById('_akt-region');
        sel.innerHTML = '';
        j.regions.forEach(function (reg) {
          var o = document.createElement('option');
          o.value = reg; o.textContent = reg;
          if (reg === 'us-east-1') o.selected = true;
          sel.appendChild(o);
        });
      }
    } catch (e) { }

    // 加载模型列表
    try {
      var r2 = await fetch('/api/claude_versions');
      var j2 = await r2.json();
      if (j2.ok && j2.versions) {
        var sel2 = document.getElementById('_akt-model-quick');
        sel2.innerHTML = '<option value="">-- 从列表选择 --</option>';
        // 分组：global / us / eu / 其他
        var groups = { 'global': [], 'us': [], 'eu': [], 'ap': [], 'other': [] };
        j2.versions.forEach(function (v) {
          var sources = v.sources || {};
          // global 优先，然后按地区
          ['global', 'us', 'eu'].forEach(function (geo) {
            if (sources[geo]) {
              groups[geo].push({ label: v.label + ' (' + geo + ')', id: sources[geo] });
            }
          });
          // 对于只有 global 的，不重复加
          if (!sources.global && !sources.us && !sources.eu) {
            groups.other.push({ label: v.label, id: v.id });
          }
        });

        var groupNames = { global: 'global 路由', us: 'us 区域', eu: 'eu 区域', other: '其他' };
        Object.keys(groups).forEach(function (g) {
          if (!groups[g].length) return;
          var og = document.createElement('optgroup');
          og.label = groupNames[g] || g;
          groups[g].forEach(function (item) {
            var o = document.createElement('option');
            o.value = item.id; o.textContent = item.label;
            og.appendChild(o);
          });
          sel2.appendChild(og);
        });
      }
    } catch (e) { }
  }

  /* ── 交互逻辑 ─────────────────────────────────────────── */
  window._aktToggle = function () {
    document.getElementById('_akt').classList.toggle('collapsed');
  };

  window._aktPickModel = function (val) {
    if (!val) return;
    document.getElementById('_akt-model').value = val;
    _aktAutoRegion(val);
  };

  window._aktAutoRegion = function (val) {
    // ARN 自动提取区域
    var m = (val || '').match(/^arn:aws:bedrock:([^:]+):/);
    if (!m) return;
    var region = m[1];
    var sel = document.getElementById('_akt-region');
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === region) { sel.value = region; return; }
    }
    // 没有这个选项就动态添加
    var opt = document.createElement('option');
    opt.value = region; opt.textContent = region; opt.selected = true;
    sel.appendChild(opt);
  };

  window._aktClear = function () {
    document.getElementById('_akt-model').value = '';
    document.getElementById('_akt-model-quick').value = '';
    document.getElementById('_akt-prompt').value = 'hi, reply in one sentence';
    document.getElementById('_akt-result').style.display = 'none';
    document.getElementById('_akt-status-badge').style.display = 'none';
  };

  window._aktSend = async function () {
    var key    = (document.getElementById('_akt-key').value || '').trim();
    var region = document.getElementById('_akt-region').value;
    var model  = (document.getElementById('_akt-model').value || '').trim();
    var prompt = (document.getElementById('_akt-prompt').value || 'hi').trim();
    var btn    = document.getElementById('_akt-btn');
    var res    = document.getElementById('_akt-result');
    var badge  = document.getElementById('_akt-status-badge');

    if (!key)    { _aktShowMsg('wa', '请填写 API Key'); return; }
    if (!model)  { _aktShowMsg('wa', '请填写 Model ID 或 ARN'); return; }
    if (!region) { _aktShowMsg('wa', '请选择区域'); return; }

    btn.disabled = true;
    btn.innerHTML = '<span class="_akt-sp"></span>&nbsp;调用中...';
    res.style.display = 'none';
    badge.style.display = 'none';

    try {
      var r = await fetch('/api/test_apikey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key, region: region, model_id: model, prompt: prompt })
      });
      var d = await r.json();

      if (d.ok && d.invoke_ok) {
        badge.style.display = 'inline-flex';
        res.className = '_akt-result _akt-result-ok';
        res.style.display = '';
        res.innerHTML =
          '<div class="_akt-result-meta">' +
            '<span>区域 <strong>' + _es(d.region) + '</strong></span>' +
            '<span>输入 <strong>' + (d.input_tokens || 0) + '</strong> tok</span>' +
            '<span>输出 <strong>' + (d.output_tokens || 0) + '</strong> tok</span>' +
          '</div>' +
          '<div class="_akt-result-body">' +
            '<div class="_akt-result-lbl">模型回复</div>' +
            '<div class="_akt-resp">' + _es(d.response || d.preview || '') + '</div>' +
          '</div>';
      } else {
        badge.style.display = 'none';
        _aktShowMsg('er', d.error || '调用失败');
      }
    } catch (e) {
      _aktShowMsg('er', '网络错误: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg> 发送测试';
    }
  };

  function _aktShowMsg(type, msg) {
    var res = document.getElementById('_akt-result');
    res.className = '_akt-result _akt-result-' + type;
    res.style.display = '';
    res.innerHTML = _es(msg);
  }

  function _es(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  // 如果页面有 testArn 输入框（test_profile.html），同步填入
  document.addEventListener('DOMContentLoaded', function () {
    loadData();
    var arnInput = document.getElementById('testArn');
    if (arnInput) {
      arnInput.addEventListener('change', function () {
        var v = arnInput.value.trim();
        if (v) {
          document.getElementById('_akt-model').value = v;
          _aktAutoRegion(v);
        }
      });
    }
  });

  // DOM 可能已经 ready
  if (document.readyState !== 'loading') {
    loadData();
  }

})();
