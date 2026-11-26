(function () {
  "use strict";
  // The chart blocks of the app: `lead` (one sentence over a module), `bars` (compared bars, a change from zero, columns
  // over time), `line` (one to four series over time) and `day` (a day as a strip of time), and two marks a table cell
  // may hold (a bar of parts, a meter with a limit). Fixed bytes, no data in it. Everything a section document brings is
  // foreign input: a text goes into the page only through textContent, a number only when finite, a colour never — the
  // marks take their colour from the classes of shell.css. A size goes into a style only as a number this file computed.
  // Charts are neutral: a series is told apart by its step of the neutral scale; only lines by category take the four
  // series colours, always with a legend and a label at the line's end. No pie, no second axis.
  var S = window.__gpmShell;
  if (!S || !S.blocks || !S.shape) { return; }
  var el = S.el, isObj = S.isObj, str = S.str, num = S.num;

  S.addStrings({
    uk: {
      asTable: "Ті самі числа таблицею",
      value: "Значення",
      period: "Період",
      ongoing: "триває",
      partialColumn: "Блідіший стовпчик: період ще триває.",
      partialLine: "Пунктир і порожня точка: період ще триває.",
      partialDropped: "Незавершений період не показано: ",
      threshold: "Поріг уваги",
      now: "Зараз",
      meeting: "Зустріч",
      focusTime: "Час фокусу",
      dayStrip: "День за часом",
      from: "від",
      to: "до",
      limit: "поріг",
      goingOn: "Триває, лишилось ",
      goingOnEnd: ".",
      hoursShort: "год",
      minutesShort: "хв",
      thousand: " тис."
    },
    en: {
      asTable: "The same numbers as a table",
      value: "Value",
      period: "Period",
      ongoing: "ongoing",
      partialColumn: "The paler column: the period is still running.",
      partialLine: "The dashed line and the hollow dot: the period is still running.",
      partialDropped: "The unfinished period is not shown: ",
      threshold: "Attention threshold",
      now: "Now",
      meeting: "Meeting",
      focusTime: "Focus time",
      dayStrip: "The day by time",
      from: "from",
      to: "to",
      limit: "limit",
      goingOn: "Going on, ",
      goingOnEnd: " left.",
      hoursShort: "h",
      minutesShort: "min",
      thousand: "k"
    }
  });

  var SVG_NS = "http://www.w3.org/2000/svg";
  var MAX_ROWS = 24, MAX_GROUPS = 8, MAX_COLUMNS = 60, MAX_POINTS = 120, MAX_SERIES = 4, MAX_ITEMS = 40, MAX_PARTS = 4;
  var TIME = /^([01]\d|2[0-3]):([0-5]\d)$/;
  var DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
  var LEVELS = ["warn", "crit"];
  var FILLS = ["", " gpm-c-fill-2", " gpm-c-fill-3"];          // the neutral scale, by the order of the series
  var uid = 0;

  // ---- values -------------------------------------------------------------------------------------------------------
  function svg(tag, attrs, text) {
    var n = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) { n.textContent = text; }
    return n;
  }
  function fmt(n) {
    try { return n.toLocaleString(S.lang === "en" ? "en-US" : "uk-UA", { maximumFractionDigits: 2 }); } catch (e) { return String(n); }
  }
  function signed(n) { return (n > 0 ? "+" : n < 0 ? "−" : "") + fmt(Math.abs(n)); }
  // a chart may fix how many digits stand after the point of its values (`digits`, 0-3): 5,40 beside 4,49
  function digitsOf(data) { var d = num(data.digits); return d !== null && d >= 0 && d <= 3 && Math.floor(d) === d ? d : null; }
  function fix(n, d) {
    if (d === null) { return fmt(n); }
    try { return n.toLocaleString(S.lang === "en" ? "en-US" : "uk-UA", { minimumFractionDigits: d, maximumFractionDigits: d }); } catch (e) { return n.toFixed(d); }
  }
  function signedFix(n, d) { return (n > 0 ? "+" : n < 0 ? "−" : "") + fix(Math.abs(n), d); }
  // the fills of the neutral scale for n series: two series are the darkest and the quietest step
  function fills(n) { return n === 2 ? ["", " gpm-c-fill-3"] : FILLS; }
  // a unit goes right after the number when it is a per cent sign, after a no-break space otherwise
  function withUnit(text, unit) { return unit ? text + (unit === "%" ? "" : " ") + unit : text; }
  function pct(x) { return (Math.round(Math.max(0, Math.min(100, x)) * 100) / 100) + "%"; }
  function level(v) { return LEVELS.indexOf(v) >= 0 ? v : null; }
  function minutes(v) {
    var m = typeof v === "string" ? TIME.exec(v) : null;
    return m ? parseInt(m[1], 10) * 60 + parseInt(m[2], 10) : null;
  }
  function clock(min) { return ("0" + Math.floor(min / 60)).slice(-2) + ":" + ("0" + (min % 60)).slice(-2); }
  // the next of 1, 2, 2.5, 5 x 10^k at or above x
  function niceUp(x) {
    if (!(x > 0)) { return 1; }
    var mag = Math.pow(10, Math.floor(Math.log(x) / Math.LN10));
    var steps = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < steps.length; i++) { if (steps[i] * mag >= x * 0.999999) { return steps[i] * mag; } }
    return 10 * mag;
  }

  // ---- the frame of a chart -----------------------------------------------------------------------------------------
  // the mark of attention with its word for a screen reader (blocks.js): a shape, never a colour alone
  var shape = S.shape;
  // a mark a pointer or the keyboard can stop on: its value in a small tip (the value is always on the chart as well)
  function hit(node, tip) {
    node.classList.add("gpm-hit");
    node.tabIndex = 0;
    node.appendChild(el("span", "gpm-tip", tip));
    return node;
  }
  function legend(items) {
    var ul = el("ul", "gpm-c-legend");
    items.forEach(function (it) {
      var li = el("li", "gpm-c-legend-item");
      var key = el("span", "gpm-c-key" + (it.cls || ""));
      key.setAttribute("aria-hidden", "true");
      li.appendChild(key);
      li.appendChild(document.createTextNode(it.text));
      ul.appendChild(li);
    });
    return ul;
  }
  // the same numbers as a table, folded under the chart: head = [text], rows = [[text]]
  function twin(head, rows) {
    var d = el("details", "gpm-c-table");
    d.appendChild(el("summary", null, S.t.asTable));
    var wrap = el("div", "gpm-scroll");
    wrap.tabIndex = 0;
    var tbl = el("table", "gpm-table");
    var tr = el("tr");
    head.forEach(function (h, i) { var th = el("th", i ? "gpm-num" : null, h); th.scope = "col"; tr.appendChild(th); });
    var thead = el("thead");
    thead.appendChild(tr);
    tbl.appendChild(thead);
    var tbody = el("tbody");
    rows.forEach(function (r) {
      var row = el("tr");
      r.forEach(function (c, i) {
        var cell = el(i ? "td" : "th", i ? "gpm-num" : null, c);
        if (!i) { cell.scope = "row"; }
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
    tbl.appendChild(tbody);
    wrap.appendChild(tbl);
    d.appendChild(wrap);
    return d;
  }
  // figure: the headline that says what the chart shows, what is measured, a legend, the plot, the notes, the table
  function frame(data, parts) {
    var fig = el("figure", "gpm-c-chart");
    var headline = str(data.headline, 200), sub = str(data.sub, 200);
    if (headline || sub) {
      var cap = el("figcaption", "gpm-c-head");
      if (headline) {
        var id = "gpm-c-" + (++uid);
        var h = el("span", "gpm-c-title", headline);
        h.id = id;
        cap.appendChild(h);
        fig.setAttribute("role", "group");
        fig.setAttribute("aria-labelledby", id);
      }
      if (sub) { cap.appendChild(el("span", "gpm-c-sub", sub)); }
      fig.appendChild(cap);
    }
    if (parts.legend) { fig.appendChild(parts.legend); }
    fig.appendChild(parts.body);
    var notes = (parts.notes || []).slice();
    if (str(data.note, 300)) { notes.push(data.note); }
    if (notes.length) {
      var foot = el("div", "gpm-c-foot");
      notes.forEach(function (n) { foot.appendChild(el("span", null, n)); });
      fig.appendChild(foot);
    }
    if (parts.twin) { fig.appendChild(parts.twin); }
    return fig;
  }

  // ---- lead: one sentence over a module -------------------------------------------------------------------------------
  function lead(data) {
    var text = str(data.text, 400);
    if (!text) { return null; }
    var box = el("div", "gpm-lead");
    box.appendChild(el("p", "gpm-lead-text", text));
    if (str(data.note, 300)) { box.appendChild(el("p", "gpm-lead-note", data.note)); }
    return box;
  }

  // ---- bars: compared bars ------------------------------------------------------------------------------------------
  function compare(data) {
    var names = (Array.isArray(data.series) ? data.series : []).filter(function (n) { return str(n, 40); }).slice(0, 3);
    var width = Math.max(1, names.length);
    var unit = str(data.unit, 8) || "";
    var rows = [];
    (Array.isArray(data.rows) ? data.rows : []).slice(0, MAX_ROWS).forEach(function (r) {
      if (!isObj(r) || !str(r.label, 80) || !Array.isArray(r.values)) { return; }
      var vals = r.values.slice(0, width).map(function (v) { var x = num(v); return x !== null && x >= 0 ? x : null; });
      if (vals.some(function (v) { return v !== null; })) { rows.push({ label: r.label, sub: str(r.sub, 80), values: vals }); }
    });
    var top = 0;
    rows.forEach(function (r) { r.values.forEach(function (v) { if (v !== null) { top = Math.max(top, v); } }); });
    if (!rows.length || top <= 0) { return null; }
    var grid = el("div", "gpm-c-bars");
    rows.forEach(function (r) {
      var lab = el("span", "gpm-c-bars-label", r.label);
      if (r.sub) { lab.appendChild(el("span", "gpm-c-bars-sub", r.sub)); }
      grid.appendChild(lab);
      var plot = el("div", "gpm-c-bars-plot");
      r.values.forEach(function (v, i) {
        if (v === null) { return; }
        var text = withUnit(fix(v, digitsOf(data)), unit);
        var row = el("div", "gpm-c-bar-row");
        var bar = el("span", "gpm-c-hbar" + fills(names.length)[i]);
        bar.style.width = pct(v / top * 76);
        row.appendChild(bar);
        row.appendChild(el("span", "gpm-c-bar-value", text));
        plot.appendChild(hit(row, r.label + (names[i] ? ", " + names[i] : "") + ": " + text));
      });
      grid.appendChild(plot);
    });
    return frame(data, {
      legend: names.length > 1 ? legend(names.map(function (n, i) { return { cls: fills(names.length)[i], text: n }; })) : null,
      body: grid,
      twin: twin([""].concat(names.length ? names : [S.t.value]), rows.map(function (r) {
        return [r.label].concat(r.values.map(function (v) { return v === null ? "" : withUnit(fix(v, digitsOf(data)), unit); }));
      }))
    });
  }

  // ---- bars: a change from zero -------------------------------------------------------------------------------------
  function delta(data) {
    var unit = typeof data.unit === "string" && data.unit.length <= 8 ? data.unit : "%";
    var raw = Array.isArray(data.groups) ? data.groups : (Array.isArray(data.rows) ? [{ rows: data.rows }] : []);
    var groups = [], hi = 0;
    raw.slice(0, MAX_GROUPS).forEach(function (g) {
      if (!isObj(g) || !Array.isArray(g.rows)) { return; }
      var rows = [];
      g.rows.slice(0, MAX_ROWS).forEach(function (r) {
        var v = isObj(r) ? num(r.value) : null;
        if (v === null || !str(r.label, 80)) { return; }
        hi = Math.max(hi, Math.abs(v));
        rows.push({ label: r.label, value: v, level: level(r.attention) });
      });
      if (rows.length) { groups.push({ title: str(g.title, 80), rows: rows }); }
    });
    if (!groups.length) { return null; }
    var ref = num(data.ref);
    if (ref === 0) { ref = null; }
    if (ref !== null) { hi = Math.max(hi, Math.abs(ref)); }
    var given = num(data.scale);
    var scale = given !== null && given >= hi && given > 0 ? given : niceUp(hi || 1);
    var half = scale / 2;
    var body = el("div", "gpm-c-groups");
    var table = [];
    groups.forEach(function (g) {
      var box = el("div", "gpm-c-group");
      if (g.title) { box.appendChild(el("p", "gpm-c-group-title", g.title)); }
      var grid = el("div", "gpm-c-delta");
      g.rows.forEach(function (r) {
        var text = withUnit(signedFix(r.value, digitsOf(data)), unit);
        var fill = r.level ? " gpm-c-fill-" + r.level : "";
        grid.appendChild(el("span", "gpm-c-delta-label", r.label));
        var row = el("div", "gpm-c-delta-row");
        var neg = el("div", "gpm-c-delta-neg"), pos = el("div", "gpm-c-delta-pos");
        if (ref !== null) {
          var line = el("span", "gpm-c-ref");
          if (ref < 0) { line.style.right = pct(Math.abs(ref) / scale * 100); neg.appendChild(line); }
          else { line.style.left = pct(ref / scale * 100); pos.appendChild(line); }
        }
        if (r.value !== 0) {
          var bar = el("span", "gpm-c-hbar" + (r.value < 0 ? " gpm-c-hbar-neg" : "") + fill);
          bar.style.width = pct(Math.abs(r.value) / scale * 100);
          (r.value < 0 ? neg : pos).appendChild(bar);
        }
        row.appendChild(neg);
        row.appendChild(pos);
        grid.appendChild(hit(row, (g.title ? g.title + ", " : "") + r.label + ": " + text));
        var val = el("span", "gpm-c-delta-value" + (r.level ? " gpm-ink-" + r.level : ""));
        if (r.level) { val.appendChild(shape(r.level)); }
        val.appendChild(document.createTextNode(text));
        grid.appendChild(val);
        table.push([(g.title ? g.title + ", " : "") + r.label, text]);
      });
      grid.appendChild(el("span"));
      var axis = el("div", "gpm-c-axis");
      axis.setAttribute("aria-hidden", "true");
      [-half, 0, half].forEach(function (v) {
        var tick = el("span", "gpm-c-axis-tick", v === 0 ? "0" : withUnit(signed(v), unit));
        tick.style.left = pct(50 + v / scale * 50);
        axis.appendChild(tick);
      });
      grid.appendChild(axis);
      grid.appendChild(el("span"));
      box.appendChild(grid);
      body.appendChild(box);
    });
    var lg = null;
    if (ref !== null) {
      lg = legend([{ cls: " gpm-c-key-line gpm-c-fill-warn", text: (str(data.refLabel, 80) || S.t.threshold) + ", " + withUnit(signed(ref), unit) }]);
    }
    return frame(data, { legend: lg, body: body, twin: twin(["", S.t.value], table) });
  }

  // ---- bars: columns over time --------------------------------------------------------------------------------------
  function columns(data) {
    var unit = str(data.unit, 8) || "";
    var cols = [], top = 0, partial = false;
    (Array.isArray(data.cols) ? data.cols : []).slice(0, MAX_COLUMNS).forEach(function (c) {
      var v = isObj(c) ? num(c.value) : null;
      if (v === null || v < 0 || !str(c.label, 24)) { return; }
      top = Math.max(top, v);
      if (c.partial === true) { partial = true; }
      cols.push({ label: c.label, value: v, partial: c.partial === true });
    });
    if (!cols.length || top <= 0) { return null; }
    var box = el("div", "gpm-c-cols");
    cols.forEach(function (c, i) {
      var text = withUnit(fmt(c.value), unit);
      var col = el("div", "gpm-c-col");
      var plot = el("div", "gpm-c-col-plot");
      plot.appendChild(el("span", "gpm-c-col-value", text));
      var bar = el("span", "gpm-c-col-bar" + (c.partial ? " gpm-c-fill-3" : ""));
      bar.style.height = Math.round(c.value / top * 120) + "px";
      plot.appendChild(bar);
      col.appendChild(plot);
      col.appendChild(el("span", "gpm-c-col-x", c.label));
      hit(col, c.label + ": " + text + (c.partial ? ", " + S.t.ongoing : ""));
      if (i >= cols.length / 2) { col.lastChild.classList.add("gpm-tip-end"); }
      box.appendChild(col);
    });
    return frame(data, {
      body: box,
      notes: partial ? [S.t.partialColumn] : [],
      twin: twin([S.t.period, S.t.value], cols.map(function (c) {
        return [c.label + (c.partial ? ", " + S.t.ongoing : ""), withUnit(fmt(c.value), unit)];
      }))
    });
  }

  // a chart that stands beside a table of the same numbers (info.twin === false) does not fold its own under itself
  function untwinned(node, info) {
    if (node && info && info.twin === false) {
      Array.prototype.slice.call(node.querySelectorAll(".gpm-c-table")).forEach(function (d) { d.parentNode.removeChild(d); });
    }
    return node;
  }
  function bars(data, view, info) {
    return untwinned(data.kind === "delta" ? delta(data) : data.kind === "columns" ? columns(data) : data.kind === "compare" ? compare(data) : null, info);
  }

  // ---- line: one to four series over time ---------------------------------------------------------------------------
  // the level marks of the value axis from zero, at most three grid lines: [value]
  function ticks(top) {
    var mag = Math.pow(10, Math.floor(Math.log(top) / Math.LN10));
    var steps = [];
    [mag / 10, mag, mag * 10].forEach(function (g) { [1, 2, 2.5, 5].forEach(function (m) { steps.push(m * g); }); });
    steps.sort(function (a, b) { return a - b; });
    var step = steps[steps.length - 1];
    for (var i = 0; i < steps.length; i++) { if (Math.floor(top / steps[i] + 1e-9) <= 3) { step = steps[i]; break; } }
    var out = [];
    for (var k = 0; k <= Math.floor(top / step + 1e-9); k++) { out.push(step * k); }
    return out;
  }

  function line(data) {
    var xs = (Array.isArray(data.x) ? data.x : []).slice(0, MAX_POINTS);
    if (xs.length < 2 || xs.some(function (x) { return !str(x, 24); })) { return null; }
    var unit = str(data.unit, 8) || "";
    var series = [];
    (Array.isArray(data.series) ? data.series : []).slice(0, MAX_SERIES).forEach(function (s) {
      if (!isObj(s) || !Array.isArray(s.values) || s.values.length !== xs.length) { return; }
      var vals = s.values.map(function (v) { var x = num(v); return x !== null && x >= 0 ? x : null; });
      if (vals.filter(function (v) { return v !== null; }).length >= 2) { series.push({ name: str(s.name, 40) || "", values: vals }); }
    });
    if (!series.length) { return null; }
    var many = series.length > 1;
    var partial = data.partial === true && xs.length > 2;
    var notes = [];
    var dropped = null;
    if (partial && many) {            // several lines: the unfinished period is left out and said so under the chart
      dropped = xs[xs.length - 1];
      xs = xs.slice(0, -1);
      series.forEach(function (s) { s.values = s.values.slice(0, -1); });
      notes.push(S.t.partialDropped + dropped + ".");
      partial = false;
    } else if (partial) { notes.push(S.t.partialLine); }
    var n = xs.length, last = partial ? n - 2 : n - 1;
    var hi = 0;
    series.forEach(function (s) { s.values.forEach(function (v) { if (v !== null) { hi = Math.max(hi, v); } }); });
    if (hi <= 0) { return null; }
    var marks = ticks(hi);
    var top = Math.max(marks[marks.length - 1], hi * 1.08);
    var W = 640, H = 240, x0 = 64, x1 = W - (many ? 176 : 124), y0 = 18, y1 = H - 34;
    function X(i) { return Math.round((x0 + (x1 - x0) * i / (n - 1)) * 10) / 10; }
    function Y(v) { return Math.round((y1 - v / top * (y1 - y0)) * 10) / 10; }
    function short(v) { return v >= 1000 && v % 1000 === 0 ? fmt(v / 1000) + S.t.thousand : fmt(v); }
    var g = svg("svg", { "class": "gpm-c-line", viewBox: "0 0 " + W + " " + H, role: "img" });
    g.tabIndex = 0;
    g.setAttribute("aria-label", str(data.headline, 200) || series.map(function (s) {
      var known = s.values.filter(function (v) { return v !== null; });
      return (s.name ? s.name + ": " : "") + S.t.from + " " + fmt(known[0]) + " " + S.t.to + " " + fmt(known[known.length - 1]);
    }).join("; "));
    marks.forEach(function (v, j) {
      g.appendChild(svg("line", { "class": j ? "gpm-c-line-grid" : "gpm-c-line-axis", x1: x0, x2: x1, y1: Y(v), y2: Y(v) }));
      g.appendChild(svg("text", { "class": "gpm-c-line-text", x: x0 - 10, y: Y(v) + 4, "text-anchor": "end" }, v === 0 ? "0" : short(v)));
    });
    var step = Math.max(1, Math.ceil((n - 1) / 7));
    for (var i = 0; i < n; i += step) {
      g.appendChild(svg("text", { "class": "gpm-c-line-text", x: X(i), y: y1 + 20, "text-anchor": "middle" }, xs[i]));
    }
    var cross = svg("line", { "class": "gpm-c-line-cross", x1: 0, x2: 0, y1: y0, y2: y1 });
    cross.style.display = "none";
    g.appendChild(cross);
    var ends = [];
    series.forEach(function (s, si) {
      var key = many ? " gpm-c-s" + (si + 1) : "";
      var run = [];
      function flush() {
        if (run.length > 1) { g.appendChild(svg("polyline", { "class": "gpm-c-line-path" + key, points: run.join(" ") })); }
        run = [];
      }
      for (var k = 0; k <= last; k++) {
        if (s.values[k] === null) { flush(); } else { run.push(X(k) + "," + Y(s.values[k])); }
      }
      flush();
      var end = last;
      while (end > 0 && s.values[end] === null) { end--; }
      if (s.values[end] === null) { return; }
      if (partial && s.values[n - 1] !== null && end === last) {
        g.appendChild(svg("line", { "class": "gpm-c-line-path gpm-c-line-part", x1: X(last), y1: Y(s.values[last]), x2: X(n - 1), y2: Y(s.values[n - 1]) }));
        g.appendChild(svg("circle", { "class": "gpm-c-line-dot-open", cx: X(n - 1), cy: Y(s.values[n - 1]), r: 4 }));
        g.appendChild(svg("text", { "class": "gpm-c-line-note", x: X(n - 1) + 12, y: Y(s.values[n - 1]) + 4 },
          withUnit(fmt(s.values[n - 1]), unit) + ", " + S.t.ongoing));
      }
      g.appendChild(svg("circle", { "class": "gpm-c-line-dot" + key, cx: X(end), cy: Y(s.values[end]), r: 5 }));
      ends.push({ y: Y(s.values[end]), x: X(end), text: (s.name && many ? (s.name.length > 18 ? s.name.slice(0, 17) + "…" : s.name) + " " : "") + withUnit(fmt(s.values[end]), unit) });
    });
    ends.sort(function (a, b) { return a.y - b.y; });
    for (var a = 1; a < ends.length; a++) { if (ends[a].y - ends[a - 1].y < 17) { ends[a].y = ends[a - 1].y + 17; } }
    ends.forEach(function (e) {
      // one line: the label sits over the last full point when an unfinished one follows it, beside it otherwise
      if (partial) { g.appendChild(svg("text", { "class": "gpm-c-line-label", x: e.x, y: e.y - 12, "text-anchor": "middle" }, e.text)); }
      else { g.appendChild(svg("text", { "class": "gpm-c-line-label", x: e.x + 14, y: Math.round((e.y + 4) * 10) / 10 }, e.text)); }
    });
    var wrap = el("div", "gpm-c-line-wrap");
    wrap.appendChild(g);
    var tip = el("span", "gpm-tip");
    tip.setAttribute("aria-hidden", "true");
    wrap.appendChild(tip);
    var cur = n - 1;
    function tipText(i) {
      var rows = [xs[i] + (partial && i === n - 1 ? ", " + S.t.ongoing : "")];
      series.forEach(function (s) {
        if (s.values[i] !== null) { rows.push((s.name ? s.name + ": " : "") + withUnit(fmt(s.values[i]), unit)); }
      });
      return rows.join("\n");
    }
    function show(i) {
      cur = Math.max(0, Math.min(n - 1, i));
      var x = X(cur);
      cross.setAttribute("x1", x);
      cross.setAttribute("x2", x);
      cross.style.display = "";
      tip.textContent = tipText(cur);
      tip.style.left = Math.max(18, Math.min(82, x / W * 100)) + "%";
      tip.style.display = "block";
    }
    function hide() { cross.style.display = "none"; tip.style.display = "none"; }
    g.addEventListener("pointermove", function (e) {
      var r = g.getBoundingClientRect();
      if (!r.width) { return; }
      var x = (e.clientX - r.left) / r.width * W, best = 0;
      for (var k = 1; k < n; k++) { if (Math.abs(X(k) - x) < Math.abs(X(best) - x)) { best = k; } }
      show(best);
    });
    g.addEventListener("pointerleave", hide);
    g.addEventListener("focus", function () { show(cur); });
    g.addEventListener("blur", hide);
    g.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { show(cur - 1); e.preventDefault(); }
      else if (e.key === "ArrowRight") { show(cur + 1); e.preventDefault(); }
    });
    return frame(data, {
      legend: many ? legend(series.map(function (s, si) { return { cls: " gpm-c-fill-s" + (si + 1), text: s.name || String(si + 1) }; })) : null,
      body: wrap,
      notes: notes,
      twin: twin([S.t.period].concat(series.map(function (s, si) { return s.name || (many ? String(si + 1) : S.t.value); })), xs.map(function (x, i) {
        return [x + (partial && i === n - 1 ? ", " + S.t.ongoing : "")].concat(series.map(function (s) {
          return s.values[i] === null ? "" : withUnit(fmt(s.values[i]), unit);
        }));
      }))
    });
  }

  // ---- day: a day as a strip of time, and its rows --------------------------------------------------------------------
  function localDay() {
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function day(data, view) {
    var start = minutes(data.start), end = minutes(data.end);
    if (start === null || end === null || end - start < 60) { return null; }
    var items = [];
    (Array.isArray(data.items) ? data.items : []).slice(0, MAX_ITEMS).forEach(function (it) {
      if (!isObj(it) || !str(it.title, 200)) { return; }
      if (str(it.product, 64) && view && typeof view.shows === "function" && !view.shows(it.product)) { return; }
      var a = minutes(it.from), b = minutes(it.to);
      if (a === null || b === null || b <= a) { return; }
      items.push({ from: a, to: b, focus: it.kind === "focus", title: it.title, note: str(it.note, 300) });
    });
    if (!items.length) { return null; }
    items.sort(function (p, q) { return p.from - q.from; });
    // «now» is this window's own clock, and only on the day the section was made for
    var now = null;
    if (typeof data.date === "string" && DATE.test(data.date) && data.date === localDay()) {
      var d = new Date();
      now = d.getHours() * 60 + d.getMinutes();
      if (now < start || now > end) { now = null; }
    }
    var span = end - start;
    var strip = el("div", "gpm-c-day");
    strip.setAttribute("role", "group");
    strip.setAttribute("aria-label", S.t.dayStrip);
    strip.appendChild(el("span", "gpm-c-day-track"));
    var hasFocus = false, hasMeeting = false;
    items.forEach(function (it) {
      var a = Math.max(start, it.from), b = Math.min(end, it.to);
      if (b <= a) { return; }
      if (it.focus) { hasFocus = true; } else { hasMeeting = true; }
      var block = el("span", "gpm-c-day-block" + (it.focus ? " gpm-c-fill-3" : ""));
      block.style.left = "calc(" + pct((a - start) / span * 100) + " + 1px)";
      block.style.width = "calc(" + pct((b - a) / span * 100) + " - 2px)";
      strip.appendChild(hit(block, clock(it.from) + "–" + clock(it.to) + ", " + it.title));
      if ((a - start) / span > 0.5) { block.lastChild.classList.add("gpm-tip-end"); }
    });
    if (now !== null) {
      var x = pct((now - start) / span * 100);
      var label = el("span", "gpm-c-day-now-label", S.t.now + " " + clock(now));
      label.style.left = x;
      strip.appendChild(label);
      var mark = el("span", "gpm-c-day-now");
      mark.style.left = x;
      strip.appendChild(mark);
    }
    var stepMin = span > 480 ? 120 : 60;
    for (var m = start; m <= end; m += stepMin) {
      var tick = el("span", "gpm-c-day-tick" + (m === start ? " gpm-c-day-tick-first" : m === end ? " gpm-c-day-tick-last" : ""), clock(m));
      tick.style.left = pct((m - start) / span * 100);
      strip.appendChild(tick);
    }
    var list = el("ul", "gpm-list gpm-c-day-rows");
    var said = false;
    function nowRow() {
      var li = el("li", "gpm-c-day-nowrow");
      li.appendChild(el("span", null, S.t.now + ", " + clock(now)));
      list.appendChild(li);
      said = true;
    }
    items.forEach(function (it) {
      // the line of «now» stands over what goes on or comes next
      if (now !== null && !said && it.to > now) { nowRow(); }
      var current = now !== null && it.from <= now && now < it.to;
      var li = el("li", "gpm-item gpm-c-day-row" + (current ? " gpm-c-day-current" : ""));
      li.appendChild(el("span", "gpm-at", clock(it.from) + "–" + clock(it.to)));
      var body = el("span", "gpm-c-day-body");
      body.appendChild(el("span", "gpm-item-title", it.title));
      if (it.note) { body.appendChild(el("span", "gpm-note", it.note)); }
      if (current) {
        var left = it.to - now, h = Math.floor(left / 60), m = left % 60;
        body.appendChild(el("span", "gpm-note", S.t.goingOn + (h ? h + " " + S.t.hoursShort + (m ? " " : "") : "") + (m ? m + " " + S.t.minutesShort : "") + S.t.goingOnEnd));
      }
      li.appendChild(body);
      list.appendChild(li);
    });
    if (now !== null && !said) { nowRow(); }
    var keys = [];
    if (hasMeeting) { keys.push({ cls: "", text: S.t.meeting }); }
    if (hasFocus) { keys.push({ cls: " gpm-c-fill-3", text: S.t.focusTime }); }
    var body = el("div", "gpm-c-day-box");
    body.appendChild(strip);
    body.appendChild(list);
    return frame(data, { legend: keys.length > 1 ? legend(keys) : null, body: body });
  }

  // ---- marks inside a table cell ----------------------------------------------------------------------------------
  // a bar of up to four parts (a share of the whole each); the column names the parts for a screen reader and the legend
  // the fill of part i of n: the neutral scale in order; a last part that means «wrong» (`last: warn`) takes that colour
  function segFill(i, n, col) {
    var warned = col.last === "warn";
    if (warned && i === n - 1) { return " gpm-c-fill-warn"; }
    var scale = fills(warned ? n - 1 : n);
    return scale[i] !== undefined ? scale[i] : " gpm-c-fill-3";
  }
  function segments(value, col) {
    var parts = (Array.isArray(value) ? value : []).slice(0, MAX_PARTS).map(function (v) { var x = num(v); return x !== null && x > 0 ? x : 0; });
    var total = parts.reduce(function (a, b) { return a + b; }, 0);
    if (total <= 0) { return null; }
    var names = Array.isArray(col.parts) ? col.parts : [];
    var bar = el("div", "gpm-c-seg");
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", parts.map(function (v, i) { return (str(names[i], 40) ? names[i] + ": " : "") + fmt(v); }).join(", "));
    var shown = [];
    parts.forEach(function (v, i) { if (v > 0) { shown.push(i); } });
    shown.forEach(function (i, at) {
      var fill = segFill(i, parts.length, col);
      var seg = el("span", "gpm-c-seg-part" + fill + (at === 0 ? " gpm-c-seg-first" : "") + (at === shown.length - 1 ? " gpm-c-seg-last" : ""));
      seg.style.flex = parts[i] + " 1 0";
      bar.appendChild(seg);
    });
    return bar;
  }
  // the legend of a segments column: its part names with the fills the bar uses
  function segmentsLegend(col) {
    var names = (Array.isArray(col.parts) ? col.parts : []).slice(0, MAX_PARTS);
    if (!names.length || names.some(function (n) { return !str(n, 40); })) { return null; }
    return legend(names.map(function (n, i) {
      return { cls: segFill(i, names.length, col), text: n };
    }));
  }
  // a meter: the value on a scale with a limit mark; the level colours the fill, the cell's text names it
  function meter(value, col, lvl) {
    var v = num(value), scale = num(col.scale), limit = num(col.limit);
    if (v === null || v < 0 || scale === null || scale <= 0) { return null; }
    var box = el("div", "gpm-c-meter");
    box.setAttribute("role", "img");
    box.setAttribute("aria-label", fmt(v) + (limit !== null ? ", " + S.t.limit + " " + fmt(limit) : ""));
    var fill = el("span", "gpm-c-meter-fill" + (level(lvl) ? " gpm-c-fill-" + lvl : ""));
    fill.style.width = pct(Math.min(v, scale) / scale * 100);
    box.appendChild(fill);
    if (limit !== null && limit > 0 && limit < scale) {
      var mark = el("span", "gpm-c-meter-limit");
      mark.style.left = pct(limit / scale * 100);
      box.appendChild(mark);
    }
    return box;
  }

  S.blocks.lead = lead;
  S.blocks.bars = bars;
  S.blocks.line = function (data, view, info) { return untwinned(line(data, view, info), info); };
  S.blocks.day = day;
  S.cells = { segments: segments, meter: meter };
  S.cellLegend = { segments: segmentsLegend };
})();
