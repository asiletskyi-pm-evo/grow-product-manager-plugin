(function () {
  "use strict";
  // The journey map inside the app (v4.13.0): the block `map` draws each map section — the data of
  // `journey_map.py app-data` — with the same markup and the same attributes the map's own page has (journey-protocol §9
  // «What the page reads»), so the page's editing script EDIT runs here unchanged: wrap keeps its fixed text in
  // #gpm-edit-src and the edit bar in #gpm-edit-bar, and this file runs it once, after the maps are in the page. Edits go
  // to the artifact's collection `edits` exactly as on the map's page. Several maps: a picker, one map at a time.
  // Fixed bytes, no data in it. The section data is foreign input: every text through textContent or setAttribute, a
  // number only when finite, a shape that does not fit is no map.
  var S = window.__gpmShell;
  if (!S || !S.blocks) { return; }
  var el = S.el, isObj = S.isObj, str = S.str, num = S.num;

  S.addStrings({
    uk: {
      mapPick: "Карти",
      mapStale: "Редагування цієї карти вимкнене: у спільних правках є %d зроблених на іншій версії карти. Спершу PM забирає або прибирає їх (крок J9).",
      mapNewer: "Карту оновлено. Онови сторінку, щоб бачити й редагувати нову версію.",
      mapReload: "Оновити сторінку",
      mapTwin: "Ця карта має ту саму назву, що й інша карта застосунку: редагуй її на її власній сторінці.",
      mapOwnPage: "Редагування карт — на їхніх сторінках: ця сторінка вже має редагування карти."
    },
    en: {
      mapPick: "Maps",
      mapStale: "Editing this map is off: the shared edits hold %d made on another version of the map. The PM takes or clears them first (step J9).",
      mapNewer: "The map was updated. Reload the page to see and edit the new version.",
      mapReload: "Reload the page",
      mapTwin: "This map has the same name as another map of the app: edit it on its own page.",
      mapOwnPage: "Maps are edited on their own pages: this page already has a map's editing."
    }
  });

  var SVG_NS = "http://www.w3.org/2000/svg";
  var LANES = ["action", "touchpoint", "experience", "pain", "metric", "anomaly", "opportunity", "solution", "initiative", "experiment"];
  var SIG = /^[0-9a-f]{16}$/;
  var MAX_STAGES = 40, MAX_ROWS = 3000, MAX_KIDS = 40, MAX_REFS = 40, MAX_POINTS = 200, MAX_DEPTH = 3, TEXT_MAX = 4000;
  var FLAG = "🎯 ";          // 🎯 — the stage's target, as the page writes it

  // ---- foreign input ----------------------------------------------------------------------------------------------
  function txt(v) { return typeof v === "string" ? (v.length > TEXT_MAX ? v.slice(0, TEXT_MAX) : v) : ""; }
  function list(v, max) { return Array.isArray(v) ? v.slice(0, max) : []; }

  function cleanGrid(g) {
    if (!isObj(g) || !str(g.map, 200) || typeof g.table_sig !== "string" || !SIG.test(g.table_sig)) { return null; }
    if (!Array.isArray(g.stages) || !g.stages.length || g.stages.length > MAX_STAGES) { return null; }
    var stages = [], ids = {};
    for (var i = 0; i < g.stages.length; i++) {
      var s = g.stages[i];
      if (!isObj(s) || !str(s.id, 200) || !Array.isArray(s.cells) || s.cells.length !== LANES.length) { return null; }
      ids[s.id] = true;
      stages.push({ id: s.id, title: txt(s.title), outcome: txt(s.outcome), gap: s.gap === true, cells: s.cells.map(txt) });
    }
    var rows = list(g.rows, MAX_ROWS).filter(function (r) {
      return isObj(r) && str(r.id, 200) && typeof r.stage === "string" && ids[r.stage] === true && LANES.indexOf(r.lane) >= 0;
    }).map(function (r) {
      return { id: r.id, stage: r.stage, lane: r.lane, text: txt(r.text), parent: txt(r.parent), code: txt(r.code),
        target: r.target === true && r.lane === "opportunity", locked: r.locked === true, meta: txt(r.meta) };
    });
    return { map: g.map, product: txt(g.product), sig: g.table_sig, stages: stages, rows: rows, notShown: txt(g.not_shown_text) };
  }

  function cleanTree(n, depth) {
    var out = { children: [], deeper: [], deeperText: "" };
    if (!isObj(n)) { return out; }
    if (depth < MAX_DEPTH) {
      list(n.children, MAX_KIDS).forEach(function (k) {
        var g = cleanGrid(k);
        if (!g || !isObj(k.chip)) { return; }
        var sub = cleanTree(k, depth + 1);
        g.stage = txt(k.stage); g.chipT = txt(k.chip.t); g.chipM = txt(k.chip.m); g.summary = txt(k.summary);
        g.summaryM = txt(k.summary_m); g.meta = txt(k.meta); g.children = sub.children; g.deeper = sub.deeper; g.deeperText = sub.deeperText;
        out.children.push(g);
      });
    }
    out.deeper = list(n.deeper, MAX_REFS).filter(isObj).map(function (x) { return { stage: txt(x.stage), t: txt(x.t), m: txt(x.m) }; });
    out.deeperText = txt(n.deeper_text);
    return out;
  }

  function cleanMap(d) {
    if (!isObj(d) || d.v !== 1 || !Array.isArray(d.lanes) || d.lanes.length !== LANES.length) { return null; }
    for (var i = 0; i < LANES.length; i++) {
      if (!isObj(d.lanes[i]) || d.lanes[i].id !== LANES[i]) { return null; }
    }
    var g = cleanGrid(d);
    if (!g) { return null; }
    var tx = isObj(d.texts) ? d.texts : {};
    g.lanes = d.lanes.map(function (l) { return txt(l.title); });
    g.journey = txt(d.journey) || g.map;
    g.texts = {};
    ["title", "meta", "above", "health", "no_trend", "gap", "children"].forEach(function (k) { g.texts[k] = txt(tx[k]); });
    var h = isObj(d.health) ? d.health : {};
    g.points = list(h.points, MAX_POINTS).filter(function (p) { return isObj(p) && str(p.date, 40) && num(p.score) !== null; })
      .map(function (p) { return { date: p.date, score: p.score, snapshot: txt(p.snapshot) }; });
    var t = cleanTree(d.tree, 1);
    g.children = t.children; g.deeper = t.deeper; g.deeperText = t.deeperText;
    return g;
  }

  // ---- drawing: the page's markup (journey_map.py render_html / _grid / _tree_parts) -------------------------------
  function svg(tag, attrs) {
    var n = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }

  function sparkline(points) {
    var w = 260, h = 56, pad = 6, n = points.length;
    var box = svg("svg", { "class": "spark", width: String(w), height: String(h), viewBox: "0 0 " + w + " " + h, role: "img" });
    var xy = points.map(function (p, i) {
      var x = pad + (w - 2 * pad) * (n > 1 ? i / (n - 1) : 0.5);
      var y = h - pad - (h - 2 * pad) * Math.max(0, Math.min(100, p.score)) / 100;
      return [x, y];
    });
    box.appendChild(svg("polyline", { fill: "none", "stroke-width": "2", points: xy.map(function (c) { return c[0].toFixed(1) + "," + c[1].toFixed(1); }).join(" ") }));
    xy.forEach(function (c, i) {
      var dot = svg("circle", { cx: c[0].toFixed(1), cy: c[1].toFixed(1), r: "3" });
      var tt = svg("title", {});
      tt.textContent = points[i].date + ": " + points[i].score;
      dot.appendChild(tt);
      box.appendChild(dot);
    });
    return box;
  }

  function item(cls, t, m) {
    var d = el("div", "item " + cls);
    d.appendChild(el("div", "t", t));
    d.appendChild(el("div", "m", m));
    return d;
  }

  // One grid: the frame with the map's name and digest, a cell per stage and lane with its stage, lane and title, a card
  // per row with its id, lane, parent, code, target and lock — the attributes EDIT reads. `chips` = {stage id: [node]}.
  // `plain` draws the same map without those attributes (a twin of another map's name): nothing of it is edited.
  function grid(g, m, chips, plain) {
    var frag = document.createDocumentFragment();
    if (g.notShown) { frag.appendChild(el("p", "meta", g.notShown)); }
    var wrap = el("div", "wrap");
    wrap.setAttribute("tabindex", "0");
    if (!plain) { wrap.setAttribute("data-map", g.map); wrap.setAttribute("data-digest", g.sig); }
    var table = el("table", "grid");
    var thead = el("thead"), hr = el("tr");
    hr.appendChild(el("th", "corner"));
    g.stages.forEach(function (s) {
      var th = el("th", "stage");
      th.appendChild(document.createTextNode(s.id + " · " + s.title));
      th.appendChild(el("div", "o", s.outcome));
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = el("tbody");
    LANES.forEach(function (lane, li) {
      var tr = el("tr");
      tr.appendChild(el("th", "lane", m.lanes[li]));
      g.stages.forEach(function (s) {
        var td = el("td");
        if (!plain) { td.setAttribute("data-stage", s.id); td.setAttribute("data-lane", lane); td.setAttribute("data-title", s.cells[li]); }
        if (li === 0 && s.gap) { td.appendChild(el("div", "item gap", m.texts.gap)); }
        if (li === 0) { (chips[s.id] || []).forEach(function (c) { td.appendChild(c); }); }
        g.rows.forEach(function (r) {
          if (r.stage !== s.id || r.lane !== lane) { return; }
          var it = item("l-" + lane + (r.target ? " target" : ""), (r.target ? FLAG : "") + r.text, r.meta);
          if (!plain) {
            it.setAttribute("data-row", r.id);
            it.setAttribute("data-lane", lane);
            if (r.parent) { it.setAttribute("data-parent", r.parent); }
            if (r.code) { it.setAttribute("data-code", r.code); }
            if (r.target) { it.setAttribute("data-target", "1"); }
            if (r.locked) { it.setAttribute("data-locked", "1"); }
          }
          if (r.code && S.decorate) { S.decorate("code", it, r.code); }
          td.appendChild(it);
        });
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    frag.appendChild(wrap);
    return { node: frag, wrap: wrap };
  }

  // The children of a node as the tree page shows them: a chip on the parent's step, each child's grid in a <details>,
  // its own children inside it, the references past the depth as chips and one line.
  function tree(n, m, ids, wraps, plain) {
    var chips = {}, body = [];
    n.children.forEach(function (k) {
      var id = ids();
      var chip = item("chip", k.chipT, k.chipM);
      chip.setAttribute("data-open", id);
      chip.setAttribute("role", "button");
      chip.setAttribute("tabindex", "0");
      (chips[k.stage] = chips[k.stage] || []).push(chip);
      var sub = tree(k, m, ids, wraps, plain);
      var det = el("details", "child");
      det.id = id;
      var sum = el("summary");
      sum.appendChild(document.createTextNode(k.summary));
      sum.appendChild(el("span", "m", k.summaryM));
      det.appendChild(sum);
      det.appendChild(el("p", "meta", k.meta));
      var g = grid(k, m, sub.chips, plain);
      wraps.push(g.wrap);
      det.appendChild(g.node);
      sub.body.forEach(function (b) { det.appendChild(b); });
      body.push(det);
    });
    n.deeper.forEach(function (x) { (chips[x.stage] = chips[x.stage] || []).push(item("ref", x.t, x.m)); });
    if (n.deeperText) { body.push(el("p", "meta", n.deeperText)); }
    return { chips: chips, body: body };
  }

  // The grid pans with the mouse held down, and a chip (or Enter on it) opens its child's map — as the page's own
  // script does; `_moved` tells EDIT a pan was no click.
  function pan(w) {
    var p = null;
    w.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) { return; }
      w._moved = false;
      p = { x: e.clientX, y: e.clientY, l: w.scrollLeft, t: w.scrollTop, i: e.pointerId, m: false };
    });
    w.addEventListener("pointermove", function (e) {
      if (!p) { return; }
      var dx = e.clientX - p.x, dy = e.clientY - p.y;
      if (!p.m && Math.abs(dx) + Math.abs(dy) < 4) { return; }
      if (!p.m) { p.m = true; try { w.setPointerCapture(p.i); } catch (x) { /* fine */ } w.classList.add("panning"); }
      w.scrollLeft = p.l - dx;
      w.scrollTop = p.t - dy;
    });
    function end() {
      if (!p) { return; }
      if (p.m) { w._moved = true; try { w.releasePointerCapture(p.i); } catch (x) { /* fine */ } }
      p = null;
      w.classList.remove("panning");
    }
    w.addEventListener("pointerup", end);
    w.addEventListener("pointercancel", end);
  }

  function opener(chip) {
    function go() {
      var w = chip.closest(".wrap");
      if (w && w._moved) { w._moved = false; return; }
      var d = document.getElementById(chip.getAttribute("data-open"));
      if (!d) { return; }
      for (var x = d; x; x = x.parentElement) { if (x.tagName === "DETAILS") { x.open = true; } }
      try { d.scrollIntoView({ block: "start" }); } catch (e) { /* fine */ }
    }
    chip.addEventListener("click", go);
    chip.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  }

  // renderMap(el, data, opts) — one map into `el`: its title, its note, the maps above it, its health, its grid and its
  // child maps. `data` is an app-data object, cleaned here; opts = {prefix, plain}. -> {wraps} or null when it is no map.
  function renderMap(box, data, opts) {
    var m = cleanMap(data);
    return m ? draw(box, m, opts || {}) : null;
  }

  function draw(box, m, opts) {
    var n = 0, prefix = opts.prefix || "gpm-map";
    var ids = function () { n += 1; return prefix + "-n" + n; };
    var wraps = [];
    box.appendChild(el("h2", "gpm-map-title", m.texts.title));
    box.appendChild(el("p", "meta", m.texts.meta));
    if (m.texts.above) { box.appendChild(el("p", "meta", m.texts.above)); }
    box.appendChild(el("h3", null, m.texts.health));
    if (m.points.length) {
      box.appendChild(sparkline(m.points));
      var pts = el("table", "pts");
      [function (p) { return el("td", null, p.date); }, function (p) { return el("td", null, String(p.score)); },
        function (p) { return el("td", "m", p.snapshot); }].forEach(function (cell) {
        var tr = el("tr");
        m.points.forEach(function (p) { tr.appendChild(cell(p)); });
        pts.appendChild(tr);
      });
      box.appendChild(pts);
    } else {
      box.appendChild(el("p", "meta", m.texts.no_trend));
    }
    var sub = tree(m, m, ids, wraps, !!opts.plain);
    var g = grid(m, m, sub.chips, !!opts.plain);
    wraps.unshift(g.wrap);
    box.appendChild(g.node);
    if (sub.body.length) {
      box.appendChild(el("h3", null, m.texts.children));
      sub.body.forEach(function (b) { box.appendChild(b); });
    }
    wraps.forEach(pan);
    Array.prototype.forEach.call(box.querySelectorAll(".item.chip[data-open]"), opener);
    return { wraps: wraps };
  }
  S.renderMap = renderMap;

  // ---- the block: every map of the snapshot at once, one shown -----------------------------------------------------
  var ctx = null;
  S.part("map", function (c) { ctx = c; watchEdits(); });

  var state = { key: null, root: null, maps: [], started: false, frozen: false, selected: null, stale: {} };

  function isMapSection(name) { return name === "map" || (typeof name === "string" && name.indexOf("map.") === 0); }

  // the map sections of the snapshot, in the order of meta.products, then by id: [{id, product, made, data}]
  function entriesOf(snap, fallback) {
    var out = [];
    if (snap && isObj(snap.sections)) {
      Object.keys(snap.sections).sort().forEach(function (id) {
        var s = snap.sections[id];
        if (s && isMapSection(s.section)) { out.push({ id: id, product: s.product, made: s.made, raw: s.data }); }
      });
    } else {
      fallback.forEach(function (x) { out.push({ id: x.info.id, product: x.info.product, made: x.info.made, raw: x.data }); });
    }
    var order = snap && snap.meta && Array.isArray(snap.meta.products) ? snap.meta.products.map(function (p) { return p.id; }) : [];
    function pos(e) { var i = order.indexOf(e.product); return i < 0 ? order.length : i; }
    return out.sort(function (a, b) { return pos(a) - pos(b) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); });
  }

  function keyOf(entries) {
    return S.lang + "|" + entries.map(function (e) {
      return e.id + "|" + e.made + "|" + (isObj(e.raw) && typeof e.raw.table_sig === "string" ? e.raw.table_sig : "");
    }).join(";");
  }

  function note(text, cls) {
    var p = el("p", "gpm-map-note" + (cls ? " " + cls : ""), text);
    p.setAttribute("role", "status");
    return p;
  }

  // A map's editing off (or on again): every card locked as a health-check row is, no «+», and a line why.
  function lock(w, on, why) {
    if (!!w.__gpmLocked === on && (!on || w.__gpmWhy === why)) { return; }
    w.__gpmWhy = why;
    if (w.__gpmNote && w.__gpmNote.parentNode) { w.__gpmNote.parentNode.removeChild(w.__gpmNote); }
    w.__gpmNote = null;
    if (on && why) { w.__gpmNote = note(why); w.parentNode.insertBefore(w.__gpmNote, w); }
    if (!!w.__gpmLocked === on) { return; }
    w.__gpmLocked = on;
    w.classList.toggle("gpm-map-locked", on);
    Array.prototype.forEach.call(w.querySelectorAll(".item[data-row]"), function (it) {
      if (on) { it.__gpmLock = it.getAttribute("data-locked"); it.setAttribute("data-locked", "1"); }
      else if (it.__gpmLock === null || it.__gpmLock === undefined) { it.removeAttribute("data-locked"); }
      else { it.setAttribute("data-locked", it.__gpmLock); }
    });
  }

  function editingOff() {
    var tog = state.root && state.root.querySelector(".edit-bar .edit-toggle");
    if (tog && document.body.classList.contains("editing")) { tog.click(); }
  }

  function applyStale() {
    if (!state.root || state.frozen) { return; }
    state.maps.forEach(function (mp) {
      mp.wraps.forEach(function (w) {
        var name = w.getAttribute("data-map"), dig = w.getAttribute("data-digest");
        var n = name && state.stale[name] ? state.stale[name].filter(function (x) { return x !== dig; }).length : 0;
        lock(w, n > 0, n > 0 ? S.t.mapStale.replace("%d", String(n)) : "");
      });
    });
  }

  // The shared edits of each map name, by the digest they were made on: a map whose edits were made on another version
  // of it is not edited here until the PM has taken or cleared them.
  function watchEdits() {
    if (!ctx) { return; }
    ctx.watchEdits(function (list) {
      var by = {};
      list.forEach(function (d) {
        var x = d.x;
        if (typeof x.map !== "string" || typeof x.digest !== "string" || (x.kind !== "row" && x.kind !== "add")) { return; }
        (by[x.map] = by[x.map] || []).push(x.digest);
      });
      state.stale = by;
      applyStale();
    });
  }

  // A newer snapshot while EDIT already runs on the maps drawn: EDIT is not run twice on one page, so the old maps stay,
  // locked, with a line and a button to reload the page.
  function freeze() {
    if (state.frozen) { return; }
    state.frozen = true;
    editingOff();
    state.maps.forEach(function (mp) { mp.wraps.forEach(function (w) { lock(w, true, ""); }); });
    var line = el("div", "gpm-map-newer");
    line.appendChild(note(S.t.mapNewer));
    var b = el("button", "gpm-map-reload", S.t.mapReload);
    b.type = "button";
    b.addEventListener("click", function () {
      S.busy(b, new Promise(function () { window.location.reload(); }));
    });
    line.firstChild.appendChild(document.createTextNode(" "));
    line.firstChild.appendChild(b);
    state.root.insertBefore(line, state.root.firstChild);
  }

  function build(entries, view) {
    var root = el("div", "gpm-maps");
    var tpl = document.getElementById("gpm-edit-bar");
    if (tpl && tpl.content) { root.appendChild(document.importNode(tpl.content, true)); }
    var pick = el("div", "gpm-map-pick");
    pick.setAttribute("role", "group");
    pick.setAttribute("aria-label", S.t.mapPick);
    root.appendChild(pick);
    var names = {}, maps = [];
    entries.forEach(function (e, i) {
      var data = cleanMap(e.raw);
      if (!data) { return; }
      var box = el("div", "gpm-map");
      box.setAttribute("data-map", data.map);
      box.setAttribute("data-section", e.id);
      var twin = Object.prototype.hasOwnProperty.call(names, data.map);
      names[data.map] = true;
      if (twin) { box.appendChild(note(S.t.mapTwin)); }
      var r = draw(box, data, { prefix: "gpm-map-" + i, plain: twin });
      var b = el("button", null, null);
      b.type = "button";
      b.appendChild(document.createTextNode(data.journey));
      if (e.product) { b.appendChild(document.createTextNode(" ")); b.appendChild(view.chip(e.product)); }
      var mp = { id: e.id, box: box, button: b, wraps: r.wraps, product: data.product };
      b.addEventListener("click", function () { state.selected = mp.id; show(); });
      pick.appendChild(b);
      root.appendChild(box);
      maps.push(mp);
    });
    if (!maps.length) { return null; }
    var bar = root.querySelector(".edit-bar");
    if (bar && maps[0].product) { bar.setAttribute("data-product", maps[0].product); }
    if (bar) { bar.setAttribute("data-root", maps[0].box.getAttribute("data-map")); }
    state.root = root;
    state.maps = maps;
    return root;
  }

  var visible = [];
  function show() {
    var shown = state.maps.filter(function (mp) { return visible.indexOf(mp.id) >= 0; });
    if (!shown.some(function (mp) { return mp.id === state.selected; })) { state.selected = shown.length ? shown[0].id : null; }
    state.maps.forEach(function (mp) {
      var on = mp.id === state.selected;
      mp.box.hidden = !on;
      mp.button.hidden = shown.indexOf(mp) < 0;
      mp.button.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var pick = state.root.querySelector(".gpm-map-pick");
    if (pick) { pick.hidden = shown.length < 2; }
  }

  // EDIT once per page, after the maps are in it — never next to another page's editing.
  function startEdit() {
    if (state.started || !state.root || state.frozen || !document.body.contains(state.root)) { return; }
    state.started = true;
    var bar = state.root.querySelector(".edit-bar");
    var src = document.getElementById("gpm-edit-src");
    if (!bar) { return; }
    var others = Array.prototype.filter.call(document.querySelectorAll(".edit-bar"), function (b) { return b !== bar; });
    if (!src || others.length) {
      bar.parentNode.removeChild(bar);
      if (others.length) { state.root.insertBefore(note(S.t.mapOwnPage), state.root.firstChild); }
      return;
    }
    var s = document.createElement("script");
    s.textContent = src.textContent;
    document.body.appendChild(s);
    applyStale();
  }

  function all(docs, view) {
    var entries = entriesOf(ctx ? ctx.data : null, docs);
    var key = keyOf(entries);
    if (state.root && key !== state.key) {
      if (state.started) { freeze(); } else { state.root = null; state.maps = []; }
    }
    if (!state.root) {
      if (!build(entries, view)) { return null; }
      state.key = key;
    }
    var ids = docs.map(function (x) { return x.info.id; });
    visible = state.maps.filter(function (mp) { return ids.indexOf(mp.id) >= 0; }).map(function (mp) { return mp.id; });
    if (!visible.length) { return null; }
    show();
    applyStale();
    setTimeout(startEdit, 0);
    return state.root;
  }

  // The block map: one document drawn alone, or — as blocks.js calls it — all the documents of the block at once.
  function map(data, view, info) { return all([{ data: data, info: info }], view); }
  map.all = all;
  S.blocks.map = map;
  // Shows one map of the block by its section id (the tray's click); false when it is not drawn or not shown now.
  S.selectMap = function (id) {
    if (!state.root || !state.maps.some(function (mp) { return mp.id === id && visible.indexOf(id) >= 0; })) { return false; }
    state.selected = id;
    show();
    return true;
  };
})();
