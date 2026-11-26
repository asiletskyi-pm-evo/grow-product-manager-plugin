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
      onPlan: "За планом",
      attentionWarn: "Увага",
      attentionCrit: "Критично",
      baseline: "база",
      weakest: "Найслабше",
      trend: "Тренд",
      needAttention: "потребує уваги",
      waitsOne: " річ чекає на тебе.",
      waitsFew: " речі чекають на тебе.",
      waitsMany: " речей чекає на тебе.",
      nothingWaits: "На тебе нічого не чекає.",
      askAttention: "Уваги потребують: ",
      nothingAsks: "Сигналів уваги немає.",
      small: ["", "Одна", "Дві", "Три", "Чотири"],
      smallSignal: ["", "один", "два", "три", "чотири"],
      signalsOne: " сигнал.",
      signalsFew: " сигнали.",
      signalsMany: " сигналів.",
      thereIs: "Є ",
      noSignals: "Сигналів немає.",
      nowFocus: "Зараз час фокусу, до ",
      nowMeeting: "Зараз зустріч, до ",
      nextAt: "Далі за календарем о ",
      goal: "Ціль",
      dataFrom: "Дані від ",
      inFirst: "у ",
      inNext: ", у ",
      inLast: " і в ",
      more: "Докладніше",
      backTo: "← ",
      alwaysOn: "Завжди увімкнено",
      turnedOn: " увімкнено",
      ownerOnly: "Змінювати модулі може лише власник.",
      notSaved: "Не вдалося зберегти. Спробуй ще раз.",
      saidCopied: "Скопійовано: «%s». Встав це в чат із Claude.",
      saidPlain: "Скажи Claude: «%s»."
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
      onPlan: "On plan",
      attentionWarn: "Warning",
      attentionCrit: "Critical",
      baseline: "baseline",
      weakest: "Weakest",
      trend: "Trend",
      needAttention: "need attention",
      waitsOne: " thing waits for you.",
      waitsFew: " things wait for you.",
      waitsMany: " things wait for you.",
      nothingWaits: "Nothing waits for you.",
      askAttention: "Asking for attention: ",
      nothingAsks: "Nothing asks for attention.",
      small: [],
      smallSignal: [],
      signalsOne: " signal.",
      signalsFew: " signals.",
      signalsMany: " signals.",
      thereIs: "",
      noSignals: "No signals.",
      nowFocus: "Focus time now, until ",
      nowMeeting: "A meeting now, until ",
      nextAt: "Next on the calendar at ",
      goal: "Goal",
      dataFrom: "Data from ",
      inFirst: "in ",
      inNext: ", in ",
      inLast: " and in ",
      more: "More",
      backTo: "← ",
      alwaysOn: "Always on",
      turnedOn: " on",
      ownerOnly: "Only the owner can change the modules.",
      notSaved: "Could not save. Try again.",
      saidCopied: "Copied: “%s”. Paste it into the chat with Claude.",
      saidPlain: "Say to Claude: “%s”."
    }
  });

  var SVG_NS = "http://www.w3.org/2000/svg";
  var BLOCK_NAMES = ["table", "list", "number", "chart", "feed", "map", "lead", "bars", "line", "day"];    // the same as BLOCKS in app_shell.py
  var QUIET = ["lead", "bars", "line"];       // blocks that take no room while their section has nothing to show (charts.js draws them)
  var SECTION = /^[a-z0-9][a-z0-9.-]{0,63}$/;
  var MODULE_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
  var TITLE_MAX = 80, MAX_BLOCKS = 8, MAX_CUSTOM = 20, MAX_RULES = 64;      // the same limits as app_shell.py's check_config
  var MAX_COLS = 12, MAX_ROWS = 500, MAX_ITEMS = 200, MAX_STAGES = 30, MAX_TREND = 60, TEXT_MAX = 500;
  var STORE_TAB = "gpm-tab", STORE_PRODUCT = "gpm-product";
  var NONE = "?";                       // the group key of «Без продукту» (a product id can never hold a question mark)
  var PALETTE = ["#2f6fde", "#1a7f37", "#b35900", "#8250df", "#0e7c86", "#c2255c", "#5c6b00", "#6c5ce7"];
  var NO_PRODUCT_COLOR = "#d0d7de";
  var ATTENTION = ["ok", "warn", "crit"];
  var GROUP_ID = /^[a-z][a-z0-9-]{0,31}$/;        // a block's `group`: the blocks that share it stand in one section
  var ROWS = ["table", "list", "feed"];           // blocks made of rows: in the rail layout the products share one of them

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
  var railMode = false;       // the side rail is the layout shown: a row on plan says so in the rail's words
  function labelOf(level) {
    var t = S.t;
    return level === "ok" ? (railMode ? t.onPlan : t.attentionOk) : level === "warn" ? t.attentionWarn : t.attentionCrit;
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
    // the colour goes in as two properties the style sheet reads: a layout may show it as a dot beside the name
    chip.style.setProperty("--gpm-chip-bg", bg);
    chip.style.setProperty("--gpm-chip-fg", foreground(bg));
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
  // A renderer tells the registry about a node it drew and that something else may add to: decorate(kind, node, key) —
  // kinds `stage` (a chart stage's head, key = "<section document id>|<stage id>", so a value is always the value of
  // that one document — that product, that section) and `code` (a map row, key = its code, from map.js).
  // Whoever registered with onDecorate (live.js) hears it; with nobody registered nothing changes in the output.
  var DECORATORS = [];
  function onDecorate(fn) { if (typeof fn === "function") { DECORATORS.push(fn); } }
  function decorate(kind, node, key) {
    DECORATORS.forEach(function (fn) { try { fn(kind, node, key); } catch (e) { /* one decorator does not stop the others */ } });
  }

  function mark(level) {
    var span = el("span", "gpm-attn gpm-attn-" + level);
    var dot = el("span", "gpm-mark");
    dot.setAttribute("aria-hidden", "true");
    span.appendChild(dot);
    span.appendChild(el("span", "gpm-attn-text", labelOf(level)));
    return span;
  }

  // the mark alone, with its word for a screen reader only: for a value that already says what is wrong
  function shape(level) {
    var span = el("span", "gpm-attn gpm-attn-" + level);
    var dot = el("span", "gpm-mark");
    dot.setAttribute("aria-hidden", "true");
    span.appendChild(dot);
    span.appendChild(el("span", "gpm-vh", labelOf(level) + ": "));
    return span;
  }

  // One cell of a table: text by default. A column may ask for more: `kind` `num` sets a number to the right;
  // `segments` and `meter` are marks drawn by charts.js (S.cells); `sub` names the row's field shown small beside the
  // value. The row's `marks` {<column key>: warn | crit} put the mark of attention at that cell.
  function cell(td, r, c, first, view, info) {
    var has = Object.prototype.hasOwnProperty.call(r, c.key);
    var subKey = str(c.sub, 64);
    var sub = subKey && Object.prototype.hasOwnProperty.call(r, subKey) ? text(r[subKey]) : "";
    var lvl = isObj(r.marks) ? attention(r.marks[c.key]) : null;
    if (lvl === "ok") { lvl = null; }
    var draw = S.cells && typeof S.cells[c.kind] === "function" ? S.cells[c.kind] : null;
    var node = draw && has ? draw(r[c.key], c, lvl) : null;
    if (node) {
      var box = el("div", "gpm-cell gpm-cell-" + c.kind);
      box.appendChild(node);
      if (sub) {
        var note = el("span", "gpm-cell-sub" + (lvl ? " gpm-ink-" + lvl : ""));
        if (lvl) { note.appendChild(shape(lvl)); }
        note.appendChild(document.createTextNode(sub));
        box.appendChild(note);
      }
      td.appendChild(box);
      return;
    }
    if (c.kind === "num") { td.className = "gpm-num"; }
    var value = has ? text(r[c.key]) : "";
    if (first) {
      var lead = el("div", "gpm-cell-lead");
      // the card's own header already names the product: the row says it only when it is another one
      if (str(r.product, 64) && !(info && info.header && r.product === info.product)) { lead.appendChild(view.chip(r.product)); lead.appendChild(document.createTextNode(" ")); }
      lead.appendChild(el("span", "gpm-cell-main", value));
      if (sub) { lead.appendChild(el("span", "gpm-cell-sub", sub)); } else { lead.classList.add("gpm-cell-lead-inline"); }
      td.appendChild(lead);
      return;
    }
    if (lvl) { td.classList.add("gpm-ink-" + lvl); td.appendChild(shape(lvl)); }
    td.appendChild(document.createTextNode(value));
    if (sub) { td.appendChild(el("span", "gpm-cell-sub", sub)); }
  }

  function table(data, view, info) {
    var cols = (Array.isArray(data.columns) ? data.columns : []).filter(function (c) { return isObj(c) && str(c.key, 64); }).slice(0, MAX_COLS);
    var rows = (Array.isArray(data.rows) ? data.rows : []).filter(function (r) {
      return isObj(r) && (!str(r.product, 64) || view.shows(r.product));
    }).slice(0, MAX_ROWS);
    if (!cols.length || !rows.length) { return null; }
    // the column «Стан» says a row's attention; rows that mark their own cells (`marks`) and tables with a drawn cell
    // (a bar of parts, a meter) say it in the cell and need no such column
    var marked = rows.some(function (r) { return isObj(r.marks); }) || cols.some(function (c) { return S.cells && typeof S.cells[c.kind] === "function"; });
    var withState = !marked && rows.some(function (r) { return attention(r.attention); });
    var wrap = el("div", "gpm-scroll");
    wrap.tabIndex = 0;
    var tbl = el("table", "gpm-table");
    var head = el("tr");
    if (withState) { var th0 = el("th", null, S.t.status); th0.scope = "col"; head.appendChild(th0); }
    // a column may name a `group`: the neighbours that share it stand under one heading
    var groups = cols.map(function (c) { return str(c.group, 40) || ""; });
    var starts = cols.map(function (c, i) { return !!groups[i] && groups[i] !== groups[i - 1]; });
    cols.forEach(function (c, i) {
      var th = el("th", c.kind === "num" ? "gpm-num" : null, str(c.title, 80) || c.key);
      th.scope = "col";
      if (starts[i]) { th.classList.add("gpm-col-start"); }
      head.appendChild(th);
    });
    var thead = el("thead");
    if (groups.some(function (g) { return g; })) {
      var over = el("tr", "gpm-col-groups");
      if (withState) { over.appendChild(el("td")); }
      for (var gi = 0; gi < cols.length;) {
        var span = 1;
        while (groups[gi] && groups[gi + span] === groups[gi]) { span++; }
        var cellOver = el(groups[gi] ? "th" : "td", groups[gi] ? "gpm-col-group gpm-col-start" : null, groups[gi] || null);
        if (groups[gi]) { cellOver.scope = "colgroup"; cellOver.colSpan = span; }
        over.appendChild(cellOver);
        gi += span;
      }
      thead.appendChild(over);
    }
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
        cell(td, r, c, i === 0, view, info);
        if (starts[i]) { td.classList.add("gpm-col-start"); }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    wrap.appendChild(tbl);
    var out = el("div", "gpm-table-wrap");
    cols.forEach(function (c) {         // a column of marks names its parts over the table
      var lg = S.cellLegend && typeof S.cellLegend[c.kind] === "function" ? S.cellLegend[c.kind](c) : null;
      if (lg) { out.appendChild(lg); }
    });
    out.appendChild(wrap);
    var w = isObj(data.weakest) ? data.weakest : null;
    if (w && str(w.title, 200) && num(w.score) !== null) {
      out.appendChild(el("p", "gpm-weakest", S.t.weakest + ": " + w.title + " — " + w.score));
    }
    if (str(data.note, 300)) { out.appendChild(el("p", "gpm-source", data.note)); }
    return out;
  }

  // a moment as this window's own day and time, 26.11.2026, 13:11; a bare date as S.showDate gives it
  function when(at) {
    var d = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(at) ? new Date(at) : null;
    if (!d || isNaN(d.getTime())) { return S.showDate(at, S.lang) || at; }
    function two(n) { return ("0" + n).slice(-2); }
    var time = two(d.getHours()) + ":" + two(d.getMinutes());
    return (S.lang === "en" ? d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate()) + " "
      : two(d.getDate()) + "." + two(d.getMonth() + 1) + "." + d.getFullYear() + ", ") + time;
  }

  function railWhen(at) {
    var d = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(at) ? new Date(at) : null;
    if (!d || isNaN(d.getTime())) { return when(at); }
    function two2(n) { return ("0" + n).slice(-2); }
    var n = new Date(), time = two2(d.getHours()) + ":" + two2(d.getMinutes());
    if (d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate()) { return time; }
    return (S.lang === "en" ? two2(d.getMonth() + 1) + "-" + two2(d.getDate()) + " " : two2(d.getDate()) + "." + two2(d.getMonth() + 1) + ", ") + time;
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
      // a row with a `value` is a pair: the name and, at the right, what it stands at; its attention colours the value
      var value = str(it.value, 80);
      if (value) {
        li.classList.add("gpm-item-pair");
        li.appendChild(el("span", "gpm-item-title", it.title));
        if (str(it.product, 64) && !(info && info.header && it.product === info.product)) { li.appendChild(view.chip(it.product)); }
        var val = el("span", "gpm-item-value" + (level && level !== "ok" ? " gpm-ink-" + level : ""));
        if (level && level !== "ok") { val.appendChild(el("span", "gpm-vh", labelOf(level) + ": ")); }
        val.appendChild(document.createTextNode(value));
        li.appendChild(val);
        if (str(it.note, 300)) { li.appendChild(el("span", "gpm-note gpm-item-pair-note", it.note)); }
        ul.appendChild(li);
        return;
      }
      if (level) { li.appendChild(mark(level)); }
      // the card's own header already names the product: the row says it only when it is another one (or there is no header)
      if (str(it.product, 64) && !(info && info.header && it.product === info.product)) { li.appendChild(view.chip(it.product)); }
      if (withDate && str(it.at, 40)) {
        li.classList.add("gpm-item-timed");
        li.appendChild(el("span", "gpm-at", info && info.rail ? railWhen(it.at) : when(it.at)));
      }
      li.appendChild(el("span", "gpm-item-title", it.title));
      if (str(it.note, 300)) { li.appendChild(el("span", "gpm-note", it.note)); }
      ul.appendChild(li);
    });
    if (!str(data.note, 300)) { return ul; }
    var box = el("div", "gpm-list-wrap");
    box.appendChild(ul);
    box.appendChild(el("p", "gpm-source", data.note));
    return box;
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

  // a number as it is read: from five digits on, the thousands stand apart (216 766)
  function grouped(n) {
    var m = /^(-?)(\d{5,})(\.\d+)?$/.exec(String(n));
    if (!m) { return String(n); }
    return m[1] + m[2].replace(/\B(?=(\d{3})+$)/g, S.lang === "en" ? "," : "\u00a0") + (m[3] || "");
  }
  // one number; with a `title` it is a band that names a goal, and stands even while the goal has no value yet
  function number(data, view, info) {
    var value = num(data.value);
    var title = str(data.title, 200), note = str(data.note, 300);
    if (value === null && !title) { return null; }
    var box = el("div", "gpm-number" + (title ? " gpm-goal" : ""));
    if (title && info && info.band) {
      var top = el("p", "gpm-goal-head");
      if (info.chip && str(info.product, 64)) { top.appendChild(view.chip(info.product)); }
      top.appendChild(el("span", "gpm-goal-label", S.t.goal));
      box.appendChild(top);
    }
    if (title) { box.appendChild(el("p", "gpm-goal-title", title)); }
    if (value === null) {
      if (note) { box.appendChild(el("p", "gpm-num-note", note)); }
      if (info && info.ask) { box.classList.add("gpm-goal-ask"); box.appendChild(info.ask); }
      return box;
    }
    box.appendChild(el("span", "gpm-num-value", grouped(value)));
    if (str(data.unit, 24)) { box.appendChild(el("span", "gpm-num-unit", data.unit)); }
    if (str(data.label, 80)) { box.appendChild(el("span", "gpm-num-label", data.label)); }
    var delta = num(data.delta);
    if (delta !== null) {
      box.appendChild(el("span", "gpm-num-delta", (delta > 0 ? "+" : "") + delta));
    }
    var trend = (Array.isArray(data.trend) ? data.trend : []).filter(function (v) { return num(v) !== null; });
    if (trend.length >= 2) { box.appendChild(sparkline(trend)); }
    if (note) { box.appendChild(el("p", "gpm-num-note", note)); }
    return box;
  }

  // a stage is `warn` at (value - baseline) / baseline <= -warning and `crit` at <= -critical (meta.thresholds)
  function stageLevel(value, baseline, th) {
    if (baseline === null || baseline <= 0) { return null; }
    var drop = (value - baseline) / baseline;
    return drop <= -th.critical ? "crit" : drop <= -th.warning ? "warn" : "ok";
  }

  function chart(data, view, info) {
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
      if (str(s.id, 64) && info && str(info.id, 200)) { decorate("stage", head, info.id + "|" + s.id); }
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
  S.onDecorate = onDecorate;
  S.decorate = decorate;
  S.productChip = productChip;
  S.mark = mark;
  S.shape = shape;
  S.productSwitch = productSwitch;
  // What the window's menu and tray need of the modules: the product and the tab shown, a way to open a tab and to hear
  // of a change (the modules part below fills them in).
  var viewFns = [];
  S.view = function () { return { product: "", tab: null }; };
  S.openTab = function () { return false; };
  S.onView = function (fn) { if (typeof fn === "function") { viewFns.push(fn); } };
  function viewChanged() { viewFns.slice().forEach(function (f) { try { f(); } catch (e) { /* one listener does not stop the others */ } }); }
  var HAS_MODULES = "gpm-has-modules";      // on <html> while the modules are shown: the host's own page colour must not show under them
  var RAIL = "gpm-layout-rail";             // on <html> while the modules are shown and the profile asks for the side rail

  // How many rows of a module ask for attention (warn or crit), for the product shown: the rows of its tables, lists and
  // feeds in the main column. A side column repeats what other modules hold, so it is not counted.
  function attentionCount(m, snap, view) {
    var n = 0;
    m.blocks.forEach(function (b) {
      if (b.bad || b.aside || SOURCES[b.source] || ["table", "list", "feed"].indexOf(b.block) < 0) { return; }
      docsOf(snap, b.source).forEach(function (d) {
        if (view.filter !== "" && groupKey(snap.meta, d.sec.product) !== view.filter) { return; }
        var rows = b.block === "table" ? d.sec.data.rows : d.sec.data.items;
        (Array.isArray(rows) ? rows : []).slice(0, MAX_ROWS).forEach(function (r) {
          if (!isObj(r) || (str(r.product, 64) && !view.shows(r.product))) { return; }
          var level = attention(r.attention);
          if (level === "warn" || level === "crit") { n++; }
        });
      });
    });
    return n;
  }

  function plural(n) {
    try { return new Intl.PluralRules(S.lang === "en" ? "en" : "uk").select(n); } catch (e) { return n === 1 ? "one" : "other"; }
  }
  // «Одна річ чекає…», «Є два сигнали.», «7 речей чекає…»: a small number is said as a word where the language has one
  function counted(n, small, one, few, many) {
    var form = plural(n);
    return (Array.isArray(small) && small[n] ? small[n] : String(n)) + (form === "one" ? one : form === "few" ? few : many);
  }
  // the documents of a source for the product shown, in the order of meta.products, «Без продукту» last
  function visibleDocs(snap, source, view) {
    var order = snap.meta.products.map(function (p) { return p.id; }).concat([NONE]);
    return docsOf(snap, source).filter(function (d) {
      return view.filter === "" || groupKey(snap.meta, d.sec.product) === view.filter;
    }).sort(function (x, y) {
      return order.indexOf(groupKey(snap.meta, x.sec.product)) - order.indexOf(groupKey(snap.meta, y.sec.product));
    });
  }
  // How many rows wait in the home module's feed, or null when no document of it counts: a document that says in its
  // own words why it is empty (`empty`, no rows) is not a count of zero.
  function waitingCount(home, snap, view) {
    var feedBlock = home ? home.blocks.filter(function (b) { return !b.bad && !b.aside && b.block === "feed" && !SOURCES[b.source]; })[0] : null;
    if (!feedBlock) { return null; }
    var docs = visibleDocs(snap, feedBlock.source, view).filter(function (d) {
      return !(str(d.sec.data.empty, 300) && !(Array.isArray(d.sec.data.items) && d.sec.data.items.length));
    });
    if (!docs.length) { return null; }
    var waiting = 0;
    docs.forEach(function (d) {
      (Array.isArray(d.sec.data.items) ? d.sec.data.items : []).slice(0, MAX_ITEMS).forEach(function (it) {
        if (isObj(it) && str(it.title, 300) && (!str(it.product, 64) || view.shows(it.product))) { waiting++; }
      });
    });
    return waiting;
  }
  // the rows of the first block of the home module's side column that ask for attention, or null when it has none.
  // `where` (an option) collects the modules those rows name in `module`, in the order met; null in it marks a row that names none.
  function signalCount(home, snap, view, where) {
    var blocks = home ? home.blocks.filter(function (b) { return !b.bad && b.aside && ROWS.indexOf(b.block) >= 0 && !SOURCES[b.source]; }).slice(0, 1) : [];
    if (!blocks.length) { return null; }
    var n = 0;
    blocks.forEach(function (b) {
      visibleDocs(snap, b.source, view).forEach(function (d) {
        var rows = b.block === "table" ? d.sec.data.rows : d.sec.data.items;
        (Array.isArray(rows) ? rows : []).slice(0, MAX_ROWS).forEach(function (r) {
          if (!isObj(r) || (str(r.product, 64) && !view.shows(r.product))) { return; }
          var level = attention(r.attention);
          if (level === "warn" || level === "crit") {
            n++;
            var at = typeof r.module === "string" && MODULE_ID.test(r.module) ? r.module : null;
            if (where && where.indexOf(at) < 0) { where.push(at); }
          }
        });
      });
    });
    return n;
  }
  // «у метриках і в напрямках»: the modules the signals stand in, each said by its own `where` of the profile; "" unless
  // every signal names a module that is shown and has that word
  function wherePhrase(ids, mods) {
    var names = [], t = S.t;
    for (var i = 0; i < ids.length; i++) {
      var m = mods.filter(function (x) { return x.id === ids[i]; })[0];
      if (!ids[i] || !m || !m.where) { return ""; }
      names.push(m.where);
    }
    if (!names.length) { return ""; }
    return names.map(function (w, j) { return (j === 0 ? t.inFirst : j === names.length - 1 ? t.inLast : t.inNext) + w; }).join("");
  }
  var CLOCK = /^([01]\d|2[0-3]):([0-5]\d)$/;
  function clockMin(v) { var m = typeof v === "string" ? CLOCK.exec(v) : null; return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : null; }
  function two(n) { return ("0" + n).slice(-2); }
  // what the home module's day says of this minute: {focus, to} for what goes on, {from} for what comes next, or null.
  // Only a day made for today counts, by this window's own clock; no title of a row is read.
  function dayNow(home, snap, view) {
    var block = home ? home.blocks.filter(function (b) { return !b.bad && b.block === "day" && !SOURCES[b.source]; })[0] : null;
    if (!block) { return null; }
    var d = new Date();
    var today = d.getFullYear() + "-" + two(d.getMonth() + 1) + "-" + two(d.getDate()), now = d.getHours() * 60 + d.getMinutes();
    var current = null, next = null;
    visibleDocs(snap, block.source, view).forEach(function (doc) {
      if (doc.sec.data.date !== today) { return; }
      (Array.isArray(doc.sec.data.items) ? doc.sec.data.items : []).slice(0, MAX_ITEMS).forEach(function (it) {
        if (!isObj(it) || (str(it.product, 64) && !view.shows(it.product))) { return; }
        var from = clockMin(it.from), to = clockMin(it.to);
        if (from === null || to === null || to <= from) { return; }
        if (from <= now && now < to) { if (!current || to > current.to) { current = { focus: it.kind === "focus", to: to }; } }
        else if (from > now && (!next || from < next.from)) { next = { from: from }; }
      });
    });
    return current || next;
  }

  // The source `@summary`: the app's state in a sentence, counted from what the modules show for the product picked —
  // how many rows wait in the home module's feed (said only when that feed has a document that counts), how many rows
  // of its side column ask for attention (without a side column: which other modules have such rows), and what its day
  // says of this minute. Nothing in it comes from a document's text.
  function summary(view) {
    var mods = view.modules || [], snap = view.snap, t = S.t;
    if (!snap || !snap.meta) { return null; }
    var parts = [], asking = [];
    var home = mods.filter(function (m) { return m.home; })[0] || null;
    var waiting = waitingCount(home, snap, view);
    if (waiting !== null) {
      parts.push(waiting === 0 ? t.nothingWaits : counted(waiting, t.small, t.waitsOne, t.waitsFew, t.waitsMany));
    }
    var named = [], signals = signalCount(home, snap, view, named);
    if (signals !== null) {
      var said = signals === 0 ? t.noSignals : t.thereIs + counted(signals, t.smallSignal, t.signalsOne, t.signalsFew, t.signalsMany);
      var places = signals === 0 ? "" : wherePhrase(named, mods);
      parts.push(places ? said.replace(/\.$/, "") + ": " + places + "." : said);
    } else {
      mods.forEach(function (m) {
        if (m === home) { return; }
        var n = attentionCount(m, snap, view);
        if (n > 0) { asking.push(m.title + " (" + n + ")"); }
      });
      parts.push(asking.length ? t.askAttention + asking.join(", ") + "." : t.nothingAsks);
    }
    var at = dayNow(home, snap, view);
    if (at) {
      parts.push(at.from === undefined ? (at.focus ? t.nowFocus : t.nowMeeting) + two(Math.floor(at.to / 60)) + ":" + two(at.to % 60) + "."
        : t.nextAt + two(Math.floor(at.from / 60)) + ":" + two(at.from % 60) + ".");
    }
    var box = el("div", "gpm-lead");
    box.appendChild(el("p", "gpm-lead-text", parts.join(" ")));
    return box;
  }
  SOURCES["@summary"] = summary;

  // the day as the rail says it: «Четвер, 26 листопада»
  function today(lang) {
    try {
      var text = new Intl.DateTimeFormat(lang === "en" ? "en-GB" : "uk-UA", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
      return text.charAt(0).toUpperCase() + text.slice(1);
    } catch (e) { return ""; }
  }

  // ---- the owner's config/app ---------------------------------------------------------------------------------------
  // One block entry: {block, source, title} + `bad` when it is not one this page can show. A title is text (a profile's
  // is {uk, en}). `custom` modules come from the owner's document: never `map`, never a source outside the section names.
  function normBlock(raw, custom, lang) {
    var b = isObj(raw) ? raw : {};
    var title = custom ? (b.title === undefined ? null : plainTitle(b.title, null))
      : (isObj(b.title) ? (str(b.title[lang], TITLE_MAX) || null) : null);
    var ok = BLOCK_NAMES.indexOf(b.block) >= 0 && !(custom && b.block === "map")
      && typeof b.source === "string" && (SECTION.test(b.source) || b.source === "@edits" || b.source === "@summary"
        || (!custom && b.block === "list" && (b.source === "@modules" || b.source === "@theme")));
    return { block: ok ? b.block : null, source: ok ? b.source : null, title: title, bad: !ok, aside: ok && b.place === "aside",
      group: ok && !custom && typeof b.group === "string" && GROUP_ID.test(b.group) ? b.group : null,
      ask: ok && !custom ? askOf(b.ask, lang) : null };
  }
  // a text of the profile in the language shown, or null
  function words(o, lang, max) { return (isObj(o) && str(o[lang], max)) || null; }
  // `ask` / `refresh` of the profile -> {label, say, empty}: a button that hands the person a phrase to say to Claude.
  // Both texts are the profile's own, embedded in the page — never a document's.
  function askOf(raw, lang) {
    var label = isObj(raw) ? words(raw.label, lang, 40) : null, say = isObj(raw) ? words(raw.say, lang, 200) : null;
    return label && say ? { label: label, say: say, empty: raw.when === "empty" } : null;
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
    // `counts`: the words the rail says after a module's count, one per plural form — «застиг», «застигли», «застигло»
    var forms = !custom && isObj(raw.counts) && Array.isArray(raw.counts[lang]) ? raw.counts[lang].filter(function (w) { return str(w, 24); }) : [];
    // not a tab: `foot` — the entry at the foot of the rail; `under` — a screen opened from its parent module
    var foot = !custom && raw.foot === true && raw.home !== true;
    var under = !custom && !foot && raw.home !== true && typeof raw.under === "string" && MODULE_ID.test(raw.under) ? raw.under : null;
    return { id: raw.id, title: title, home: !custom && raw.home === true, blocks: blocks, composed: composed && !(short && composed),
      counts: forms.length >= 2 && forms.length <= 3 ? forms : null, foot: foot, under: under,
      where: custom ? null : words(raw.where, lang, 40), about: custom ? null : words(raw.about, lang, 120),
      back: under ? words(raw.back, lang, 40) : null };
  }

  // the document as foreign input -> {modules: [{id, on, order}], custom: [module]} or null
  function cleanConfig(raw) {
    if (!isObj(raw) || (raw.v !== undefined && raw.v !== 1)) { return null; }
    var cfg = { modules: [], custom: [], rawCustom: Array.isArray(raw.custom) ? raw.custom.slice(0, MAX_CUSTOM) : [] };
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
      if (r && r.on === false && !m.foot) { return; }      // the foot module holds the switches: it is never turned off
      var ordered = !!(r && r.order !== null);
      m.pos = ordered ? r.order : i;
      m.ordered = ordered;
      m.index = i;
      out.push(m);
    });
    out.sort(function (a, b) {
      return a.pos - b.pos || (a.ordered === b.ordered ? 0 : a.ordered ? -1 : 1) || a.index - b.index;
    });
    // every module a person can turn on or off, whatever its state: the profile's and the owner's, in their base order
    out.switches = all.filter(function (m) { return !m.foot && !m.under; }).map(function (m) {
      var r = Object.prototype.hasOwnProperty.call(rules, m.id) ? rules[m.id] : null;
      return { id: m.id, title: m.title, about: m.about, home: m.home, on: !(r && r.on === false) };
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
        // a section may say in its own words why it has nothing to show yet
        if (!node && str(d.sec.data.empty, 300)) { node = el("p", "gpm-empty", d.sec.data.empty); }
        if (!node) { return; }
        cards.push({ key: key, node: node, product: d.sec.product });
        dates.push(snap.meta.sections[d.id] || d.sec.made);
      });
      var order = snap.meta.products.map(function (p) { return p.id; }).concat([NONE]);
      cards.sort(function (a, b2) { return order.indexOf(a.key) - order.indexOf(b2.key); });
    }
    if (!cards.length) {
      if (QUIET.indexOf(b.block) >= 0) { return { node: null, dates: dates }; }
      box.appendChild(el("p", "gpm-empty", S.t.empty));
      return { node: box, dates: dates };
    }
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

  // The blocks of a module one under another; a block with `place: aside` stands in a side column beside them. With the
  // side rail the panel names its module itself (the rail's entry is not over it); a `lead` that opens the home module
  // is that module's heading, so its title is kept for a screen reader only.
  function renderModule(m, snap, view, rail) {
    var panel = el("div", "gpm-module" + (m.home ? " gpm-module-home" : ""));
    var dates = [];
    var split = m.blocks.some(function (b) { return b.aside; });
    var main = split ? el("div", "gpm-col-main") : panel, aside = split ? el("aside", "gpm-col-aside") : null;
    var leads = false;
    m.blocks.forEach(function (b, i) {
      var r = renderBlock(b, snap, view);
      dates = dates.concat(r.dates);
      if (!r.node) { return; }
      var sec = el("section", "gpm-block gpm-block-" + (b.block || "none"));
      if (m.composed && b.title) { sec.appendChild(el("h3", "gpm-block-title", b.title)); }
      sec.appendChild(r.node);
      if (i === 0 && b.block === "lead") { leads = true; }
      (b.aside ? aside : main).appendChild(sec);
    });
    if (split) {
      panel.classList.add("gpm-module-split");
      panel.appendChild(main);
      panel.appendChild(aside);
    }
    var fresh = null;
    if (dates.length) {
      var oldest = dates.slice().sort()[0];
      var shown = S.showDate(oldest, S.lang);
      if (shown) { fresh = el("p", "gpm-fresh-module", S.t.freshness + shown); }
    }
    if (!rail) {
      if (fresh) { panel.insertBefore(fresh, panel.firstChild); }
      return panel;
    }
    var box = el("div", "gpm-module-box");
    box.appendChild(el("h2", "gpm-module-title" + (m.home && leads ? " gpm-vh" : ""), m.title));
    box.appendChild(panel);
    if (fresh) { box.appendChild(fresh); }
    return box;
  }

  // ---- the side rail: a module as sections, the products together ----------------------------------------------------
  // a moment said short: the time when it is today, the day and month otherwise
  function shortWhen(at) {
    var d = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(at || "") ? new Date(at) : null;
    if (!d || isNaN(d.getTime())) { var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(at || ""); return m ? (S.lang === "en" ? m[2] + "-" + m[3] : m[3] + "." + m[2]) : ""; }
    var n = new Date();
    if (d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate()) { return two(d.getHours()) + ":" + two(d.getMinutes()); }
    return S.lang === "en" ? two(d.getMonth() + 1) + "-" + two(d.getDate()) : two(d.getDate()) + "." + two(d.getMonth() + 1);
  }
  // what a section says at the right of its heading: the document's own `side`, or its `source` and when it was read
  function sideOf(d, snap) {
    var side = str(d.sec.data.side, 80);
    if (side) { return side; }
    var source = str(d.sec.data.source, 80);
    if (!source) { return ""; }
    var at = shortWhen(snap.meta.sections[d.id] || d.sec.made);
    return at ? source + ", " + at : source;
  }
  function uniq(list) { return list.filter(function (v, i) { return v && list.indexOf(v) === i; }); }
  // The documents of a block of rows as one: a list or a feed always, a table when its documents have the same columns
  // (else null). A row shows the product it names itself; one that names none stands without a label.
  function merged(b, docs) {
    var note = uniq(docs.map(function (d) { return str(d.sec.data.note, 300); })).join(" ");
    var rows = [];
    if (b.block === "table") {
      var keys = function (d) {
        return JSON.stringify((Array.isArray(d.sec.data.columns) ? d.sec.data.columns : []).map(function (c) { return isObj(c) ? c.key : null; }));
      };
      if (docs.some(function (d) { return keys(d) !== keys(docs[0]); })) { return null; }
      docs.forEach(function (d) {
        (Array.isArray(d.sec.data.rows) ? d.sec.data.rows : []).forEach(function (r) { rows.push(r); });
      });
      return { columns: docs[0].sec.data.columns, rows: rows, note: note };
    }
    docs.forEach(function (d) {
      (Array.isArray(d.sec.data.items) ? d.sec.data.items : []).forEach(function (r) { rows.push(r); });
    });
    return { items: rows, note: note };
  }
  function railSection(title, side, product, view, cls) {
    var sec = el("section", "gpm-block " + cls);
    if (!title) { return sec; }
    var head = el("div", "gpm-block-head");
    head.appendChild(el("h3", "gpm-block-title", title));
    if (product || side) {
      var right = el("span", "gpm-block-side");
      if (product) { right.appendChild(view.chip(product)); }
      if (side) { right.appendChild(el("span", "gpm-block-side-text", side)); }
      head.appendChild(right);
    }
    sec.appendChild(head);
    return sec;
  }
  function infoOf(d, more) {
    var info = { id: d.id, product: d.sec.product, section: d.sec.section, made: d.sec.made, header: true, rail: true };
    Object.keys(more || {}).forEach(function (k) { info[k] = more[k]; });
    return info;
  }
  // A button that hands the person a phrase to say to Claude. A page cannot start Claude's run, so the click copies the
  // phrase and says where it goes; without a clipboard it says the phrase. Both texts are the profile's own.
  function sayButton(ask, cls) {
    var box = el("div", "gpm-ask" + (cls ? " " + cls : ""));
    var b = el("button", "gpm-btn gpm-ask-btn", ask.label);
    b.type = "button";
    var note = el("p", "gpm-ask-note");
    note.hidden = true;
    note.setAttribute("role", "status");
    function tell(copied) {
      note.textContent = (copied ? S.t.saidCopied : S.t.saidPlain).replace("%s", function () { return ask.say; });
      note.hidden = false;
    }
    b.addEventListener("click", function () {
      try { navigator.clipboard.writeText(ask.say).then(function () { tell(true); }, function () { tell(false); }); }
      catch (e) { tell(false); }
    });
    box.appendChild(b);
    box.appendChild(note);
    return box;
  }
  S.sayButton = sayButton;
  // true while none of the documents has a value or a row to show
  function nothingIn(docs) {
    return docs.every(function (d) {
      var x = d.sec.data;
      return num(x.value) === null && !(Array.isArray(x.items) && x.items.length) && !(Array.isArray(x.rows) && x.rows.length);
    });
  }
  // The source `@modules`: a switch per module a person can turn on or off (the owner's config/app, written by the part
  // through view.hooks); the home module is always on. -> {node, side}
  function modulesList(view) {
    var hooks = view.hooks || {}, list = el("ul", "gpm-list gpm-switches"), on = 0;
    (view.switches || []).forEach(function (m) {
      var li = el("li", "gpm-item gpm-switch-row");
      var text = el("span", "gpm-switch-text");
      var name = el("span", "gpm-item-title", m.title);
      name.id = "gpm-switch-" + m.id;
      text.appendChild(name);
      if (m.about) { text.appendChild(el("span", "gpm-note", m.about)); }
      li.appendChild(text);
      if (m.on || m.home) { on++; }
      if (m.home) { li.appendChild(el("span", "gpm-switch-fixed", S.t.alwaysOn)); }
      else {
        var sw = el("button", "gpm-switch");
        sw.type = "button";
        sw.setAttribute("role", "switch");
        sw.setAttribute("aria-checked", m.on ? "true" : "false");
        sw.setAttribute("aria-labelledby", name.id);
        sw.setAttribute("data-module", m.id);
        var knob = el("span", "gpm-switch-knob");
        knob.setAttribute("aria-hidden", "true");
        sw.appendChild(knob);
        // never disabled for the time of a write: the switch keeps the focus, and a second click then is not heard
        sw.disabled = hooks.canWrite === false || typeof hooks.setModule !== "function";
        if (hooks.saving === true) { sw.setAttribute("aria-busy", "true"); }
        sw.addEventListener("click", function () { hooks.setModule(m.id, !m.on); });
        li.appendChild(sw);
      }
      list.appendChild(li);
    });
    var box = el("div", "gpm-block-body");
    box.appendChild(list);
    if (hooks.note) { var said = el("p", "gpm-ask-note", hooks.note); said.setAttribute("role", "status"); box.appendChild(said); }
    return { node: box, side: on + S.t.turnedOn };
  }
  SOURCES["@modules"] = function (view) { return modulesList(view).node; };
  // The source `@theme`: the shell's own theme switch, moved out of the header into this block (one element, never copied)
  var themeEl = null;
  function themeBox() {
    if (!themeEl) { themeEl = document.querySelector(".gpm-theme"); }
    var box = el("div", "gpm-block-body gpm-theme-box");
    if (themeEl) { box.appendChild(themeEl); }
    return box;
  }
  SOURCES["@theme"] = themeBox;
  function hasThemeBlock(profile) {
    return (Array.isArray(profile.modules) ? profile.modules : []).some(function (m) {
      return isObj(m) && Array.isArray(m.blocks) && m.blocks.some(function (b) { return isObj(b) && b.source === "@theme"; });
    });
  }

  // One block -> its section, or none: a block whose documents show nothing and say nothing of why takes no room.
  function blockSections(b, snap, view, chips) {
    var cls = "gpm-block-" + (b.block || "none"), sec;
    if (b.bad) {
      sec = railSection(b.title, "", null, view, cls);
      sec.appendChild(el("p", "gpm-unsupported", S.t.unsupported));
      return [sec];
    }
    if (b.source === "@modules") {
      var sw = modulesList(view);
      sec = railSection(b.title, sw.side, null, view, cls + " gpm-block-switches");
      sec.appendChild(sw.node);
      return [sec];
    }
    if (SOURCES[b.source] || typeof RENDER[b.block].all === "function") {
      var r = renderBlock(b, snap, view);
      if (!r.node) { return []; }
      sec = railSection(b.title, "", null, view, cls);
      sec.appendChild(r.node);
      return [sec];
    }
    var docs = visibleDocs(snap, b.source, view);
    if (!docs.length) { return []; }
    if (b.block === "lead") {         // the sentences of the products shown, as one introduction
      var texts = uniq(docs.map(function (d) { return str(d.sec.data.text, 400); }));
      if (!texts.length) { return []; }
      sec = el("section", "gpm-block " + cls);
      var lead = el("div", "gpm-lead");
      lead.appendChild(el("p", "gpm-lead-text", texts.join(" ")));
      sec.appendChild(lead);
      return [sec];
    }
    var sides = uniq(docs.map(function (d) { return sideOf(d, snap); }));
    var side = sides.length === 1 && docs.every(function (d) { return sideOf(d, snap) === sides[0]; }) ? sides[0] : "";
    var title = (docs.length === 1 && str(docs[0].sec.data.heading, TITLE_MAX)) || b.title;
    var body = el("div", "gpm-block-body");
    var data = ROWS.indexOf(b.block) >= 0 ? merged(b, docs) : null;
    if (data) {
      var whole = RENDER[b.block](data, view, { header: view.filter !== "", product: view.filter, rail: true });
      if (whole) { body.appendChild(whole); }
      else {
        var why = uniq(docs.map(function (d) { return str(d.sec.data.empty, 300); }));
        if (!why.length) { return []; }
        why.forEach(function (w) { body.appendChild(el("p", "gpm-empty", w)); });
      }
      sec = railSection(title, side, null, view, cls);
      sec.appendChild(body);
      if (b.ask && (!b.ask.empty || nothingIn(docs))) { sec.appendChild(sayButton(b.ask)); }
      return [sec];
    }
    var cards = [], wants = b.ask && (!b.ask.empty || nothingIn(docs)), inBand = false;
    docs.forEach(function (d) {
      // a goal's band with no value yet takes the ask beside its words
      var beside = wants && !inBand && b.block === "number" && !title && num(d.sec.data.value) === null && str(d.sec.data.title, 200);
      var extra = { band: !title, chip: chips && !title };
      if (beside) { extra.ask = sayButton(b.ask, "gpm-ask-beside"); inBand = true; }
      var node = RENDER[b.block](d.sec.data, view, infoOf(d, extra)), told = false;
      if (!node && str(d.sec.data.empty, 300)) { node = el("p", "gpm-empty", d.sec.data.empty); told = true; }
      if (node) { cards.push({ node: node, product: d.sec.product, told: told }); }
    });
    if (!cards.length) { return []; }
    cards.forEach(function (c) {
      var card = el("div", "gpm-card");
      card.setAttribute("data-product", groupKey(snap.meta, c.product));
      if (chips && title && cards.length > 1) {
        var head = el("div", "gpm-card-head");
        head.appendChild(view.chip(c.product));
        card.appendChild(head);
      }
      card.appendChild(c.node);
      body.appendChild(card);
    });
    // one card: the heading names its product — not over a day (it is the person's) or over words that only explain
    sec = railSection(title, side, chips && title && cards.length === 1 && b.block !== "day" && !cards[0].told ? cards[0].product : null, view, cls);
    sec.appendChild(body);
    if (wants && !inBand) { sec.appendChild(sayButton(b.ask)); }
    return [sec];
  }
  // The blocks that share a `group` -> one section per product: its heading (the document's own `heading`, else the first
  // block's title), then the blocks side by side — a number and a chart beside each other, a table under them. A chart
  // beside a table of the same numbers does not fold its own under itself.
  function groupSections(u, snap, view, chips) {
    var per = {};
    u.blocks.forEach(function (b) {
      if (b.bad || SOURCES[b.source] || typeof RENDER[b.block].all === "function") { return; }
      visibleDocs(snap, b.source, view).forEach(function (d) {
        var key = groupKey(snap.meta, d.sec.product);
        if (!Object.prototype.hasOwnProperty.call(per, key)) { per[key] = []; }
        per[key].push({ b: b, d: d });
      });
    });
    var order = snap.meta.products.map(function (p) { return p.id; }).concat([NONE, ""]);
    var out = [];
    Object.keys(per).sort(function (x, y) { return order.indexOf(x) - order.indexOf(y); }).forEach(function (key) {
      var entries = per[key];
      var hasTable = entries.some(function (e) { return e.b.block === "table"; });
      var parts = [];
      entries.forEach(function (e) {
        var node = RENDER[e.b.block](e.d.sec.data, view, infoOf(e.d, { twin: !hasTable }));
        if (!node && str(e.d.sec.data.empty, 300)) { node = el("p", "gpm-empty", e.d.sec.data.empty); }
        if (node) { parts.push({ node: node, e: e }); }
      });
      if (!parts.length) { return; }
      var title = "", side = "";
      parts.forEach(function (p) {
        if (!title) { title = str(p.e.d.sec.data.heading, TITLE_MAX) || ""; }
        if (!side) { side = sideOf(p.e.d, snap); }
      });
      if (!title) { u.blocks.forEach(function (b) { if (!title && b.title) { title = b.title; } }); }
      var sec = railSection(title, side, chips && key !== "" ? parts[0].e.d.sec.product : null, view, "gpm-block-group");
      var row = el("div", "gpm-group");
      parts.forEach(function (p) {
        var part = el("div", "gpm-group-part gpm-group-" + p.e.b.block);
        part.appendChild(p.node);
        row.appendChild(part);
      });
      sec.appendChild(row);
      out.push(sec);
    });
    return out;
  }
  function renderRail(m, snap, view) {
    var panel = el("div", "gpm-module gpm-module-rail" + (m.home ? " gpm-module-home" : "") + (m.foot ? " gpm-module-foot" : "") + (m.under ? " gpm-module-under" : ""));
    var split = m.blocks.some(function (b) { return b.aside; });
    var main = split ? el("div", "gpm-col-main") : panel, aside = split ? el("aside", "gpm-col-aside") : null;
    var chips = snap.meta.products.length > 1 && view.filter === "";
    var units = [], leads = false, shown = 0;
    m.blocks.forEach(function (b, i) {
      var last = units[units.length - 1];
      if (b.group && last && last.group === b.group && last.aside === b.aside) { last.blocks.push(b); }
      else { units.push({ group: b.group, aside: b.aside, blocks: [b], first: i === 0 }); }
    });
    units.forEach(function (u) {
      var nodes = u.group ? groupSections(u, snap, view, chips) : blockSections(u.blocks[0], snap, view, chips);
      nodes.forEach(function (n) { (u.aside ? aside : main).appendChild(n); shown++; });
      if (u.first && u.blocks[0].block === "lead" && nodes.length) { leads = true; }
    });
    if (!shown) { main.appendChild(el("p", "gpm-empty", S.t.empty)); }
    // the screens that stand under this module: a row each, opened by a click
    var hooks = view.hooks || {};
    var kids = (view.modules || []).filter(function (x) { return x.under === m.id; });
    if (kids.length && typeof hooks.open === "function") {
      var more = railSection(S.t.more, "", null, view, "gpm-block-more");
      var ul = el("ul", "gpm-list");
      kids.forEach(function (k) {
        var li = el("li", "gpm-item gpm-more-row");
        var go = el("button", "gpm-more-link", screenHeading(k, snap, view) || k.title);
        go.type = "button";
        go.setAttribute("data-open", k.id);
        go.addEventListener("click", function () { hooks.open(k.id); });
        li.appendChild(go);
        ul.appendChild(li);
      });
      more.appendChild(ul);
      main.appendChild(more);
    }
    if (split) {
      panel.classList.add("gpm-module-split");
      panel.appendChild(main);
      panel.appendChild(aside);
    }
    var box = el("div", "gpm-module-box");
    if (m.under && typeof hooks.open === "function") {
      var parent = (view.modules || []).filter(function (x) { return x.id === m.under; })[0];
      var back = el("button", "gpm-back", m.back || S.t.backTo + (parent ? parent.title : ""));
      back.type = "button";
      back.setAttribute("data-open", m.under);
      back.addEventListener("click", function () { hooks.open(m.under); });
      box.appendChild(back);
    }
    box.appendChild(el("h2", "gpm-module-title" + (m.home && leads ? " gpm-vh" : ""), (m.under && screenHeading(m, snap, view)) || m.title));
    box.appendChild(panel);
    return box;
  }
  // what a screen under a module shows: the `heading` of the first document of its first block, when it has one
  function screenHeading(m, snap, view) {
    var b = m.blocks[0];
    if (!b || b.bad || SOURCES[b.source]) { return ""; }
    var docs = visibleDocs(snap, b.source, view);
    for (var i = 0; i < docs.length; i++) { var h = str(docs[i].sec.data.heading, TITLE_MAX); if (h) { return h; } }
    return "";
  }

  // renderModules(profile, config, data, product, active) -> {modules, active, tabs, panel}: the tabs and the panel of the
  // open module as elements; `product` is "" for «Усі» or one product id. Tab clicks are wired by the part below.
  function renderModules(profile, config, data, product, active, lang, hooks) {
    var mods = moduleList(profile, config, lang);
    railMode = profile.layout === "rail";
    // a tab: every module but the screens under another one and, in the rail, the module of its foot
    var tabs = mods.filter(function (m) { return !m.under && !(railMode && m.foot); });
    var open = null;
    mods.forEach(function (m) { if (m.id === active) { open = m; } });
    // a screen under a module is reached only through that module (the rail draws the way)
    if (open && open.under && !(railMode && tabs.some(function (m) { return m.id === open.under; }))) { open = null; }
    if (!open) { open = tabs.filter(function (m) { return m.home; })[0] || tabs[0] || null; }
    var meta = data.meta;
    function viewOf(filter) {
      return {
        meta: meta, filter: filter, modules: mods, snap: data, hooks: hooks || {}, switches: mods.switches,
        chip: function (id) { return meta.products.length ? productChip(id, meta) : document.createTextNode(""); },
        shows: function (id) { return filter === "" || groupKey(meta, id) === filter; }
      };
    }
    var view = viewOf(product);
    // the foot module is about the app, not about a product: it shows every product whatever the switch says
    var shown = open && open.foot && railMode ? viewOf("") : view;
    return { modules: mods, tabs: tabs, active: open ? open.id : null, selected: open ? open.under || open.id : null, view: view,
      foot: railMode ? mods.filter(function (m) { return m.foot; })[0] || null : null,
      panel: !open ? null : profile.layout === "rail" ? renderRail(open, data, shown) : renderModule(open, data, shown, false) };
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
    var rail = profile.layout === "rail", navEl = null, dayEl = null, footEl = null, footLink = null;
    var ownTheme = hasThemeBlock(profile), refresh = askOf(profile.refresh, ctx.lang);
    var refreshNote = isObj(profile.refresh) && typeof profile.refresh.source === "string" && SECTION.test(profile.refresh.source) ? profile.refresh.source : null;
    // the switches of the modules write the owner's config/app: {v, modules: [{id, on, order?}], custom} — the rules as
    // they were with one of them changed, the custom modules as they were read
    var dbRef = null, hooks = { canWrite: null, saving: false, note: "", setModule: setModule, open: openScreen };
    function setModule(id, on) {
      if (!dbRef || hooks.saving || hooks.canWrite === false || !MODULE_ID.test(id)) { return; }
      var rules = [], found = false;
      (config ? config.modules : []).forEach(function (r) {
        var rule = { id: r.id, on: r.id === id ? on === true : r.on };
        if (r.order !== null) { rule.order = r.order; }
        if (r.id === id) { found = true; }
        rules.push(rule);
      });
      if (!found) { rules.push({ id: id, on: on === true }); }
      var doc = { v: 1, modules: rules.slice(0, MAX_RULES), custom: config ? config.rawCustom : [] };
      hooks.saving = true;
      hooks.note = "";
      safePaint();
      Promise.resolve().then(function () { return dbRef.collection("config").doc("app").set(doc); }).then(function () {
        hooks.saving = false;
        config = cleanConfig(doc) || config;
        safePaint();
      }, function (e) {
        hooks.saving = false;
        // the database refuses a write below the rule's level the same way as a malformed one: the switches turn read-only
        if (e && e.code === "invalid_argument") { hooks.canWrite = false; hooks.note = ctx.t.ownerOnly; }
        else { hooks.note = ctx.t.notSaved; }
        safePaint();
      });
    }
    function openScreen(id) {
      pickTab(id);
      var h = root.querySelector(".gpm-module-title");
      if (h) { h.tabIndex = -1; try { h.focus(); } catch (e) { /* nothing to focus */ } }
    }

    var shownTab = null;
    S.view = function () { return { product: product || "", tab: shownTab }; };
    S.openTab = function (id) { pickTab(id); return shownTab === id; };

    function showPage() {
      document.documentElement.classList.remove(HAS_MODULES);
      document.documentElement.classList.remove(RAIL);
      if (navEl && navEl.parentNode) { navEl.parentNode.removeChild(navEl); }
      if (dayEl && dayEl.parentNode) { dayEl.parentNode.removeChild(dayEl); }
      if (footEl && footEl.parentNode) {
        var line = footEl.querySelector(".gpm-fresh");
        if (line) { footEl.parentNode.insertBefore(line, footEl); }       // the date's line goes back where the shell put it
        footEl.parentNode.removeChild(footEl);
      }
      navEl = null;
      dayEl = null;
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
        || (navEl && navEl.contains(document.activeElement)) ? document.activeElement : null;
      var focusKey = focus ? (focus.getAttribute("data-tab") !== null ? "tab:" + focus.getAttribute("data-tab")
        : focus.getAttribute("data-product") !== null ? "product:" + focus.getAttribute("data-product")
        : focus.getAttribute("data-module") !== null ? "module:" + focus.getAttribute("data-module") : null) : null;
      if (product === null) { product = stored(STORE_PRODUCT) || ""; }
      if (product !== "" && productIndex(snap.meta, product) < 0) { product = ""; }
      var r = renderModules(profile, config, snap, product, active, ctx.lang, hooks);
      // the theme switch of a profile that shows it in a block (`@theme`) leaves the header: it stands in that block only
      if (ownTheme) {
        var inHeader = ctx.header.querySelector(".gpm-theme");
        if (inHeader) { themeEl = inHeader; inHeader.parentNode.removeChild(inHeader); }
      }

      var tabs = el("div", "gpm-tabs");
      tabs.setAttribute("role", "tablist");
      tabs.setAttribute("aria-label", ctx.t.modules);
      if (rail) { tabs.setAttribute("aria-orientation", "vertical"); }
      r.tabs.forEach(function (m) {
        var b = el("button", "gpm-tab", rail ? null : m.title);
        if (rail) {         // the rail's entry: the module, and how many of its rows ask for attention
          b.appendChild(el("span", "gpm-tab-title", m.title));
          var waits = m.home ? waitingCount(m, snap, r.view) : null;
          var asking = m.home ? 0 : attentionCount(m, snap, r.view);
          if (waits) {              // the home module: how many rows wait, said plainly
            b.appendChild(el("span", "gpm-tab-count gpm-tab-count-own", String(waits)));
          } else if (asking > 0) {
            var count = el("span", "gpm-tab-count");
            if (m.counts) {         // the module's own word for it: «1 застиг»
              var form = plural(asking);
              count.appendChild(document.createTextNode(asking + " " + (m.counts.length === 3 ? m.counts[form === "one" ? 0 : form === "few" ? 1 : 2] : m.counts[form === "one" ? 0 : 1])));
            } else {
              var dot = el("span", "gpm-mark");
              dot.setAttribute("aria-hidden", "true");
              count.appendChild(dot);
              count.appendChild(document.createTextNode(String(asking)));
              count.appendChild(el("span", "gpm-vh", " " + ctx.t.needAttention));
            }
            b.appendChild(count);
          }
        }
        b.type = "button";
        b.id = "gpm-tab-" + m.id;
        b.setAttribute("role", "tab");
        b.setAttribute("data-tab", m.id);
        b.setAttribute("aria-selected", m.id === r.selected ? "true" : "false");
        b.setAttribute("aria-controls", "gpm-panel");
        b.tabIndex = m.id === r.selected || (r.foot && r.selected === r.foot.id && m === r.tabs[0]) ? 0 : -1;
        b.addEventListener("click", function () { pickTab(m.id); });
        tabs.appendChild(b);
      });
      tabs.addEventListener("keydown", function (e) {
        var ids = r.tabs.map(function (m) { return m.id; });
        var at = Math.max(ids.indexOf(r.selected), 0), to = -1;
        if (e.key === "ArrowRight" || (rail && e.key === "ArrowDown")) { to = (at + 1) % ids.length; }
        else if (e.key === "ArrowLeft" || (rail && e.key === "ArrowUp")) { to = (at - 1 + ids.length) % ids.length; }
        else if (e.key === "Home") { to = 0; }
        else if (e.key === "End") { to = ids.length - 1; }
        if (to >= 0 && ids.length) { e.preventDefault(); focusKey = "tab:" + ids[to]; pickTab(ids[to]); refocus(); }
      });

      var body = el("div", "gpm-panel");
      body.id = "gpm-panel";
      body.setAttribute("role", "tabpanel");
      if (r.selected) { body.setAttribute("aria-labelledby", r.foot && r.selected === r.foot.id ? "gpm-foot-link" : "gpm-tab-" + r.selected); }
      body.appendChild(r.panel || el("p", "gpm-empty", ctx.t.noModules));

      while (root.firstChild) { root.removeChild(root.firstChild); }
      if (navEl && navEl.parentNode) { navEl.parentNode.removeChild(navEl); }
      navEl = null;
      if (!rail) { root.appendChild(tabs); }
      root.appendChild(body);

      if (switchEl && switchEl.parentNode) { switchEl.parentNode.removeChild(switchEl); }
      switchEl = productSwitch(snap.meta, product, pickProduct);
      // the side rail: the header is the rail — the title and the day, the products, the modules, then whatever else it holds
      var after = rail ? ctx.header.querySelector(".gpm-title") : null;
      var before = rail ? (after ? after.nextSibling : ctx.header.firstChild) : ctx.actions;
      if (rail) {
        if (!dayEl) { var words = today(ctx.lang); if (words) { dayEl = el("span", "gpm-today", words); } }
        if (dayEl && dayEl.parentNode !== ctx.header) { ctx.header.insertBefore(dayEl, before); }
        if (dayEl) { before = dayEl.nextSibling; }
      }
      if (switchEl) { ctx.header.insertBefore(switchEl, before); }
      if (rail) { navEl = tabs; ctx.header.insertBefore(tabs, switchEl ? switchEl.nextSibling : before); }

      if (rail) {
        var fresh = ctx.header.querySelector(".gpm-fresh"), made = shortWhen(snap.meta.made);
        var day = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(snap.meta.made) ? new Date(snap.meta.made) : null;
        if (fresh && made && day && !isNaN(day.getTime())) {
          var clock = two(day.getHours()) + ":" + two(day.getMinutes());
          // the run's own sentence on when the next data comes (the section the profile's `refresh` names), every product's
          var next = refreshNote ? uniq(docsOf(snap, refreshNote).map(function (d) { return str(d.sec.data.text, 200); })).join(" ") : "";
          fresh.textContent = ctx.t.dataFrom + (made === clock ? clock : made + ", " + clock) + "." + (next ? " " + next : "");
        }
        // the foot of the rail: the ask for fresh data, then the foot module (the settings). Built once, so a line the
        // button has said stays through a repaint.
        if (!footEl) {
          footEl = el("div", "gpm-foot");
          if (refresh) { footEl.appendChild(sayButton(refresh, "gpm-ask-refresh")); }
          footLink = el("button", "gpm-foot-link");
          footLink.type = "button";
          footLink.id = "gpm-foot-link";
          footLink.addEventListener("click", function () { var to = footLink.getAttribute("data-tab"); if (to) { pickTab(to); } });
          footEl.appendChild(footLink);
        }
        footLink.hidden = !r.foot;
        if (r.foot) {
          footLink.textContent = r.foot.title;
          footLink.setAttribute("data-tab", r.foot.id);
          if (r.selected === r.foot.id) { footLink.setAttribute("aria-current", "page"); } else { footLink.removeAttribute("aria-current"); }
        }
        if (footEl.parentNode !== ctx.header) { ctx.header.insertBefore(footEl, ctx.actions); }
        if (fresh && fresh.parentNode !== footEl) { footEl.insertBefore(fresh, footEl.firstChild); }
      }
      root.hidden = false;
      if (page) { page.hidden = true; }
      document.documentElement.classList.add(HAS_MODULES);
      if (rail) { document.documentElement.classList.add(RAIL); }
      shownTab = r.active;
      refocus();
      viewChanged();
      function refocus() {
        if (!focusKey) { return; }
        var sel = focusKey.indexOf("tab:") === 0 ? '[data-tab="' + focusKey.slice(4) + '"]'
          : focusKey.indexOf("module:") === 0 ? '[data-module="' + focusKey.slice(7) + '"]' : '[data-product="' + focusKey.slice(8) + '"]';
        var scope = focusKey.indexOf("tab:") === 0 ? (navEl || root) : focusKey.indexOf("module:") === 0 ? root : switchEl;
        var node = scope ? scope.querySelector(sel) : null;
        if (node) { try { node.focus(); } catch (e) { /* nothing to focus */ } }
      }
    }

    function safePaint() {
      try { paint(); } catch (e) { showPage(); }      // a failure shows the page as it was
    }
    ctx.onData(safePaint);
    safePaint();
    // who may turn a module on or off: the owner. What the platform does not say stays open, and a refused write closes it.
    Promise.resolve().then(function () {
      return window.claude && typeof window.claude.use === "function" ? window.claude.use("user") : null;
    }).then(function (u) { return u && typeof u.isOwner === "function" ? u.isOwner() : null; }).then(function (own) {
      if (own === false) { hooks.canWrite = false; hooks.note = ctx.t.ownerOnly; safePaint(); }
    }, function () { /* nothing known: the switches stay as they are */ });
    return ctx.db().then(function (db) {
      dbRef = db && typeof db.collection === "function" ? db : null;
      return readConfig(db, function (c) { if (!hooks.saving) { config = c; safePaint(); } });
    }).then(function (c) { config = c; safePaint(); });
  });
})();
