/**
 * BedrockPersist — 表单状态持久化
 *
 * 凭证（ak / sk / aid）和所有偏好设置：均用 sessionStorage
 *   - 刷新页面（F5）即清除所有内容
 *   - 关闭 tab 或重启浏览器即清除
 *   - 同一 session 内页面间跳转时保留
 */
var BedrockPersist = (function () {
  var CREDS_KEY   = "bedrock_creds";   // sessionStorage
  var PREFS_KEY   = "bedrock_prefs";   // sessionStorage

  /* ── 编解码 ──────────────────────────────────────────── */
  function enc(obj) {
    return btoa(unescape(encodeURIComponent(JSON.stringify(obj))));
  }
  function dec(s) {
    try { return JSON.parse(decodeURIComponent(escape(atob(s)))); }
    catch (e) { return null; }
  }

  /* ── 刷新时清除所有内容 ───────────────────────────────── */
  // performance API：type "reload" = F5/Ctrl+R，"navigate" = 正常导航
  (function clearAllOnReload() {
    try {
      var navType = 0;
      if (window.performance) {
        if (performance.getEntriesByType) {
          var nav = performance.getEntriesByType("navigation")[0];
          if (nav) navType = nav.type === "reload" ? 1 : 0;
        } else if (performance.navigation) {
          navType = performance.navigation.type;
        }
      }
      if (navType === 1) {
        sessionStorage.removeItem(CREDS_KEY);
        sessionStorage.removeItem(PREFS_KEY);
        sessionStorage.removeItem("bedrock_create_results");
      }
    } catch (e) {}
    // 清除旧版 localStorage 残留
    try {
      localStorage.removeItem("bedrock_prefs");
      localStorage.removeItem("bedrock_mgr");
      localStorage.removeItem("bedrock_mgr_c");
    } catch (e) {}
    // 清除旧版 cookie 残留
    try {
      document.cookie = "bedrock_mgr_c=;path=/;max-age=0";
      document.cookie = "bedrock_mgr=;path=/;max-age=0";
    } catch (e) {}
  })();

  function getCreds() {
    try {
      var raw = sessionStorage.getItem(CREDS_KEY);
      if (raw) { var d = dec(raw); if (d && typeof d === "object") return d; }
    } catch (e) {}
    return {};
  }
  function saveCreds(data) {
    try { sessionStorage.setItem(CREDS_KEY, enc(data)); } catch (e) {}
  }

  /* ── 偏好：也用 sessionStorage ───────────────────────── */
  function getPrefs() {
    try {
      var raw = sessionStorage.getItem(PREFS_KEY);
      if (raw) { var d = dec(raw); if (d && typeof d === "object") return d; }
    } catch (e) {}
    return {};
  }
  function savePrefs(data) {
    try { sessionStorage.setItem(PREFS_KEY, enc(data)); } catch (e) {}
  }

  /* ── 合并写入 ────────────────────────────────────────── */
  function mergeInto(target, src) {
    var out = {};
    var k;
    for (k in target) if (target.hasOwnProperty(k)) out[k] = target[k];
    for (k in src)    if (src.hasOwnProperty(k))    out[k] = src[k];
    return out;
  }

  /* ── DOM 工具 ────────────────────────────────────────── */
  function $(id)  { return document.getElementById(id); }
  function val(id){ var el=$(id); return el ? el.value.trim() : ""; }
  function text(id){ var el=$(id); return el ? (el.textContent||"").trim() : ""; }
  function checkedIn(sel) {
    var rs=[];
    document.querySelectorAll(sel+" input:checked").forEach(function(cb){ rs.push(cb.value); });
    return rs;
  }

  /* ── 收集 ────────────────────────────────────────────── */
  function collectCreds() {
    var d = {};
    var ak=val("ak"), sk=val("sk"), aid=text("aid");
    if (ak)  d.ak  = ak;
    if (sk)  d.sk  = sk;
    if (aid) d.aid = aid;
    return d;
  }
  function collectTags() {
    var tags=[];
    document.querySelectorAll("#tgg .tr").forEach(function(r){
      var k=r.querySelector(".tk"), v=r.querySelector(".tv");
      if (k && k.value.trim()) tags.push({ k:k.value.trim(), v:v?v.value.trim():"" });
    });
    return tags;
  }
  function collectPrefs() {
    var d = {};
    if ($("rgl"))        d.regions    = checkedIn("#rgl");
    if ($("mgl"))        d.models     = checkedIn("#mgl");
    if ($("pname"))      d.pname      = val("pname");
    if ($("pdesc"))      d.pdesc      = val("pdesc");
    if ($("manualArns")) d.manualArns = val("manualArns");
    if ($("testArn"))    d.testArn    = val("testArn");
    if ($("tgg"))        d.tags       = collectTags();
    return d;
  }

  /* ── 恢复 ────────────────────────────────────────────── */
  function restoreCreds(d) {
    if ($("ak")  && d.ak)  $("ak").value = d.ak;
    if ($("sk")  && d.sk)  $("sk").value = d.sk;
    if ($("aid") && d.aid) {
      $("aid").textContent = d.aid;
      if ($("ar")) $("ar").style.display = "flex";
    }
  }
  function restoreTags(tags) {
    if (!tags || !tags.length || !$("tgg")) return;
    var g = $("tgg");
    g.innerHTML = "";
    tags.forEach(function(t, i) {
      var r = document.createElement("div");
      r.className = "tr";
      if (i === 0) {
        r.innerHTML = '<input class="tk" placeholder="key"><input class="tv" placeholder="value"><button class="btn bsm" onclick="addTg()">+ 添加行</button>';
      } else {
        r.innerHTML = '<input class="tk" placeholder="key"><input class="tv" placeholder="value"><button class="btn bsm" onclick="addTg()">+</button><button class="rm" onclick="this.parentElement.remove();BedrockPersist.save()">✕</button>';
      }
      g.appendChild(r);
      r.querySelector(".tk").value = t.k || "";
      r.querySelector(".tv").value = t.v || "";
    });
  }
  function restoreChecks(sel, saved) {
    if (!saved || !saved.length) return;
    var setMap = {};
    saved.forEach(function(v){ setMap[v] = 1; });
    document.querySelectorAll(sel+" input").forEach(function(cb){ cb.checked = !!setMap[cb.value]; });
    if (typeof upRC      === "function") upRC();
    if (typeof upMC      === "function") upMC();
    if (typeof upPreview === "function") upPreview();
  }

  /* ── 公开 API ────────────────────────────────────────── */
  function save() {
    saveCreds(mergeInto(getCreds(), collectCreds()));
    savePrefs(mergeInto(getPrefs(), collectPrefs()));
  }

  function saveCredsOnly() {
    saveCreds(mergeInto(getCreds(), collectCreds()));
  }

  function load() {
    var c = getCreds();
    var p = getPrefs();
    restoreCreds(c);
    if ($("pname")      && p.pname)      $("pname").value      = p.pname;
    if ($("pdesc")      && p.pdesc)      $("pdesc").value      = p.pdesc;
    if ($("manualArns") && p.manualArns) $("manualArns").value = p.manualArns;
    if ($("testArn")    && p.testArn)    $("testArn").value    = p.testArn;
    restoreTags(p.tags);
    return p;   // 返回 prefs 供 afterListsReady 用
  }

  function bind() {
    ["ak","sk"].forEach(function(id){
      var el=$(id); if(!el) return;
      el.addEventListener("input",  saveCredsOnly);
      el.addEventListener("change", saveCredsOnly);
    });
    ["pname","pdesc","manualArns","testArn"].forEach(function(id){
      var el=$(id); if(!el) return;
      el.addEventListener("input",  save);
      el.addEventListener("change", save);
    });
    document.querySelectorAll(".nav a").forEach(function(a){
      a.addEventListener("click", function(){ saveCredsOnly(); save(); });
    });
    var tgg=$("tgg");
    if (tgg) tgg.addEventListener("input", save);
    window.addEventListener("beforeunload", function(){ saveCredsOnly(); save(); });
  }

  function afterListsReady(d) {
    if (d.regions) restoreChecks("#rgl", d.regions);
    if (d.models && $("mgl")) restoreChecks("#mgl", d.models);
  }

  function onVerified(accountId) {
    var c = mergeInto(getCreds(), collectCreds());
    c.aid = accountId;
    saveCreds(c);
  }

  function init() {
    var d = load();
    bind();
    return d;
  }

  return {
    init:            init,
    load:            load,
    save:            save,
    saveCreds:       saveCredsOnly,
    set:             function(data){ saveCreds(mergeInto(getCreds(), data)); savePrefs(mergeInto(getPrefs(), data)); },
    get:             function(){ return mergeInto(getCreds(), getPrefs()); },
    afterListsReady: afterListsReady,
    onVerified:      onVerified,
  };
})();
