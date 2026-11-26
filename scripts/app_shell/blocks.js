(function () {
  "use strict";
  // The modules of the app: tabs built from the profile's modules (and the owner's config/app), each made of ready data
  // blocks — table, list, number, chart, feed (map arrives in map.js) — fed by the sections of the database snapshot.
  // Fixed bytes, no data in it. Everything read from the database or the config is foreign input: a value goes into the
  // page only through textContent, a colour only as #rrggbb, a number only when finite; nothing becomes HTML, CSS, script
  // or a link. Registered in the registry that shell.js exposes; if that is absent this file does nothing.
  var S = window.__gpmShell;
  if (!S) { return; }
  var el = S.el, isObj = S.isObj, str = S.str, num = S.num;

  S.addStrings({
    uk: {
      all: "Усі",
      product: "Продукт",
      noProduct: "Без продукту",
      modules: "Модулі",
      empty: "Ще немає даних — Claude додасть їх після наступного прогону",
      unsupported: "блок не підтримується",
      noModules: "Жодного модуля не увімкнено",
      editsPlaceholder: "Правки команди з'являться тут",
      mapPlaceholder: "Карта з'явиться тут",
      status: "Стан",
      attentionOk: "Усе гаразд",
      attentionWarn: "Увага",
      attentionCrit: "Критично",
      baseline: "база",
      weakest: "Найслабше",
      trend: "Тренд"
    },
    en: {
      all: "All",
      product: "Product",
      noProduct: "No product",
      modules: "Modules",
      empty: "No data yet — Claude will add it after the next run",
      unsupported: "this block is not supported",
      noModules: "No module is turned on",
      editsPlaceholder: "Team edits will appear here",
      mapPlaceholder: "The map will appear here",
      status: "Status",
      attentionOk: "OK",
      attentionWarn: "Warning",
      attentionCrit: "Critical",
      baseline: "baseline",
      weakest: "Weakest",
      trend: "Trend"
    }
  });

  var SVG_NS = "http://www.w3.org/2000/svg";
  var BLOCK_NAMES = ["table", "list", "number", "chart", "feed", "map"];    // the same as BLOCKS in app_shell.py
  var SECTION = /^[a-z0-9][a-z0-9.-]{0,63}$/;
  var MODULE_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
  var TITLE_MAX = 80, MAX_BLOCKS = 8, MAX_CUSTOM = 20, MAX_RULES = 64;      // the same limits as app_shell.py's check_config
  var MAX_COLS = 12, MAX_ROWS = 500, MAX_ITEMS = 200, MAX_STAGES = 30, MAX_TREND = 60, TEXT_MAX = 500;
  var STORE_TAB = "gpm-tab", STORE_PRODUCT = "gpm-product";
  var NONE = "?";                       // the group key of «Без продукту» (a product id can never hold a question mark)
  var PALETTE = ["#2f6fde", "#1a7f37", "#b35900", "#8250df", "#0e7c86", "#c2255c", "#5c6b00", "#6c5ce7"];
  var NO_PRODUCT_COLOR = "#d0d7de";
  var ATTENTION = ["ok", "warn", "crit"];

  // ---- storage: a convenience only, never trusted to be there --------------------------------------------------------
  function stored(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function keep(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* kept for this session only */ }
  }

  // ---- values -----------------------------------------------------------------------------------------------------------
  function text(v) {
    if (typeof v === "string") { return v.length > TEXT_MAX ? v.slice(0, TEXT_MAX) : v; }
    if (typeof v === "number" && isFinite(v)) { return String(v); }
    return "";
  }
  function plainTitle(v, fallback) {
    if (typeof v !== "string") { return fallback; }
    var s = v.trim();
    if (!s) { return fallback; }
    return s.length > TITLE_MAX ? s.slice(0, TITLE_MAX) : s;
  }
  function attention(v) { return ATTENTION.indexOf(v) >= 0 ? v : null; }
  function svg(tag, attrs) {
    var n = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function labelOf(level) {
    var t = S.t;
    return level === "ok" ? t.attentionOk : level === "warn" ? t.attentionWarn : t.attentionCrit;
  }

  // ---- products ---------------------------------------------------------------------------------------------------------
  function productIndex(meta, id) {
    var list = meta && meta.products ? meta.products : [];
    for (var i = 0; i < list.length; i++) { if (list[i].id === id) { return i; } }
    return -1;
  }
  // a product id as the group it belongs to: itself when meta knows it, else «Без продукту»; with no products declared,
  // everything is one unlabelled group
  function groupKey(meta, id) {
    if (!meta || !meta.products.length) { return ""; }
    return productIndex(meta, id) >= 0 ? id : NONE;
  }
  function colorOf(meta, index) {
    if (index < 0) { return NO_PRODUCT_COLOR; }
    return meta.products[index].color || PALETTE[index % PALETTE.length];
  }
  // black or white, whichever reads better on the colour
  function foreground(bg) { return S.ratio(bg, "#ffffff") >= S.ratio(bg, "#000000") ? "#ffffff" : "#000000"; }

  // the short name of a product on its colour; a product without a valid colour takes one from PALETTE by its position
  function productChip(product, meta) {
    var i = productIndex(meta, product);
    var chip = el("span", "gpm-chip", i < 0 ? S.t.noProduct : meta.products[i].label);
    var bg = colorOf(meta, i);
    chip.style.backgroundColor = bg;
    chip.style.color = foreground(bg);
    chip.setAttribute("data-product", i < 0 ? NONE : product);
    return chip;
  }

  function productSwitch(meta, current, onPick) {
    if (!meta || meta.products.length < 2) { return null; }
    var group = el("div", "gpm-products");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", S.t.product);
    [{ id: "", label: S.t.all, color: null }].concat(meta.products.map(function (p, i) {
      return { id: p.id, label: p.label, color: colorOf(meta, i) };
    })).forEach(function (p) {
      var b = el("button", null, null);
      b.type = "button";
      b.setAttribute("data-product", p.id);
      b.setAttribute("aria-pressed", p.id === current ? "true" : "false");
      if (p.color) {
        var dot = el("span", "gpm-dot");
        dot.setAttribute("aria-hidden", "true");
        dot.style.backgroundColor = p.color;
        b.appendChild(dot);
      }
      b.appendChild(document.createTextNode(p.label));
      b.addEventListener("click", function () { onPick(p.id); });
      group.appendChild(b);
    });
    return group;
  }

  // ---- blocks -----------------------------------------------------------------------------------------------------------
  // A block renderer takes the data of one section document and the view -> an element, or null when the data does not
  // hold what the block shows. `view` = {meta, filter, chip(id), shows(id)}; `info` = {id, product, section, made}.
  function mark(level) {
    var span = el("span", "gpm-attn gpm-attn-" + level);
    var dot = el("span", "gpm-mark");
    dot.setAttribute("aria-hidden", "true");
    span.appendChild(dot);
    span.appendChild(el("span", "gpm-attn-text", labelOf(level)));
    return span;
  }

  function table(data, view) {
    var cols = (Array.isArray(data.columns) ? data.columns : []).filter(function (c) { return isObj(c) && str(c.key, 64); }).slice(0, MAX_COLS);
    var rows = (Array.isArray(data.rows) ? data.rows : []).filter(function (r) {
      return isObj(r) && (!str(r.product, 64) || view.shows(r.product));
    }).slice(0, MAX_ROWS);
    if (!cols.length || !rows.length) { return null; }
    var withState = rows.some(function (r) { return attention(r.attention); });
    var wrap = el("div", "gpm-scroll");
    wrap.tabIndex = 0;
    var tbl = el("table", "gpm-table");
    var head = el("tr");
    if (withState) { var th0 = el("th", null, S.t.status); th0.scope = "col"; head.appendChild(th0); }
    cols.forEach(function (c) { var th = el("th", null, str(c.title, 80) || c.key); th.scope = "col"; head.appendChild(th); });
    var thead = el("thead");
    thead.appendChild(head);
    tbl.appendChild(thead);
    var tbody = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr");
      var level = attention(r.attention);
      if (withState) {
        var s = el("td", "gpm-state-cell");
        if (level) { s.appendChild(mark(level)); }
        tr.appendChild(s);
      }
      cols.forEach(function (c, i) {
        var td = el("td");
        if (i === 0 && str(r.product, 64)) { td.appendChild(view.chip(r.product)); td.appendChild(document.createTextNode(" ")); }
        td.appendChild(document.createTextNode(Object.prototype.hasOwnProperty.call(r, c.key) ? text(r[c.key]) : ""));
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    wrap.appendChild(tbl);
    var out = el("div", "gpm-table-wrap");
    out.appendChild(wrap);
    var w = isObj(data.weakest) ? data.weakest : null;
    if (w && str(w.title, 200) && num(w.score) !== null) {
      out.appendChild(el("p", "gpm-weakest", S.t.weakest + ": " + w.title + " — " + w.score));
    }
    return out;
  }

  function items(data, view, withDate, info) {
    var list = (Array.isArray(data.items) ? data.items : []).filter(function (it) {
      return isObj(it) && str(it.title, 300) && (!str(it.product, 64) || view.shows(it.product));
    }).slice(0, MAX_ITEMS);
    if (!list.length) { return null; }
    var ul = el("ul", "gpm-list");
    list.forEach(function (it) {
      var li = el("li", "gpm-item");
      var level = attention(it.attention);
      if (level) { li.appendChild(mark(level)); }
      // the card's own header already names the product: the row says it only when it is another one (or there is no header)
      if (str(it.product, 64) && !(info && info.header && it.product === info.product)) { li.appendChild(view.chip(it.product)); }
      if (withDate && str(it.at, 40)) {
        var d = S.showDate(it.at, S.lang) || it.at;
        li.appendChild(el("span", "gpm-at", d));
      }
      li.appendChild(el("span", "gpm-item-title", it.title));
      if (str(it.note, 300)) { li.appendChild(el("span", "gpm-note", it.note)); }
      ul.appendChild(li);
    });
    return ul;
  }
  function list(data, view, info) { return items(data, view, false, info); }
  function feed(data, view, info) { return items(data, view, true, info); }

  function sparkline(trend) {
    var pts = trend.slice(0, MAX_TREND);
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), span = hi - lo;
    var W = 120, H = 32, P = 3;
    var coords = pts.map(function (v, i) {
      var x = P + (W - 2 * P) * i / (pts.length - 1);
      var y = span === 0 ? H / 2 : H - P - (H - 2 * P) * (v - lo) / span;
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var s = svg("svg", { "class": "gpm-spark", viewBox: "0 0 " + W + " " + H, width: String(W), height: String(H), role: "img" });
    s.setAttribute("aria-label", S.t.trend);
    s.appendChild(svg("polyline", { points: coords.join(" "), fill: "none", "stroke-width": "2", "class": "gpm-spark-line" }));
    return s;
  }

  function number(data) {
    var value = num(data.value);
    if (value === null) { return null; }
    var box = el("div", "gpm-number");
    box.appendChild(el("span", "gpm-num-value", String(value)));
    if (str(data.unit, 24)) { box.appendChild(el("span", "gpm-num-unit", data.unit)); }
    var delta = num(data.delta);
    if (delta !== null) {
      box.appendChild(el("span", "gpm-num-delta", (delta > 0 ? "+" : "") + delta));
    }
    var trend = (Array.isArray(data.trend) ? data.trend : []).filter(function (v) { return num(v) !== null; });
    if (trend.length >= 2) { box.appendChild(sparkline(trend)); }
    return box;
  }

  // a stage is `warn` at (value - baseline) / baseline <= -warning and `crit` at <= -critical (meta.thresholds)
  function stageLevel(value, baseline, th) {
    if (baseline === null || baseline <= 0) { return null; }
    var drop = (value - baseline) / baseline;
    return drop <= -th.critical ? "crit" : drop <= -th.warning ? "warn" : "ok";
  }

  function chart(data, view) {
    var stages = (Array.isArray(data.stages) ? data.stages : []).filter(function (s) {
      return isObj(s) && str(s.title, 200) && num(s.value) !== null;
    }).slice(0, MAX_STAGES);
    if (!stages.length) { return null; }
    var th = view.meta && view.meta.thresholds ? view.meta.thresholds : { warning: 0.1, critical: 0.25 };
    var top = 0;
    stages.forEach(function (s) { top = Math.max(top, s.value, num(s.baseline) || 0); });
    var box = el("div", "gpm-chart");
    stages.forEach(function (s) {
      var base = num(s.baseline);
      var level = stageLevel(s.value, base, th);
      var unit = str(s.unit, 24) ? " " + s.unit : "";
      var row = el("div", "gpm-stage" + (level ? " gpm-stage-" + level : ""));
      var head = el("div", "gpm-stage-head");
      head.appendChild(el("span", "gpm-stage-title", s.title));
      head.appendChild(el("span", "gpm-stage-value", s.value + unit));
      if (base !== null) { head.appendChild(el("span", "gpm-stage-base", S.t.baseline + " " + base + unit)); }
      if (level && level !== "ok") { head.appendChild(mark(level)); }
      row.appendChild(head);
      var scale = top > 0 ? 100 / top : 0;
      var g = svg("svg", { "class": "gpm-bars", viewBox: "0 0 100 10", preserveAspectRatio: "none", role: "img", width: "100%", height: "10" });
      g.setAttribute("aria-label", s.title + ": " + s.value + (base !== null ? " / " + base : ""));
      g.appendChild(svg("rect", { "class": "gpm-bar-track", x: "0", y: "0", width: "100", height: "10" }));
      g.appendChild(svg("rect", { "class": "gpm-bar gpm-bar-" + (level || "plain"), x: "0", y: "1", width: String(Math.max(0, s.value) * scale), height: "8" }));
      if (base !== null) {
        g.appendChild(svg("line", { "class": "gpm-bar-base", x1: String(Math.max(0, base) * scale), x2: String(Math.max(0, base) * scale), y1: "0", y2: "10", "vector-effect": "non-scaling-stroke" }));
      }
      row.appendChild(g);
      box.appendChild(row);
    });
    return box;
  }

  function placeholder(words) { return el("p", "gpm-placeholder", words); }
  function map() { return placeholder(S.t.mapPlaceholder); }

  // The renderers by block name: map.js replaces `map`. Sources that are not sections: `@edits` is the team's edits,
  // fed by later files.
  var RENDER = { table: table, list: list, number: number, chart: chart, feed: feed, map: map };
  var SOURCES = { "@edits": function () { return placeholder(S.t.editsPlaceholder); } };
  S.blocks = RENDER;
  S.sources = SOURCES;
  S.productChip = productChip;
  S.productSwitch = productSwitch;
  // What the window's menu and tray need of the modules: the product and the tab shown, a way to open a tab and to hear
  // of a change (the modules part below fills them in).
  var viewFns = [];
  S.view = function () { return { product: "", tab: null }; };
  S.openTab = function () { return false; };
  S.onView = function (fn) { if (typeof fn === "function") { viewFns.push(fn); } };
  function viewChanged() { viewFns.slice().forEach(function (f) { try { f(); } catch (e) { /* one listener does not stop the others */ } }); }
  var HAS_MODULES = "gpm-has-modules";      // on <html> while the modules are shown: the host's own page colour must not show under them

  // ---- the owner's config/app ---------------------------------------------------------------------------------------
  // One block entry: {block, source, title} + `bad` when it is not one this page can show. A title is text (a profile's
  // is {uk, en}). `custom` modules come from the owner's document: never `map`, never a source outside the section names.
  function normBlock(raw, custom, lang) {
    var b = isObj(raw) ? raw : {};
    var title = custom ? (b.title === undefined ? null : plainTitle(b.title, null))
      : (isObj(b.title) ? (str(b.title[lang], TITLE_MAX) || null) : null);
    var ok = BLOCK_NAMES.indexOf(b.block) >= 0 && !(custom && b.block === "map")
      && typeof b.source === "string" && (SECTION.test(b.source) || b.source === "@edits");
    return { block: ok ? b.block : null, source: ok ? b.source : null, title: title, bad: !ok };
  }

  // One module -> {id, title, home, blocks: [...], composed} or null (no usable id). A module in neither form, in both
  // forms, with a `map` next to another block, or without blocks shows the line «блок не підтримується».
  function normModule(raw, custom, lang) {
    if (!isObj(raw) || typeof raw.id !== "string" || !MODULE_ID.test(raw.id)) { return null; }
    var title = custom ? plainTitle(raw.title, raw.id)
      : (isObj(raw.title) && str(raw.title[lang], TITLE_MAX)) || raw.id;
    var short = raw.block !== undefined || raw.source !== undefined, composed = raw.blocks !== undefined;
    var blocks;
    if (short && composed) { blocks = [normBlock(null)]; }
    else if (composed) {
      blocks = Array.isArray(raw.blocks) ? raw.blocks.slice(0, MAX_BLOCKS).map(function (b) { return normBlock(b, custom, lang); }) : [];
      if (!blocks.length) { blocks = [normBlock(null)]; }
      else if (blocks.length > 1 && blocks.some(function (b) { return b.block === "map"; })) { blocks = [normBlock(null)]; }
    } else if (short) { blocks = [normBlock(raw, custom, lang)]; }
    else { blocks = [normBlock(null)]; }
    return { id: raw.id, title: title, home: !custom && raw.home === true, blocks: blocks, composed: composed && !(short && composed) };
  }

  // the document as foreign input -> {modules: [{id, on, order}], custom: [module]} or null
  function cleanConfig(raw) {
    if (!isObj(raw) || (raw.v !== undefined && raw.v !== 1)) { return null; }
    var cfg = { modules: [], custom: [] };
    (Array.isArray(raw.modules) ? raw.modules.slice(0, MAX_RULES) : []).forEach(function (r) {
      if (!isObj(r) || typeof r.id !== "string" || !MODULE_ID.test(r.id) || typeof r.on !== "boolean") { return; }
      var rule = { id: r.id, on: r.on, order: null };
      if (r.order !== undefined) {
        if (typeof r.order !== "number" || Math.floor(r.order) !== r.order || Math.abs(r.order) > 1000) { return; }
        rule.order = r.order;
      }
      cfg.modules.push(rule);
    });
    var seen = {};
    (Array.isArray(raw.custom) ? raw.custom : []).forEach(function (c) {
      if (cfg.custom.length >= MAX_CUSTOM) { return; }
      var m = normModule(c, true, "uk");
      if (!m || Object.prototype.hasOwnProperty.call(seen, m.id)) { return; }
      seen[m.id] = true;
      cfg.custom.push(m);
    });
    return cfg;
  }

  function parseConfig(qs) {
    try {
      var docs = qs && qs.docs ? Array.prototype.slice.call(qs.docs) : [];
      for (var i = 0; i < docs.length; i++) {
        var d = docs[i];
        if (d && d.id === "app" && d.exists !== false && typeof d.data === "function") { return cleanConfig(d.data()); }
      }
    } catch (e) { /* the default order stands */ }
    return null;
  }

  // The document config/app, kept live like the snapshot: resolves once with the first answer (null when there is none,
  // after 10 s, on a refusal or without a database) and calls onChange with every later one. Never throws, never rejects.
  function readConfig(db, onChange) {
    return new Promise(function (resolve) {
      var settled = false, timer = null;
      function first(v) { if (!settled) { settled = true; if (timer) { clearTimeout(timer); } resolve(v); } }
      if (!db || typeof db.collection !== "function") { first(null); return; }
      timer = setTimeout(function () { first(null); }, S.LOAD_TIMEOUT);
      try {
        db.collection("config").onSnapshot(function (qs) {
          var cfg = parseConfig(qs);
          if (!settled) { first(cfg); }
          else if (onChange) { try { onChange(cfg); } catch (e) { /* a listener must not break the stream */ } }
        }, function () { first(null); });
      } catch (e) { first(null); }
    });
  }
  S.readConfig = readConfig;
  S.cleanConfig = cleanConfig;

  // The modules in the order of the tabs: the profile's, then the owner's custom ones; `on: false` removes one, `order`
  // moves one (a module without an order keeps its place; a tie goes to the one with an order).
  function moduleList(profile, config, lang) {
    var base = (Array.isArray(profile.modules) ? profile.modules : []).map(function (m) { return normModule(m, false, lang); })
      .filter(function (m) { return m; });
    var ids = {};
    base.forEach(function (m) { ids[m.id] = true; });
    var all = base.concat(config ? config.custom.filter(function (m) { return !ids[m.id]; }) : []);
    var rules = {};
    (config ? config.modules : []).forEach(function (r) { if (!Object.prototype.hasOwnProperty.call(rules, r.id)) { rules[r.id] = r; } });
    var out = [];
    all.forEach(function (m, i) {
      var r = Object.prototype.hasOwnProperty.call(rules, m.id) ? rules[m.id] : null;
      if (r && r.on === false) { return; }
      var ordered = !!(r && r.order !== null);
      m.pos = ordered ? r.order : i;
      m.ordered = ordered;
      m.index = i;
      out.push(m);
    });
    out.sort(function (a, b) {
      return a.pos - b.pos || (a.ordered === b.ordered ? 0 : a.ordered ? -1 : 1) || a.index - b.index;
    });
    return out;
  }

  // ---- the data of a module ---------------------------------------------------------------------------------------
  // the section documents of a source: the sections named so; for `map` also `map.*`
  function docsOf(snap, source) {
    return Object.keys(snap.sections).sort().filter(function (id) {
      var name = snap.sections[id].section;
      return name === source || (source === "map" && name.indexOf("map.") === 0);
    }).map(function (id) { return { id: id, sec: snap.sections[id] }; });
  }

  // One block of a module -> {node, dates}: the cards of its documents, products in the order of meta.products and
  // «Без продукту» last; the product switch decides which products show.
  function renderBlock(b, snap, view) {
    var box = el("div", "gpm-block-body");
    var dates = [];
    if (b.bad) { box.appendChild(el("p", "gpm-unsupported", S.t.unsupported)); return { node: box, dates: dates }; }
    var cards = [];
    if (SOURCES[b.source]) {
      cards.push({ key: "", node: SOURCES[b.source](view), product: "" });
    } else if (typeof RENDER[b.block].all === "function") {
      // a renderer that draws every document of its block at once (map.js: a picker, one map at a time)
      var docs = docsOf(snap, b.source).filter(function (d) {
        return view.filter === "" || groupKey(snap.meta, d.sec.product) === view.filter;
      }).map(function (d) {
        return { data: d.sec.data, info: { id: d.id, product: d.sec.product, section: d.sec.section, made: d.sec.made } };
      });
      var whole = docs.length ? RENDER[b.block].all(docs, view) : null;
      if (whole) {
        cards.push({ key: "", node: whole, product: "" });
        docs.forEach(function (d) { dates.push(snap.meta.sections[d.info.id] || d.info.made); });
      }
    } else {
      docsOf(snap, b.source).forEach(function (d) {
        var key = groupKey(snap.meta, d.sec.product);
        if (view.filter !== "" && key !== view.filter) { return; }
        var node = RENDER[b.block](d.sec.data, view, { id: d.id, product: d.sec.product, section: d.sec.section, made: d.sec.made, header: key !== "" });
        if (!node) { return; }
        cards.push({ key: key, node: node, product: d.sec.product });
        dates.push(snap.meta.sections[d.id] || d.sec.made);
      });
      var order = snap.meta.products.map(function (p) { return p.id; }).concat([NONE]);
      cards.sort(function (a, b2) { return order.indexOf(a.key) - order.indexOf(b2.key); });
    }
    if (!cards.length) { box.appendChild(el("p", "gpm-empty", S.t.empty)); return { node: box, dates: dates }; }
    cards.forEach(function (c) {
      var card = el("div", "gpm-card");
      card.setAttribute("data-product", c.key);
      if (c.key !== "") {
        var head = el("div", "gpm-card-head");
        head.appendChild(productChip(c.product, snap.meta));
        card.appendChild(head);
      }
      card.appendChild(c.node);
      box.appendChild(card);
    });
    return { node: box, dates: dates };
  }

  function renderModule(m, snap, view) {
    var panel = el("div", "gpm-module");
    var dates = [];
    m.blocks.forEach(function (b) {
      var sec = el("section", "gpm-block");
      if (m.composed && b.title) { sec.appendChild(el("h3", "gpm-block-title", b.title)); }
      var r = renderBlock(b, snap, view);
      sec.appendChild(r.node);
      dates = dates.concat(r.dates);
      panel.appendChild(sec);
    });
    if (dates.length) {
      var oldest = dates.slice().sort()[0];
      var shown = S.showDate(oldest, S.lang);
      if (shown) { panel.insertBefore(el("p", "gpm-fresh-module", S.t.freshness + shown), panel.firstChild); }
    }
    return panel;
  }

  // renderModules(profile, config, data, product, active) -> {modules, active, tabs, panel}: the tabs and the panel of the
  // open module as elements; `product` is "" for «Усі» or one product id. Tab clicks are wired by the part below.
  function renderModules(profile, config, data, product, active, lang) {
    var mods = moduleList(profile, config, lang);
    var open = null;
    mods.forEach(function (m) { if (m.id === active) { open = m; } });
    if (!open) { open = mods.filter(function (m) { return m.home; })[0] || mods[0] || null; }
    var meta = data.meta;
    var view = {
      meta: meta, filter: product,
      chip: function (id) { return meta.products.length ? productChip(id, meta) : document.createTextNode(""); },
      shows: function (id) { return product === "" || groupKey(meta, id) === product; }
    };
    return { modules: mods, active: open ? open.id : null, panel: open ? renderModule(open, data, view) : null };
  }
  S.renderModules = renderModules;

  // ---- the part -----------------------------------------------------------------------------------------------------
  S.part("modules", function (ctx) {
    var profile = ctx.profile;
    if (!Array.isArray(profile.modules) || !profile.modules.length) { return; }     // no modules: the page is never hidden
    var root = document.querySelector(".gpm-modules");
    var page = document.querySelector(".gpm-page");
    if (!root) { return; }
    var config = null, active = stored(STORE_TAB), product = null, switchEl = null;

    var shownTab = null;
    S.view = function () { return { product: product || "", tab: shownTab }; };
    S.openTab = function (id) { pickTab(id); return shownTab === id; };

    function showPage() {
      document.documentElement.classList.remove(HAS_MODULES);
      shownTab = null;
      root.hidden = true;
      if (page) { page.hidden = false; }
      if (switchEl && switchEl.parentNode) { switchEl.parentNode.removeChild(switchEl); }
      switchEl = null;
      viewChanged();
    }

    function pickProduct(id) { product = id; keep(STORE_PRODUCT, id); paint(); }
    function pickTab(id) { active = id; keep(STORE_TAB, id); paint(); }

    function paint() {
      var snap = ctx.data;
      // a snapshot was read: its meta holds a date. Without one the page stays as it was.
      if (!snap || !snap.meta || !S.showDate(snap.meta.made, "en")) { showPage(); return; }
      var focus = document.activeElement && root.contains(document.activeElement) || (switchEl && switchEl.contains(document.activeElement))
        ? document.activeElement : null;
      var focusKey = focus ? (focus.getAttribute("data-tab") !== null ? "tab:" + focus.getAttribute("data-tab")
        : focus.getAttribute("data-product") !== null ? "product:" + focus.getAttribute("data-product") : null) : null;
      if (product === null) { product = stored(STORE_PRODUCT) || ""; }
      if (product !== "" && productIndex(snap.meta, product) < 0) { product = ""; }
      var r = renderModules(profile, config, snap, product, active, ctx.lang);

      var tabs = el("div", "gpm-tabs");
      tabs.setAttribute("role", "tablist");
      tabs.setAttribute("aria-label", ctx.t.modules);
      r.modules.forEach(function (m) {
        var b = el("button", "gpm-tab", m.title);
        b.type = "button";
        b.id = "gpm-tab-" + m.id;
        b.setAttribute("role", "tab");
        b.setAttribute("data-tab", m.id);
        b.setAttribute("aria-selected", m.id === r.active ? "true" : "false");
        b.setAttribute("aria-controls", "gpm-panel");
        b.tabIndex = m.id === r.active ? 0 : -1;
        b.addEventListener("click", function () { pickTab(m.id); });
        tabs.appendChild(b);
      });
      tabs.addEventListener("keydown", function (e) {
        var ids = r.modules.map(function (m) { return m.id; });
        var at = ids.indexOf(r.active), to = -1;
        if (e.key === "ArrowRight") { to = (at + 1) % ids.length; }
        else if (e.key === "ArrowLeft") { to = (at - 1 + ids.length) % ids.length; }
        else if (e.key === "Home") { to = 0; }
        else if (e.key === "End") { to = ids.length - 1; }
        if (to >= 0 && ids.length) { e.preventDefault(); focusKey = "tab:" + ids[to]; pickTab(ids[to]); refocus(); }
      });

      var body = el("div", "gpm-panel");
      body.id = "gpm-panel";
      body.setAttribute("role", "tabpanel");
      if (r.active) { body.setAttribute("aria-labelledby", "gpm-tab-" + r.active); }
      body.appendChild(r.panel || el("p", "gpm-empty", ctx.t.noModules));

      while (root.firstChild) { root.removeChild(root.firstChild); }
      root.appendChild(tabs);
      root.appendChild(body);

      if (switchEl && switchEl.parentNode) { switchEl.parentNode.removeChild(switchEl); }
      switchEl = productSwitch(snap.meta, product, pickProduct);
      if (switchEl) { ctx.header.insertBefore(switchEl, ctx.actions); }

      root.hidden = false;
      if (page) { page.hidden = true; }
      document.documentElement.classList.add(HAS_MODULES);
      shownTab = r.active;
      refocus();
      viewChanged();
      function refocus() {
        if (!focusKey) { return; }
        var sel = focusKey.indexOf("tab:") === 0 ? '[data-tab="' + focusKey.slice(4) + '"]' : '[data-product="' + focusKey.slice(8) + '"]';
        var scope = focusKey.indexOf("tab:") === 0 ? root : switchEl;
        var node = scope ? scope.querySelector(sel) : null;
        if (node) { try { node.focus(); } catch (e) { /* nothing to focus */ } }
      }
    }

    function safePaint() {
      try { paint(); } catch (e) { showPage(); }      // a failure shows the page as it was
    }
    ctx.onData(safePaint);
    safePaint();
    return ctx.db().then(function (db) {
      return readConfig(db, function (c) { config = c; safePaint(); });
    }).then(function (c) { config = c; safePaint(); });
  });
})();
