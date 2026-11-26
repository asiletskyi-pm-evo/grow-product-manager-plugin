(function () {
  "use strict";
  // The app shell core: fixed bytes, no data in it. The profile comes from #gpm-profile; the parts are started
  // independently, each in its own try/catch — a part that fails, is refused or never settles switches itself off (or
  // waits) alone and holds no other part back. The core exposes one registry, window.__gpmShell; the files that follow
  // it (blocks.js, ...) register their parts there first, and every part starts on DOMContentLoaded.

  var STRINGS = {
    uk: {
      install: "Встановити як застосунок",
      busy: "Виконується…",
      done: "Готово",
      cancelled: "Скасовано: ви відмовились встановлювати",
      unavailable: "Тут встановити не вийде",
      failed: "Не вдалося встановити",
      refused: "Відмовлено",
      freshness: "дані від ",
      themeLabel: "Тема",
      themeLight: "Світла",
      themeDark: "Темна",
      themeSystem: "Як у системі"
    },
    en: {
      install: "Install as an app",
      busy: "Working…",
      done: "Done",
      cancelled: "Cancelled: you declined to install",
      unavailable: "Cannot be installed here",
      failed: "Installation failed",
      refused: "Refused",
      freshness: "data from ",
      themeLabel: "Theme",
      themeLight: "Light",
      themeDark: "Dark",
      themeSystem: "System"
    }
  };
  var PARTS = [];
  var t = STRINGS.uk;            // the words of the page's language, set in init()
  var pageLang = "uk";

  function part(name, fn) { PARTS.push({ name: name, run: fn }); }

  function readProfile() {
    var el = document.getElementById("gpm-profile");
    return JSON.parse(el.textContent);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text != null) { e.textContent = text; }
    return e;
  }

  // The state of one button: at once the label «Виконується…» and disabled; then «Готово» or the refusal in words,
  // in a note next to the button. Every button of the shell goes through it. Resolves true when the action succeeded.
  function busy(button, promise) {
    var label = button.textContent;
    var note = button.nextElementSibling && button.nextElementSibling.classList.contains("gpm-state")
      ? button.nextElementSibling : null;
    if (!note) {
      note = el("span", "gpm-state");
      note.setAttribute("role", "status");
      button.parentNode.insertBefore(note, button.nextSibling);
    }
    button.disabled = true;
    button.textContent = t.busy;
    note.textContent = "";
    return Promise.resolve(promise).then(function () {
      note.textContent = t.done;
      return true;
    }, function (e) {
      var why = e && e.refusal ? e.message : t.refused + (e && (e.code || e.message) ? ": " + (e.code || e.message) : "");
      note.textContent = why;
      return false;
    }).then(function (ok) {
      button.textContent = label;
      button.disabled = false;
      return ok;
    });
  }

  function refusal(text) {
    var e = new Error(text);
    e.refusal = true;
    return e;
  }

  // ---- the install button -----------------------------------------------------------------------------------------
  part("install", function (ctx) {
    return ctx.desktop().then(function (desktop) {
      if (!desktop || !desktop.install) { return; }
      return desktop.install.state().then(function (state) {
        if (state !== "available") { return; }
        var button = el("button", "gpm-btn gpm-install", t.install);
        button.type = "button";
        ctx.actions.appendChild(button);
        button.addEventListener("click", function () {
          // inside the promise: a request() that throws at once is a refusal in words, never an error on the page
          var asked = Promise.resolve().then(function () { return desktop.install.request(); }).then(function (answer) {
            if (answer === "installed") { return; }
            if (answer === "cancelled") { throw refusal(t.cancelled); }
            throw refusal(answer === "unavailable" ? t.unavailable : t.failed);
          });
          busy(button, asked).then(function (ok) { if (ok) { button.disabled = true; } });
        });
      });
    });
  });

  // ---- the data channel -------------------------------------------------------------------------------------------
  // The data of the app lives in the artifact's database (collection `snapshot`), never in this page. Everything read
  // there is foreign input: a type is never trusted, a document that does not fit its shape is skipped, and a value goes
  // into the page only through textContent. readSnapshot never throws and never rejects.
  var SECTION_ID = /^[a-z0-9][a-z0-9.-]{0,63}--[a-z0-9][a-z0-9-]{0,63}$/;
  var COLOR = /^#[0-9a-fA-F]{6}$/;
  var LOAD_TIMEOUT = 10000;

  function isObj(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function str(v, max) { return typeof v === "string" && v.length > 0 && v.length <= (max || 200) ? v : null; }
  function num(v) { return typeof v === "number" && isFinite(v) ? v : null; }

  function cleanMeta(raw) {
    if (!isObj(raw)) { return null; }
    var made = str(raw.made, 40);
    if (!made) { return null; }
    var meta = { made: made, products: [], thresholds: { warning: 0.1, critical: 0.25 }, sections: {}, connectors: {} };
    if (Array.isArray(raw.products)) {
      raw.products.forEach(function (p) {
        if (!isObj(p) || !str(p.id, 64) || !str(p.label, 24)) { return; }
        meta.products.push({ id: p.id, label: p.label, color: typeof p.color === "string" && COLOR.test(p.color) ? p.color : null });
      });
    }
    if (isObj(raw.thresholds)) {
      var w = num(raw.thresholds.warning), c = num(raw.thresholds.critical);
      if (w !== null && c !== null && w > 0 && c > w && c < 1) { meta.thresholds = { warning: w, critical: c }; }
    }
    if (isObj(raw.sections)) {
      Object.keys(raw.sections).forEach(function (id) {
        if (SECTION_ID.test(id) && str(raw.sections[id], 40)) { meta.sections[id] = raw.sections[id]; }
      });
    }
    if (isObj(raw.connectors)) {
      Object.keys(raw.connectors).forEach(function (role) {
        var b = /^[a-z0-9][a-z0-9-]{0,63}$/.test(role) ? cleanBinding(raw.connectors[role]) : null;
        if (b) { meta.connectors[role] = b; }
      });
    }
    return meta;
  }

  // A role's binding {server, tool, input, pick} (the same rules as `snapshot --connectors` in app_shell.py): the
  // connector's display name and tool, the tool's arguments (plain JSON, at most 4 KiB and 6 levels, the placeholders
  // {codes} / "{codes[]}" only) and three dot-paths that read the answer. A binding that does not fit is dropped.
  var PICK_PATH = /^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+){0,7}$/;
  var INPUT_MAX = 4096, INPUT_DEPTH = 6;
  function inputFits(v, depth) {
    if (Array.isArray(v) || isObj(v)) {
      if (depth > INPUT_DEPTH) { return false; }
      var keys = Array.isArray(v) ? null : Object.keys(v);
      if (keys && keys.some(function (k) { return k.indexOf("{") >= 0 || k.indexOf("}") >= 0; })) { return false; }
      return (keys ? keys.map(function (k) { return v[k]; }) : v).every(function (x) { return inputFits(x, depth + 1); });
    }
    if (typeof v === "string") {
      var rest = v.split("{codes}").join("");
      return v === "{codes[]}" || (rest.indexOf("{") < 0 && rest.indexOf("}") < 0);
    }
    return v === null || typeof v === "boolean" || num(v) !== null;
  }
  function cleanBinding(b) {
    try {
      if (!isObj(b) || !str(b.server, 100) || !str(b.tool, 100) || !isObj(b.input) || !isObj(b.pick)) { return null; }
      var text = JSON.stringify(b.input);
      if (unescape(encodeURIComponent(text)).length > INPUT_MAX || !inputFits(b.input, 1)) { return null; }
      var keys = Object.keys(b.pick).sort().join(",");
      if (keys !== "items,key,value") { return null; }
      var pick = {};
      var ok = ["items", "key", "value"].every(function (k) {
        var v = b.pick[k];
        pick[k] = v;
        return typeof v === "string" && (PICK_PATH.test(v) || (k === "items" && v === ""));
      });
      return ok ? { server: b.server, tool: b.tool, input: JSON.parse(text), pick: pick } : null;
    } catch (e) { return null; }
  }

  function cleanSection(id, raw) {
    if (!SECTION_ID.test(id) || !isObj(raw) || !isObj(raw.data)) { return null; }
    var made = str(raw.made, 40);
    if (!made || !str(raw.section, 64)) { return null; }
    // a document with no product (or an unreadable one) is kept with product "": the modules show it under «Без продукту»
    return { product: str(raw.product, 64) || "", section: raw.section, made: made, data: raw.data };
  }

  function emptySnapshot() { return { meta: null, theme: null, sections: {} }; }

  // A query snapshot -> {meta, theme, sections}. The theme is kept as an object only; its tokens are checked by the
  // part that applies it.
  function parseSnapshot(qs) {
    var out = emptySnapshot();
    try {
      var docs = qs && qs.docs ? Array.prototype.slice.call(qs.docs) : [];
      docs.forEach(function (d) {
        try {
          var id = d && typeof d.id === "string" ? d.id : "";
          var body = d && d.exists !== false && typeof d.data === "function" ? d.data() : null;
          if (id === "meta") { out.meta = cleanMeta(body); }
          else if (id === "theme") { out.theme = isObj(body) ? body : null; }
          else {
            var sec = cleanSection(id, body);
            if (sec) { out.sections[id] = sec; }
          }
        } catch (e) { /* one malformed document is skipped */ }
      });
    } catch (e) { return emptySnapshot(); }
    return out;
  }

  // Resolves once with the first answer (an empty result after 10 s, on a refusal or without a database); stays
  // subscribed and calls onChange with every later state. Subscribed once, never again.
  function readSnapshot(db, onChange) {
    return new Promise(function (resolve) {
      var settled = false, timer = null;
      function first(v) { if (!settled) { settled = true; if (timer) { clearTimeout(timer); } resolve(v); } }
      if (!db || typeof db.collection !== "function") { first(emptySnapshot()); return; }
      timer = setTimeout(function () { first(emptySnapshot()); }, LOAD_TIMEOUT);
      try {
        db.collection("snapshot").onSnapshot(function (qs) {
          var snap = parseSnapshot(qs);
          if (!settled) { first(snap); }
          else if (onChange) { try { onChange(snap); } catch (e) { /* a listener must not break the stream */ } }
        }, function () { first(emptySnapshot()); });
      } catch (e) { first(emptySnapshot()); }
    });
  }

  // 2026-11-26T10:00:00Z -> 26.11.2026 (uk) / 2026-11-26 (en); anything else shows no line.
  function showDate(made, lang) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(made || "");
    if (!m) { return ""; }
    return lang === "en" ? m[1] + "-" + m[2] + "-" + m[3] : m[3] + "." + m[2] + "." + m[1];
  }

  part("data", function (ctx) {
    var line = null;
    function paint(snap) {
      var text = snap && snap.meta ? showDate(snap.meta.made, ctx.lang) : "";
      if (!line && !text) { return; }
      if (!line) {
        line = el("span", "gpm-fresh");
        ctx.header.insertBefore(line, ctx.actions);
      }
      line.textContent = text ? ctx.t.freshness + text : "";
      line.hidden = !text;
    }
    function apply(snap) { ctx.setData(snap); paint(snap); }
    return ctx.db().then(function (db) { return readSnapshot(db, apply); }).then(apply);
  });

  // ---- the theme --------------------------------------------------------------------------------------------------
  // The colours, font and radius of the shell come from the product's design tokens: the document `snapshot/theme`
  // (light and dark), read through the data channel. It is foreign input: a colour only as #rrggbb, a font only from the
  // fixed list below (the same twelve as the script that writes the theme), a radius only a whole number 0-24; anything
  // else keeps the neutral default that shell.css holds. Only variables on the root element are set — the wrapped
  // page's own colours are never touched. The switch in the header chooses light, dark or the system's own.
  var TOKENS = ["bg", "surface", "text", "muted", "accent", "border", "ok", "warn", "crit"];
  var FONTS = ["Inter", "Roboto", "Open Sans", "Montserrat", "Manrope", "Rubik", "Nunito", "PT Sans", "Fira Sans",
    "IBM Plex Sans", "Noto Sans", "Golos Text"];
  var FONT_FALLBACK = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  var FONT_LINK = "gpm-font";
  var CHOICES = ["light", "dark", "system"];
  var STORE_KEY = "gpm-theme";
  var choice = "system";          // the person's choice; the default follows the system

  function relLuminance(hex) {
    var c = [1, 3, 5].map(function (i) {
      var v = parseInt(hex.substr(i, 2), 16) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function ratio(a, b) {
    var x = relLuminance(a), y = relLuminance(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }

  function systemDark() {
    try { return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches); } catch (e) { return false; }
  }
  function effectiveMode() { return choice === "system" ? (systemDark() ? "dark" : "light") : choice; }

  function readChoice() {
    try {
      var v = window.localStorage.getItem(STORE_KEY);
      return CHOICES.indexOf(v) >= 0 ? v : "system";
    } catch (e) { return "system"; }
  }
  function saveChoice(v) {
    try { window.localStorage.setItem(STORE_KEY, v); } catch (e) { /* kept for this session only */ }
  }

  // The one place where a font is loaded: a single <link> built from the list's own spelling, never from the database.
  function setFont(name) {
    var link = document.getElementById(FONT_LINK);
    var i = FONTS.indexOf(name);
    if (i < 0) { if (link) { link.parentNode.removeChild(link); } return false; }
    var href = "https://fonts.googleapis.com/css2?family=" + FONTS[i].split(" ").join("+") + ":wght@400;700&display=swap";
    if (!link) {
      link = document.createElement("link");
      link.rel = "stylesheet";
      link.id = FONT_LINK;
      document.head.appendChild(link);
    }
    if (link.getAttribute("href") !== href) { link.setAttribute("href", href); }
    return true;
  }

  function applyTheme(theme) {
    var style = document.documentElement.style;
    var side = isObj(theme) && isObj(theme[effectiveMode()]) ? theme[effectiveMode()] : {};
    TOKENS.forEach(function (k) {
      if (typeof side[k] === "string" && COLOR.test(side[k])) { style.setProperty("--gpm-" + k, side[k]); }
      else { style.removeProperty("--gpm-" + k); }
    });
    if (typeof side.accent === "string" && COLOR.test(side.accent)) {
      style.setProperty("--gpm-accent-fg", ratio("#ffffff", side.accent) >= ratio("#0d1117", side.accent) ? "#ffffff" : "#0d1117");
    } else { style.removeProperty("--gpm-accent-fg"); }
    var r = isObj(theme) ? theme.radius : null;
    if (typeof r === "number" && isFinite(r) && Math.floor(r) === r && r >= 0 && r <= 24) { style.setProperty("--gpm-radius", r + "px"); }
    else { style.removeProperty("--gpm-radius"); }
    var f = isObj(theme) ? theme.font : null;
    if (typeof f === "string" && setFont(f)) { style.setProperty("--gpm-font", '"' + f + '", ' + FONT_FALLBACK); }
    else { setFont(null); style.removeProperty("--gpm-font"); }
  }

  part("theme", function (ctx) {
    var theme = ctx.data ? ctx.data.theme : null;
    var group = el("div", "gpm-theme");
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", ctx.t.themeLabel);
    var labels = { light: ctx.t.themeLight, dark: ctx.t.themeDark, system: ctx.t.themeSystem };
    var buttons = {};
    function paint() {
      document.documentElement.setAttribute("data-theme", choice);
      CHOICES.forEach(function (c) { buttons[c].setAttribute("aria-pressed", c === choice ? "true" : "false"); });
      applyTheme(theme);
    }
    CHOICES.forEach(function (c) {
      var b = el("button", null, labels[c]);
      b.type = "button";
      b.setAttribute("data-mode", c);
      b.addEventListener("click", function () { choice = c; saveChoice(c); paint(); });
      buttons[c] = b;
      group.appendChild(b);
    });
    ctx.actions.appendChild(group);
    choice = readChoice();
    paint();
    try {   // «as in the system» follows the system live
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var follow = function () { if (choice === "system") { paint(); } };
      if (mq.addEventListener) { mq.addEventListener("change", follow); } else if (mq.addListener) { mq.addListener(follow); }
    } catch (e) { /* no live following; the choice still works */ }
    ctx.onData(function (snap) { theme = snap && snap.theme ? snap.theme : null; applyTheme(theme); });
  });

  // ---- the registry -----------------------------------------------------------------------------------------------
  // What the files after this one need. `t` is a getter: the words of the page's language, set in init().
  var REGISTRY = {
    part: part, el: el, busy: busy, refusal: refusal, isObj: isObj, str: str, num: num, showDate: showDate, ratio: ratio,
    COLOR: COLOR, LOAD_TIMEOUT: LOAD_TIMEOUT,
    addStrings: function (extra) {
      Object.keys(STRINGS).forEach(function (lang) {
        if (isObj(extra) && isObj(extra[lang])) { Object.keys(extra[lang]).forEach(function (k) { STRINGS[lang][k] = extra[lang][k]; }); }
      });
    }
  };
  Object.defineProperty(REGISTRY, "t", { get: function () { return t; }, enumerable: true });
  Object.defineProperty(REGISTRY, "lang", { get: function () { return pageLang; }, enumerable: true });
  try { Object.defineProperty(window, "__gpmShell", { value: REGISTRY }); } catch (e) { /* the shell runs without a registry for later files */ }

  // ---- the start --------------------------------------------------------------------------------------------------
  function init() {
    var profile;
    try { profile = readProfile(); } catch (e) { return; }
    var lang = profile.lang === "en" ? "en" : "uk";
    t = STRINGS[lang];
    pageLang = lang;
    var header = document.querySelector("header.gpm-shell");
    if (!header) { return; }
    var title = header.querySelector(".gpm-title");
    var actions = header.querySelector(".gpm-actions");
    if (title && profile.title && profile.title[lang]) { title.textContent = profile.title[lang]; }
    if (!actions) { actions = el("div", "gpm-actions"); header.appendChild(actions); }
    var desktopPromise = null, dbPromise = null, last = emptySnapshot(), listeners = [];
    var editsList = null, editsFns = [], editsStarted = false;
    // The last read, for tests and nothing else: a getter, so the page cannot assign it.
    try { Object.defineProperty(window, "__gpm", { value: Object.freeze({ get data() { return last; } }) }); } catch (e) { /* kept */ }
    var ctx;
    ctx = {
      profile: profile, lang: lang, t: t, header: header, actions: actions,
      // the last snapshot read, and a way to hear the next ones: ctx.onData(fn) calls fn(snapshot) on every change
      get data() { return last; },
      onData: function (fn) { if (typeof fn === "function") { listeners.push(fn); } },
      setData: function (snap) {
        last = snap;
        listeners.slice().forEach(function (fn) { try { fn(snap); } catch (e) { /* one listener does not stop the others */ } });
      },
      // The shared edits (collection `edits`) are read once for everyone: ctx.watchEdits(fn) calls fn(list) now (when
      // there is an answer already) and on every change; list = [{id, x, local}], x the document's own object, local
      // true while it is this window's own write not yet confirmed. Whoever reads the documents checks their shape.
      watchEdits: function (fn) {
        if (typeof fn !== "function") { return; }
        editsFns.push(fn);
        if (editsList) { try { fn(editsList); } catch (e) { /* a listener must not break the others */ } }
        if (editsStarted) { return; }
        editsStarted = true;
        ctx.db().then(function (db) {
          if (!db || typeof db.collection !== "function") { return; }
          try {
            db.collection("edits").onSnapshot(function (qs) {
              var list = [];
              try {
                Array.prototype.slice.call(qs && qs.docs ? qs.docs : []).forEach(function (d) {
                  var x = d && typeof d.data === "function" ? d.data() : null;
                  if (isObj(x) && typeof d.id === "string") { list.push({ id: d.id, x: x, local: !!(d.metadata && d.metadata.hasPendingWrites) }); }
                });
              } catch (e) { list = []; }
              editsList = list;
              editsFns.slice().forEach(function (f) { try { f(list); } catch (e) { /* one listener does not stop the others */ } });
            }, function () { /* no edits without the database's leave */ });
          } catch (e) { /* no edits */ }
        });
      },
      db: function () {
        if (!dbPromise) {
          dbPromise = Promise.resolve().then(function () {
            return window.claude && typeof window.claude.use === "function" ? window.claude.use("db") : null;
          }).catch(function () { return null; });
        }
        return dbPromise;
      },
      desktop: function () {
        if (!desktopPromise) {
          desktopPromise = Promise.resolve().then(function () {
            return window.claude && typeof window.claude.use === "function" ? window.claude.use("desktop") : null;
          }).catch(function () { return null; });
        }
        return desktopPromise;
      }
    };
    PARTS.forEach(function (p) {
      try { Promise.resolve(p.run(ctx)).catch(function () {}); } catch (e) { /* this part is off */ }
    });
  }

  function start() { try { init(); } catch (e) { /* the page stays as it is */ } }
  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", start); } else { start(); }
})();
