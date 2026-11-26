(function () {
  "use strict";
  // Live numbers through the viewer's connectors (v4.13.0). The snapshot in the database stays the base: its numbers and
  // date are always shown. On top of it, when the page was published with connectors and the snapshot's meta binds a
  // role to a connector tool (meta.connectors[role] = {server, tool, input, pick}, written by `snapshot --connectors`),
  // this file asks that tool — with `watchTool`, the display arm of the `mcp` capability — for
  //   issue-status    a short status per code the maps already show, put beside each map row that carries the code;
  //   funnel-numbers  a live number per stage of the funnel chart already in the snapshot, put beside the snapshot's value.
  // Nothing is asked that the snapshot does not already show: only those codes, only those stage ids, no new queries.
  // One fetch when the data arrives (and again only when the codes change), one more per press of the button «Оновити»
  // (through busy) — no refetchInterval, no polling, no retry by itself. The shape of a tool's arguments and answer is the
  // tool's own, so it comes from the binding as data: `input` (with the placeholders {codes} and "{codes[]}" only) and
  // `pick` (three dot-paths into the answer). A connector's name is shown only as it comes from the binding, through
  // textContent. Fixed bytes, no data in it. Without `mcp`, without a binding or on any failure the page shows the
  // snapshot's own numbers with their date and the line «живі числа недоступні: <reason in words>». No console error.
  var S = window.__gpmShell;
  if (!S || !S.onDecorate) { return; }
  var el = S.el, isObj = S.isObj, str = S.str, num = S.num;

  S.addStrings({
    uk: {
      liveLine: "Живі числа",
      liveWord: "наживо",
      liveRefresh: "Оновити",
      liveOff: "живі числа недоступні: ",
      liveSnap: "цифри зі знімка від ",
      liveAsOf: "показано станом на ",
      reAbsent: "цей перегляд не підтримує конектори",
      reReauth: "%s: потрібно підключити знову (Налаштування → Конектори в claude.ai)",
      reNotConn: "%s: конектор не додано (Налаштування → Конектори в claude.ai)",
      reHost: "%s: локальний сервер недоступний у цьому вікні",
      reSelect: "%s: обери, який конектор використовувати",
      reNotAllowed: "%s: немає дозволу для цієї сторінки",
      rePolicy: "%s: політика організації не дозволяє цей запит",
      reApproval: "%s: потрібне схвалення запиту — натисни «Оновити»",
      reTool: "%s: конектор відповів помилкою",
      reUpstream: "%s: конектор зараз не відповідає",
      reOther: "%s: запит не вдався",
      reNoMatch: "%s: у відповіді немає потрібних чисел",
      reChanged: "обліковий запис змінився — онови сторінку"
    },
    en: {
      liveLine: "Live numbers",
      liveWord: "live",
      liveRefresh: "Refresh",
      liveOff: "live numbers are unavailable: ",
      liveSnap: "figures from the snapshot of ",
      liveAsOf: "shown as of ",
      reAbsent: "this view does not support connectors",
      reReauth: "%s: needs to be reconnected (Settings → Connectors in claude.ai)",
      reNotConn: "%s: the connector is not added (Settings → Connectors in claude.ai)",
      reHost: "%s: the local server is not available in this window",
      reSelect: "%s: choose which connector to use",
      reNotAllowed: "%s: this page is not allowed to use it",
      rePolicy: "%s: your organization's policy does not allow this request",
      reApproval: "%s: the request needs your approval — press «Refresh»",
      reTool: "%s: the connector answered with an error",
      reUpstream: "%s: the connector is not answering right now",
      reOther: "%s: the request failed",
      reNoMatch: "%s: the answer holds none of the numbers needed",
      reChanged: "the account changed — reload the page"
    }
  });

  var ROLES = ["issue-status", "funnel-numbers"];
  var CODE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
  var MAX_CODES = 200, MAX_ITEMS = 1000, MAX_ROWS = 20000, STATUS_MAX = 40, WAIT = 20000;
  var MAX_NODES = { code: 3000, stage: 400 };

  // Error codes of the platform (refs: mcp.d.ts) -> the reason's words; `deny` = an authorization denial (what was shown
  // is taken away); every other code is transient (the last good value stays, with its time). Unknown = upstream_error.
  var WHY = {
    needs_reauth: ["reReauth", true], server_not_connected: ["reNotConn", true], server_not_found: ["reNotConn", true],
    selection_required: ["reSelect", true], not_in_manifest: ["reNotAllowed", true], consent_required: ["reNotAllowed", true],
    blocked_by_policy: ["rePolicy", true], approval_required: ["reApproval", true], not_granted: ["reAbsent", true],
    capability_disabled: ["reAbsent", true], capability_removed: ["reAbsent", true], user_changed: ["reChanged", true],
    tool_error: ["reTool", false], server_unavailable: ["reUpstream", false], upstream_error: ["reUpstream", false],
    rate_limited: ["reUpstream", false], cancelled: ["reUpstream", false], bad_request: ["reOther", false],
    self_only: ["reOther", false], transform_error: ["reOther", false]
  };

  // ---- the nodes the renderers hand over (blocks.js, map.js) ------------------------------------------------------------
  var nodes = { code: [], stage: [] };
  var current = null;             // the part's state once it runs: {textFor(kind, key)}

  function put(node, kind, text) {
    var found = null;
    for (var i = 0; i < node.children.length; i++) {
      if (node.children[i].classList.contains("gpm-live")) { found = node.children[i]; break; }
    }
    if (!text) { if (found) { node.removeChild(found); } return; }
    if (!found) {
      found = el(kind === "stage" ? "span" : "div", "gpm-live");
      node.appendChild(found);
    }
    if (found.textContent !== text) { found.textContent = text; }
  }
  function decorateNode(rec) { try { put(rec.node, rec.kind, current ? current.textFor(rec.kind, rec.key) : ""); } catch (e) { /* nothing is added */ } }

  S.onDecorate(function (kind, node, key) {
    if (!nodes[kind] || !node || typeof key !== "string") { return; }
    var rec = { node: node, kind: kind, key: key };
    nodes[kind].push(rec);
    if (nodes[kind].length > MAX_NODES[kind]) { nodes[kind].shift(); }
    decorateNode(rec);
  });

  // ---- reading the snapshot: what is asked for ----------------------------------------------------------------------------
  function mapCodes(data, out, seen, depth) {
    if (!isObj(data) || depth > 3) { return; }
    (Array.isArray(data.rows) ? data.rows : []).forEach(function (r) {
      seen.rows++;
      if (seen.rows > MAX_ROWS || !isObj(r) || typeof r.code !== "string" || !CODE.test(r.code) || seen.set[r.code]) { return; }
      seen.set[r.code] = true;
      out.push(r.code);
    });
    if (isObj(data.tree) && Array.isArray(data.tree.children)) {
      data.tree.children.slice(0, 40).forEach(function (k) { mapCodes(k, out, seen, depth + 1); });
    }
    if (depth > 1 && Array.isArray(data.children)) {
      data.children.slice(0, 40).forEach(function (k) { mapCodes(k, out, seen, depth + 1); });
    }
  }

  function codesOf(snap) {
    var out = [], seen = { rows: 0, set: Object.create(null) };
    Object.keys(snap.sections).sort().forEach(function (id) {
      var sec = snap.sections[id];
      if (sec.section === "map" || sec.section.indexOf("map.") === 0) { mapCodes(sec.data, out, seen, 1); }
    });
    return out.slice(0, MAX_CODES);
  }

  function stagesOf(snap) {
    var out = [], set = Object.create(null);
    Object.keys(snap.sections).sort().forEach(function (id) {
      var sec = snap.sections[id];
      if (sec.section !== "funnel" || !Array.isArray(sec.data.stages)) { return; }
      sec.data.stages.forEach(function (s) {
        if (isObj(s) && str(s.id, 64) && !set[s.id]) { set[s.id] = true; out.push(s.id); }
      });
    });
    return out.slice(0, MAX_CODES);
  }

  // The arguments of the call: the binding's input with {codes} (inside a string) -> the codes joined with «, » and a
  // value that is exactly "{codes[]}" -> the array of codes. Nothing else is replaced.
  function fill(v, list) {
    if (typeof v === "string") {
      if (v === "{codes[]}") { return list.slice(); }
      return v.split("{codes}").join(list.join(", "));
    }
    if (Array.isArray(v)) { return v.map(function (x) { return fill(x, list); }); }
    if (isObj(v)) {
      var o = {};
      Object.keys(v).forEach(function (k) { o[k] = fill(v[k], list); });
      return o;
    }
    return v;
  }

  // A dot-path into foreign data: own properties of objects and indexes of arrays only; anything else is «missing».
  function get(v, path) {
    if (path === "") { return v; }
    var segs = path.split(".");
    for (var i = 0; i < segs.length; i++) {
      if (Array.isArray(v) && /^\d{1,6}$/.test(segs[i])) { v = v[Number(segs[i])]; }
      else if (isObj(v) && Object.prototype.hasOwnProperty.call(v, segs[i])) { v = v[segs[i]]; }
      else { return undefined; }
    }
    return v;
  }

  function hhmm(ms) {
    var d = new Date(ms);
    function two(n) { return (n < 10 ? "0" : "") + n; }
    return two(d.getHours()) + ":" + two(d.getMinutes());
  }

  // ---- the part -----------------------------------------------------------------------------------------------------------
  S.part("live", function (ctx) {
    var roles = {};               // role -> {role, binding, asked, key, seq, unsub, status, values, at, err, settle, timer}
    var mcpP = null, theMcp = null, absent = false, halted = false;
    var bar = null, linesBox = null, button = null;

    function t() { return S.t; }
    function getMcp() {
      if (!mcpP) {
        mcpP = Promise.resolve().then(function () {
          return window.claude && typeof window.claude.use === "function" ? window.claude.use("mcp") : null;
        }).then(function (m) { return m && typeof m.watchTool === "function" ? m : null; }).catch(function () { return null; });
      }
      return mcpP;
    }

    // what is to be asked now: role -> {binding, asked}
    function plan() {
      var snap = ctx.data, out = {};
      var meta = snap && snap.meta ? snap.meta : null;
      if (!meta || !isObj(meta.connectors)) { return out; }
      ROLES.forEach(function (role) {
        var b = meta.connectors[role];
        if (!isObj(b)) { return; }
        var asked = role === "issue-status" ? codesOf(snap) : stagesOf(snap);
        if (asked.length) { out[role] = { binding: b, asked: asked }; }
      });
      return out;
    }

    function stop(st) {
      st.seq++;
      if (st.unsub) { try { st.unsub(); } catch (e) { /* gone anyway */ } st.unsub = null; }
      settleWith(st, false);
    }

    function shown(st) { return st.values && (st.status === "ok" || (st.status === "err" && st.keep)) ? st.values : null; }

    // ---- the reasons --------------------------------------------------------------------------------------------------------
    function reasonOf(code, server) {
      var w = WHY[code] || WHY.upstream_error;
      var key = w[0];
      if (key === "reNotConn" && server.indexOf("host:") === 0) { key = "reHost"; }
      return { key: key, deny: w[1] };
    }

    // ---- the answers --------------------------------------------------------------------------------------------------------
    function readValues(st, res) {
      var out = Object.create(null), n = 0;
      var payload = isObj(res) ? (res.payload !== undefined ? res.payload : res.structuredContent) : undefined;
      var items = get(payload, st.binding.pick.items);
      if (!Array.isArray(items)) { return { values: out, n: 0 }; }
      var want = Object.create(null);
      st.asked.forEach(function (k) { want[k] = true; });
      items.slice(0, MAX_ITEMS).forEach(function (it) {
        var k = get(it, st.binding.pick.key), v = get(it, st.binding.pick.value);
        if (typeof k !== "string" || want[k] !== true) { return; }
        if (st.role === "issue-status") {
          if (typeof v !== "string" || !v.length || v.length > STATUS_MAX) { return; }
        } else if (num(v) === null) { return; }
        if (!(k in out)) { n++; }
        out[k] = v;
      });
      return { values: out, n: n };
    }

    function settleWith(st, ok) {
      if (st.settle) { var f = st.settle; st.settle = null; if (st.timer) { clearTimeout(st.timer); st.timer = null; } f(ok); }
    }

    function onEvent(st, seq, ev) {
      try {
        if (st.seq !== seq || !isObj(ev)) { return; }
        if (ev.type === "data" && isObj(ev.result)) {
          var read = readValues(st, ev.result);
          var cache = isObj(ev.result.cache) ? ev.result.cache : null;
          st.at = cache && num(cache.storedAt) !== null ? cache.storedAt : Date.now();
          st.values = read.values;
          st.keep = false;
          if (read.n) { st.status = "ok"; st.err = null; }
          else { st.status = "err"; st.err = { key: "reNoMatch", deny: false, nomatch: true }; }
          if (!(cache && cache.revalidating === true)) { settleWith(st, st.status === "ok"); }
        } else {
          var e = ev.type === "error" && isObj(ev.error) ? ev.error : {};
          var r = reasonOf(typeof e.code === "string" ? e.code : "", st.binding.server);
          st.err = { key: r.key, deny: r.deny, retryable: e.retryable === true, approval: e.code === "approval_required", changed: e.code === "user_changed" };
          if (r.deny) { st.values = null; st.keep = false; }
          else { st.keep = !!(st.values && Object.keys(st.values).length); }
          st.status = "err";
          if (st.err.changed) { halted = true; }
          settleWith(st, false);
        }
        paint();
      } catch (x) { /* a handler never throws into the page */ }
    }

    // (Re)watch one role: the previous watch is dropped, the arguments are built again from the binding. Resolves true
    // when the first answer carries live values, false otherwise (no answer within a time too).
    function start(st) {
      if (st.unsub) { try { st.unsub(); } catch (e) { /* gone anyway */ } st.unsub = null; }
      if (st.settle) { settleWith(st, false); }
      st.seq++;
      var seq = st.seq;
      var done = new Promise(function (resolve) { st.settle = resolve; });
      st.timer = setTimeout(function () { settleWith(st, false); }, WAIT);
      try {
        st.unsub = theMcp.watchTool(st.binding.server, st.binding.tool, fill(st.binding.input, st.asked), function (ev) { onEvent(st, seq, ev); });
      } catch (e) {
        onEvent(st, seq, { type: "error", error: { code: "bad_request", message: "" } });
      }
      return done;
    }

    // approval_required: the watch never asks; one callTool, from the press, does — its answer is shown as any other.
    function approve(st) {
      var seq = st.seq;
      return Promise.resolve().then(function () {
        return theMcp.callTool(st.binding.server, st.binding.tool, fill(st.binding.input, st.asked));
      }).then(function (res) {
        onEvent(st, seq, { type: "data", result: res });
        return st.status === "ok";
      }, function (e) {
        onEvent(st, seq, { type: "error", error: isObj(e) ? e : {} });
        return false;
      });
    }

    // ---- what is on screen --------------------------------------------------------------------------------------------------
    function snapDate() {
      var meta = ctx.data && ctx.data.meta;
      return meta ? S.showDate(meta.made, ctx.lang) : "";
    }

    function textFor(kind, key) {
      var st = roles[kind === "code" ? "issue-status" : "funnel-numbers"];
      var vals = st ? shown(st) : null;
      if (!vals || !(key in vals)) { return ""; }
      if (kind === "code") { return CODE.test(key) ? vals[key] : ""; }
      return t().liveWord + ": " + vals[key] + " · " + hhmm(st.at);
    }

    function refreshable(st) {
      return !halted && (st.status === "ok" || (st.status === "err" && st.err && (st.err.retryable || st.err.nomatch || st.err.approval)));
    }

    function buildBar() {
      bar = el("div", "gpm-live-bar");
      bar.hidden = true;
      linesBox = el("div", "gpm-live-lines");
      linesBox.setAttribute("role", "status");
      bar.appendChild(linesBox);
      button = el("button", "gpm-btn gpm-live-refresh", t().liveRefresh);
      button.type = "button";
      button.hidden = true;
      bar.appendChild(button);
      ctx.header.parentNode.insertBefore(bar, ctx.header.nextSibling);
      button.addEventListener("click", function () { S.busy(button, refresh()).then(paint); });
    }

    function lines() {
      var out = [];
      var date = snapDate();
      var tail = date ? " · " + t().liveSnap + date : "";
      if (absent) { return [t().liveOff + t().reAbsent + tail]; }
      var groups = [], byKey = {};
      Object.keys(roles).forEach(function (role) {
        var st = roles[role];
        if (st.status === "ok") {
          out.push(t().liveLine + ": " + st.binding.server + " · " + hhmm(st.at));
        } else if (st.status === "err" && st.err) {
          var g = byKey[st.err.key];
          if (!g) { g = byKey[st.err.key] = { key: st.err.key, servers: [], at: 0 }; groups.push(g); }
          g.servers.push(st.binding.server);
          if (shown(st) && !g.at) { g.at = st.at; }
        }
      });
      groups.forEach(function (g) {
        var words = t()[g.key].split("%s").join(g.servers.join(", "));
        out.push(t().liveOff + words + (g.at ? " · " + t().liveAsOf + hhmm(g.at) : "") + tail);
      });
      return out;
    }

    function paint() {
      try {
        var want = Object.keys(roles).length > 0 || absent;
        if (want && !bar) { buildBar(); }
        if (bar) {
          var texts = lines();
          var seen = {};
          texts = texts.filter(function (x) { if (seen[x]) { return false; } seen[x] = true; return true; });
          while (linesBox.firstChild) { linesBox.removeChild(linesBox.firstChild); }
          texts.forEach(function (x) { linesBox.appendChild(el("p", "gpm-live-line", x)); });
          if (!button.disabled) {
            button.hidden = !Object.keys(roles).some(function (r) { return refreshable(roles[r]); });
          }
          bar.hidden = !texts.length && button.hidden;
        }
        nodes.code.forEach(decorateNode);
        nodes.stage.forEach(decorateNode);
      } catch (e) { /* the page stays as it was */ }
    }

    // The press: every role that may be asked again is asked once — a role that failed for good is left alone.
    function refresh() {
      var waits = [], last = "";
      Object.keys(roles).forEach(function (role) {
        var st = roles[role];
        if (!refreshable(st)) { return; }
        waits.push(st.status === "err" && st.err.approval ? approve(st) : start(st));
      });
      if (!waits.length) { return Promise.resolve(); }
      return Promise.all(waits).then(function (res) {
        if (res.some(function (ok) { return ok; })) { return; }
        var ls = lines();
        last = ls.length ? ls[0] : t().liveOff + t().reAbsent;
        throw S.refusal(last);
      });
    }

    // ---- the flow -----------------------------------------------------------------------------------------------------------
    function apply(mcp) {
      var want = plan();
      Object.keys(roles).forEach(function (role) {
        if (!want[role]) { stop(roles[role]); delete roles[role]; }
      });
      if (!Object.keys(want).length) { absent = false; paint(); return; }
      if (!mcp) { absent = true; paint(); return; }
      absent = false;
      theMcp = mcp;
      Object.keys(want).forEach(function (role) {
        var key = JSON.stringify([want[role].binding, want[role].asked]);
        var st = roles[role];
        if (st && st.key === key) { return; }
        if (st) { stop(st); }
        st = roles[role] = { role: role, binding: want[role].binding, asked: want[role].asked, key: key, seq: 0, unsub: null, status: "pending", values: null, at: 0, err: null, keep: false, settle: null, timer: null };
        start(st);
      });
      paint();
    }

    function sync() {
      try {
        if (halted) { return; }
        if (!Object.keys(plan()).length) { apply(null); return; }
        getMcp().then(function (m) { if (!halted) { apply(m); } }).catch(function () { /* the page stays as it was */ });
      } catch (e) { /* the page stays as it was */ }
    }

    current = { textFor: textFor };
    ctx.onData(sync);
    sync();
  });
})();
