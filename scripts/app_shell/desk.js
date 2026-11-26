(function () {
  "use strict";
  // What the installed app's window adds: the application menu, the badge on the icon, the menu-bar (tray) item,
  // notifications, the permissions panel and the app's icon. Fixed bytes, no data in it. Everything here starts only in
  // an installed app window (`desktop` with `permissions`); in a browser none of it renders and nothing errors. A
  // permission is asked one at a time, from a button press, with a 30 s timeout; a feature whose permission is not
  // granted stays off silently and switches on at once when the permission comes. The team-edits feed (`@edits`) reads
  // the artifact's `edits` collection through the one shared subscription of the core (ctx.watchEdits) and needs no
  // desktop; the badge and the notifications read the same list.

  var S = window.__gpmShell;
  if (!S || !S.blocks) { return; }
  var el = S.el, isObj = S.isObj, str = S.str, num = S.num;

  S.addStrings({
    uk: {
      permsToggle: "Дозволи",
      permsTitle: "Дозволи",
      permNotifications: "Сповіщення",
      permMenuBar: "Рядок меню",
      permAllow: "Дозволити",
      permSettings: "Налаштування",
      stGranted: "дозволено",
      stDenied: "не дозволено",
      stUnavailable: "недоступно тут",
      stPrompt: "ще не запитано",
      stNoAnswer: "немає відповіді — спробуй ще раз",
      iconLater: "іконка застосується після перевстановлення",
      menuEdit: "Редагувати",
      newEdit: "Нова правка на карті «%s»",
      stageWarn: "Етап «%s»: увага — на %d% нижче за базову лінію",
      stageCrit: "Етап «%s»: критично — на %d% нижче за базову лінію",
      editRow: "змінено рядок",
      editAdd: "додано рядок",
      editRemove: "рядок прибрано"
    },
    en: {
      permsToggle: "Permissions",
      permsTitle: "Permissions",
      permNotifications: "Notifications",
      permMenuBar: "Menu bar",
      permAllow: "Allow",
      permSettings: "Settings",
      stGranted: "allowed",
      stDenied: "not allowed",
      stUnavailable: "unavailable here",
      stPrompt: "not asked yet",
      stNoAnswer: "no answer — try again",
      iconLater: "the icon applies after reinstalling",
      menuEdit: "Edit",
      newEdit: "New edit on the map «%s»",
      stageWarn: "Stage «%s»: warning — %d% below baseline",
      stageCrit: "Stage «%s»: critical — %d% below baseline",
      editRow: "row edited",
      editAdd: "row added",
      editRemove: "row removed"
    }
  });

  var ASK_TIMEOUT = 30000;                       // ms: a permission that does not answer in this time is «no answer»
  var PERMS = ["notifications", "menu-bar"];     // the permissions of a profile this file handles
  var GLYPHS = ["journey", "os", "chart"];       // the same as GLYPHS in app_shell.py
  var RANK = { ok: 0, warn: 1, crit: 2 };
  var SEEN_KEY = "gpm-seen";
  var DEFAULT_ACCENT = "#2f6fde";
  var MAX_NOTE = 300, MAX_TITLE = 30, MAX_ICON_BYTES = 256 * 1024;

  function fmt(template) {
    var args = Array.prototype.slice.call(arguments, 1), i = 0;
    return template.replace(/%[sd]/g, function () { return String(args[i++]); });
  }
  function has(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }
  function cut(text, max) { return text.length > max ? text.slice(0, max - 1) + "…" : text; }

  // ---- the team's edits: one list for the feed, the badge and the notifications ---------------------------------------
  var edits = { list: [], loaded: false, fns: [] };

  // [{id, map, kind: row|add|remove, by, at, local}] from the shared list; a document of no known kind is skipped
  function cleanEdits(raw) {
    var out = [];
    raw.forEach(function (d) {
      var x = d.x, map = str(x.map, 200);
      if (!map || (x.kind !== "row" && x.kind !== "add")) { return; }
      var kind = x.kind === "add" ? "add" : (isObj(x.edit) && x.edit.remove === true ? "remove" : "row");
      out.push({ id: d.id, map: map, kind: kind, by: typeof x.by === "string" ? x.by : "", at: typeof x.at === "string" ? x.at : "", local: !!d.local });
    });
    return out;
  }
  function onEdits(fn) {
    edits.fns.push(fn);
    if (edits.loaded) { try { fn(edits.list); } catch (e) { /* one listener does not stop the others */ } }
  }

  // The feed block (source @edits): one item per document still in the collection — the map's name, what kind of change
  // in words, when; newest first; never a person. Every node made is kept and redrawn live while it is in the page.
  var feeds = [];
  function fillFeed(f) {
    while (f.box.firstChild) { f.box.removeChild(f.box.firstChild); }
    var words = { row: S.t.editRow, add: S.t.editAdd, remove: S.t.editRemove };
    var list = edits.list.slice().sort(function (a, b) { return a.at < b.at ? 1 : a.at > b.at ? -1 : 0; }).map(function (e) {
      var item = { title: e.map, note: words[e.kind] };
      if (/^\d{4}-\d{2}-\d{2}/.test(e.at)) { item.at = e.at; }
      return item;
    });
    var ul = S.blocks.feed({ items: list }, f.view, {});
    if (ul) { f.box.appendChild(ul); } else { f.box.appendChild(el("p", "gpm-placeholder", S.t.editsPlaceholder)); }
  }
  S.sources["@edits"] = function (view) {
    var f = { box: el("div", "gpm-edits"), view: view };
    feeds.push(f);
    fillFeed(f);
    return f.box;
  };
  S.part("edits", function (ctx) {
    ctx.watchEdits(function (raw) {
      edits.list = cleanEdits(raw);
      edits.loaded = true;
      feeds = feeds.filter(function (f) { return document.body.contains(f.box); });
      feeds.forEach(function (f) { try { fillFeed(f); } catch (e) { /* the feed stays as it was */ } });
      edits.fns.slice().forEach(function (fn) { try { fn(edits.list); } catch (e) { /* one listener does not stop the others */ } });
    });
  });

  // ---- the icon -------------------------------------------------------------------------------------------------------
  function modeNow() {
    var a = document.documentElement.getAttribute("data-theme");
    if (a === "light" || a === "dark") { return a; }
    try { return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; } catch (e) { return "light"; }
  }
  function accentOf(theme) {
    var side = isObj(theme) && isObj(theme[modeNow()]) ? theme[modeNow()] : null;
    return side && typeof side.accent === "string" && S.COLOR.test(side.accent) ? side.accent : DEFAULT_ACCENT;
  }
  function roundRect(g, x, y, w, h, r) {
    g.beginPath();
    g.moveTo(x + r, y);
    g.arcTo(x + w, y, x + w, y + h, r);
    g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r);
    g.arcTo(x, y, x + w, y, r);
    g.closePath();
  }
  // drawIcon(glyph, theme) -> a 256×256 PNG data URL under 256 KB: the glyph on the theme's accent; null for an unknown
  // glyph or when the drawing is not possible
  function drawIcon(glyph, theme) {
    if (GLYPHS.indexOf(glyph) < 0) { return null; }
    try {
      var c = document.createElement("canvas");
      c.width = 256;
      c.height = 256;
      var g = c.getContext("2d");
      if (!g) { return null; }
      var bg = accentOf(theme);
      var fg = S.ratio("#ffffff", bg) >= S.ratio("#0d1117", bg) ? "#ffffff" : "#0d1117";
      g.fillStyle = bg;
      roundRect(g, 0, 0, 256, 256, 56);
      g.fill();
      g.fillStyle = fg;
      g.strokeStyle = fg;
      g.lineWidth = 14;
      g.lineJoin = "round";
      g.lineCap = "round";
      if (glyph === "journey") {
        var pts = [[56, 176], [104, 96], [152, 152], [200, 72]];
        g.beginPath();
        pts.forEach(function (p, i) { if (i) { g.lineTo(p[0], p[1]); } else { g.moveTo(p[0], p[1]); } });
        g.stroke();
        pts.forEach(function (p) { g.beginPath(); g.arc(p[0], p[1], 18, 0, 2 * Math.PI); g.fill(); });
      } else if (glyph === "os") {
        [[60, 60], [140, 60], [60, 140], [140, 140]].forEach(function (p) { roundRect(g, p[0], p[1], 56, 56, 12); g.fill(); });
      } else {
        [[62, 50], [112, 90], [162, 130]].forEach(function (b) { roundRect(g, b[0], 196 - b[1], 36, b[1], 6); g.fill(); });
      }
      var url = c.toDataURL("image/png");
      return url.indexOf("data:image/png;base64,") === 0 && url.length * 3 / 4 <= MAX_ICON_BYTES ? url : null;
    } catch (e) { return null; }
  }
  S.drawIcon = drawIcon;

  // ---- what the snapshot says to the tray and the notifications --------------------------------------------------------
  function sectionsOf(snap, test) {
    var out = [];
    if (!snap || !isObj(snap.sections)) { return out; }
    Object.keys(snap.sections).sort().forEach(function (id) {
      var sec = snap.sections[id];
      if (sec && test(sec.section)) { out.push({ id: id, sec: sec }); }
    });
    return out;
  }
  function isMap(name) { return name === "map" || (typeof name === "string" && name.indexOf("map.") === 0); }

  // the weakest journey of the product chosen, or the lowest across products in «Усі»: {title, score} or null
  function weakestOf(snap, product) {
    var best = null;
    sectionsOf(snap, function (n) { return n === "portfolio"; }).forEach(function (x) {
      var w = x.sec.data.weakest;
      if (product && x.sec.product !== product) { return; }
      if (!isObj(w) || !str(w.title, 100) || num(w.score) === null) { return; }
      if (!best || w.score < best.score) { best = { title: w.title, score: w.score }; }
    });
    return best;
  }

  // ---- the part: only in an installed app's window ---------------------------------------------------------------------
  S.part("desk", function (ctx) {
    return ctx.desktop().then(function (desktop) {
      if (!desktop || !desktop.permissions || typeof desktop.permissions.state !== "function") { return; }
      return Promise.all([readStates(desktop), viewerId()]).then(function (r) { run(ctx, desktop, r[0], r[1]); });
    });
  });

  // the state of every permission, or null when it cannot be read (the panel and the features that need one stay off)
  function readStates(desktop) {
    return Promise.resolve().then(function () { return desktop.permissions.state(); }).then(function (rec) {
      return isObj(rec) ? rec : null;
    }, function () { return null; });
  }
  function viewerId() {
    return Promise.resolve().then(function () {
      return window.claude && typeof window.claude.use === "function" ? window.claude.use("user") : null;
    }).then(function (u) {
      return u && typeof u.id === "function" ? u.id() : null;
    }).then(function (id) { return typeof id === "string" && id ? id : null; }, function () { return null; });
  }

  function run(ctx, desktop, states, me) {
    var profile = ctx.profile, t = S.t;
    var perm = {};                         // what is known of each permission; unknown = off
    PERMS.forEach(function (n) { perm[n] = states && typeof states[n] === "string" ? states[n] : "unknown"; });
    var wanted = (Array.isArray(profile.permissions) ? profile.permissions : []).filter(function (n) { return PERMS.indexOf(n) >= 0; });
    var title = profile.title && typeof profile.title[ctx.lang] === "string" ? profile.title[ctx.lang] : "";
    var listens = Array.isArray(profile.notify) ? profile.notify : [];

    function granted(n) { return perm[n] === "granted" && wanted.indexOf(n) >= 0; }
    function guard(fn) { try { var r = fn(); if (r && typeof r.catch === "function") { r.catch(function () {}); } } catch (e) { /* this feature is off */ } }

    // ---- notifications: only while the permission is granted, only the kinds the profile names
    function notify(kind, text) {
      if (listens.indexOf(kind) < 0 || !granted("notifications") || !desktop.notification) { return false; }
      guard(function () { return desktop.notification.show({ body: cut(String(text), MAX_NOTE) }); });
      return true;
    }
    S.notify = notify;

    // ---- the badge: how many documents of `edits` are still not taken
    var lastBadge = null;
    function setBadge(n) {
      var text = n <= 0 ? "" : n > 99 ? "99+" : String(n);
      if (text === lastBadge || !desktop.app || !desktop.app.dock || typeof desktop.app.dock.setBadge !== "function") { return; }
      lastBadge = text;
      guard(function () { return desktop.app.dock.setBadge(text); });
    }

    // ---- edits.new: a document that appeared after the app loaded, that this viewer did not write
    var known = null;
    onEdits(function (list) {
      if (profile.badge) { setBadge(list.length); }
      var fresh = [];
      list.forEach(function (d) { if (known && !has(known, d.id)) { fresh.push(d); } });
      known = {};
      list.forEach(function (d) { known[d.id] = true; });
      if (!me) { return; }                  // without the viewer's id an own edit cannot be told from another's: say nothing
      fresh.forEach(function (d) { if (d.by !== me && !d.local) { notify("edits.new", fmt(S.t.newEdit, cut(d.map, 120))); } });
    });

    // ---- threshold.crossed: a stage that got worse than the level last seen for this product and stage
    var seen = null;
    function loadSeen() {
      seen = {};
      try {
        var o = JSON.parse(window.localStorage.getItem(SEEN_KEY) || "null");
        if (isObj(o)) { Object.keys(o).forEach(function (k) { if (k.length <= 300 && has(RANK, o[k])) { seen[k] = o[k]; } }); }
      } catch (e) { /* remembered for this session only */ }
    }
    function saveSeen() { try { window.localStorage.setItem(SEEN_KEY, JSON.stringify(seen)); } catch (e) { /* kept in memory */ } }
    function checkThresholds(snap) {
      if (!seen) { loadSeen(); }
      var th = snap && snap.meta ? snap.meta.thresholds : { warning: 0.1, critical: 0.25 };
      var changed = false;
      sectionsOf(snap, function (n) { return n === "funnel"; }).forEach(function (x) {
        if (!Array.isArray(x.sec.data.stages)) { return; }
        x.sec.data.stages.slice(0, 60).forEach(function (st) {
          if (!isObj(st) || !str(st.id, 64)) { return; }
          var v = num(st.value), b = num(st.baseline);
          if (v === null || b === null || b <= 0) { return; }
          var drop = (v - b) / b;
          var level = drop <= -th.critical ? "crit" : drop <= -th.warning ? "warn" : "ok";
          var key = x.sec.product + "|" + st.id;
          var before = has(seen, key) ? seen[key] : null;
          if (before !== null && RANK[level] > RANK[before]) {
            var label = "", products = snap.meta ? snap.meta.products : [];
            if (products.length > 1) {
              products.forEach(function (p) { if (p.id === x.sec.product) { label = " (" + p.label + ")"; } });
            }
            notify("threshold.crossed", fmt(level === "crit" ? S.t.stageCrit : S.t.stageWarn, (str(st.title, 100) || st.id) + label, Math.round(-drop * 100)));
          }
          if (before !== level) { seen[key] = level; changed = true; }
        });
      });
      if (changed) { saveSeen(); }
    }

    // ---- the menu and the tray share the profile's items
    function moduleTitle(id) {
      var mods = Array.isArray(profile.modules) ? profile.modules : [];
      for (var i = 0; i < mods.length; i++) {
        if (mods[i].id === id) { return mods[i].title && typeof mods[i].title[ctx.lang] === "string" ? mods[i].title[ctx.lang] : id; }
      }
      return id;
    }
    function tabShown(id) {
      var tabs = document.querySelectorAll(".gpm-tabs [data-tab]");
      for (var i = 0; i < tabs.length; i++) { if (tabs[i].getAttribute("data-tab") === id) { return true; } }
      return false;
    }
    function editToggle() {
      var root = document.querySelector(".gpm-modules");
      var tg = root && !root.hidden ? root.querySelector(".edit-bar .edit-toggle") : null;
      return tg && tg.offsetParent !== null ? tg : null;
    }
    function mapModule() {
      var mods = Array.isArray(profile.modules) ? profile.modules : [];
      for (var i = 0; i < mods.length; i++) {
        var m = mods[i];
        if (m.block === "map" || (Array.isArray(m.blocks) && m.blocks.some(function (b) { return b.block === "map"; }))) { return m.id; }
      }
      return null;
    }
    function reveal(forTray) {
      if (forTray && desktop.window && typeof desktop.window.show === "function") { guard(function () { return desktop.window.show(); }); }
    }
    // [{label, enabled, click, accelerator?}] from profile.menu in order. `open-in-claude` has no call in the typed API:
    // it is left out.
    function profileItems(forTray) {
      var out = [];
      (Array.isArray(profile.menu) ? profile.menu : []).forEach(function (entry) {
        if (typeof entry === "string") {
          out.push({ label: moduleTitle(entry), enabled: tabShown(entry), click: function () { reveal(forTray); S.openTab(entry); } });
        } else if (isObj(entry) && entry.action === "edit") {
          var item = { label: S.t.menuEdit, enabled: !!editToggle(), click: function () { reveal(forTray); var tg = editToggle(); if (tg) { tg.click(); } } };
          if (!forTray && typeof entry.accel === "string" && /(Cmd|Ctrl|CmdOrCtrl)\+/.test(entry.accel)) { item.accelerator = entry.accel; }
          out.push(item);
        }
      });
      return out;
    }

    var lastMenu = null;
    function updateMenu() {
      if (!desktop.Menu || typeof desktop.Menu.setApplicationMenu !== "function" || !Array.isArray(profile.menu) || !profile.menu.length) { return; }
      var items = profileItems(false);
      if (!items.length) { return; }
      var key = JSON.stringify(items.map(function (i) { return [i.label, i.enabled, i.accelerator || ""]; }));
      if (key === lastMenu) { return; }
      lastMenu = key;
      guard(function () { return desktop.Menu.setApplicationMenu([{ label: title || "App", submenu: items }, { role: "editMenu" }]); });
    }

    var lastTray = null, trayUp = false, iconCache = { key: "", url: null };
    function trayIcon() {
      var glyph = profile.icon && profile.icon.glyph, theme = ctx.data ? ctx.data.theme : null;
      var key = glyph + "|" + accentOf(theme);
      if (iconCache.key !== key) { iconCache = { key: key, url: drawIcon(glyph, theme) }; }
      return iconCache.url;
    }
    function updateTray() {
      if (!isObj(profile.tray) || !desktop.tray || typeof desktop.tray.set !== "function") { return; }
      if (!granted("menu-bar")) {
        if (trayUp && typeof desktop.tray.remove === "function") { guard(function () { return desktop.tray.remove(); }); }
        trayUp = false;
        lastTray = null;
        return;
      }
      var snap = ctx.data, w = weakestOf(snap, S.view().product);
      var heading = w ? w.title + " — " + w.score : title;
      var maps = sectionsOf(snap, isMap).map(function (x) {
        return { label: str(x.sec.data.journey, 200) || x.id, enabled: true, click: function () {
          reveal(true);
          var mod = mapModule();
          if (mod) { S.openTab(mod); }
          if (S.selectMap) { S.selectMap(x.id); }
        } };
      });
      var items = maps.concat(maps.length ? [{ type: "separator" }] : [], profileItems(true));
      var icon = trayIcon();
      var key = JSON.stringify([heading, items.map(function (i) { return [i.label || i.type, i.enabled]; }), icon ? 1 : 0]);
      if (key === lastTray) { return; }
      lastTray = key;
      var opts = { title: cut(heading, MAX_TITLE), toolTip: cut(title, 100), menu: items.map(function (i) {
        return i.type ? { type: i.type } : { label: i.label, enabled: i.enabled, click: i.click };
      }) };
      if (icon) { opts.icon = icon; opts.iconIsTemplate = false; }
      trayUp = true;
      guard(function () { return desktop.tray.set(opts); });
    }

    function updateAll() { updateMenu(); updateTray(); }

    // ---- permissions: one at a time, a button each, 30 s
    function refresh() {
      return readStates(desktop).then(function (rec) {
        if (rec) { PERMS.forEach(function (n) { if (typeof rec[n] === "string") { perm[n] = rec[n]; } }); }
        updateAll();
        return rec;
      });
    }
    // askPermission(name) -> Promise<"granted"|"denied"|"timeout">: ONE name per request, raced against 30 s; a late
    // answer still refreshes the states, so the feature switches on without a reload
    function askPermission(name) {
      var timer = null;
      var raw = Promise.resolve().then(function () { return desktop.permissions.request([name]); });
      var answered = raw.then(function (rec) { return isObj(rec) && rec[name] === "granted" ? "granted" : "denied"; }, function () { return "denied"; });
      raw.then(function () { return refresh(); }, function () {});
      var timeout = new Promise(function (resolve) { timer = setTimeout(function () { resolve("timeout"); }, ASK_TIMEOUT); });
      return Promise.race([answered, timeout]).then(function (r) { clearTimeout(timer); return r; });
    }
    S.askPermission = askPermission;

    var rows = [], iconNote = null, pending = false;
    function stateWord(n) {
      var s = perm[n];
      return s === "granted" ? t.stGranted : s === "denied" ? t.stDenied : s === "unavailable" ? t.stUnavailable : t.stPrompt;
    }
    function paintRows() {
      rows.forEach(function (r) {
        var s = perm[r.name];
        r.state.textContent = stateWord(r.name);
        var offer = s !== "granted" && s !== "unavailable";
        if (offer && !r.btn) {
          r.btn = el("button", null, "");
          r.btn.type = "button";
          r.btn.addEventListener("click", function () { press(r); });
          r.row.insertBefore(r.btn, r.state.nextSibling);
        }
        if (!offer && r.btn) { r.btn.parentNode.removeChild(r.btn); r.btn = null; }
        if (r.btn) { r.btn.textContent = s === "denied" ? t.permSettings : t.permAllow; r.btn.disabled = pending; }
      });
    }
    function press(r) {
      var denied = perm[r.name] === "denied";
      pending = true;
      rows.forEach(function (o) { if (o.btn) { o.btn.disabled = true; } });
      var job = denied ? Promise.resolve().then(function () { return desktop.permissions.manage(); })
        : askPermission(r.name).then(function (answer) {
          if (answer === "granted") { return; }
          throw S.refusal(answer === "timeout" ? t.stNoAnswer : t.stDenied);
        });
      S.busy(r.btn, job).then(function () { pending = false; return refresh(); }).then(paintRows, paintRows);
    }
    function buildPanel() {
      if (!states || !wanted.length || !ctx.header.parentNode) { return; }
      var toggle = el("button", "gpm-perms-toggle", t.permsToggle);
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      var panel = el("section", "gpm-perms");
      panel.hidden = true;
      panel.setAttribute("aria-label", t.permsTitle);
      panel.appendChild(el("h2", null, t.permsTitle));
      wanted.forEach(function (name) {
        var row = el("div", "gpm-perm");
        row.setAttribute("data-perm", name);
        var r = { name: name, row: row, state: el("span", "gpm-perm-state"), btn: null };
        row.appendChild(el("span", "gpm-perm-name", name === "notifications" ? t.permNotifications : t.permMenuBar));
        row.appendChild(r.state);
        panel.appendChild(row);
        rows.push(r);
      });
      iconNote = el("p", "gpm-icon-note", t.iconLater);
      iconNote.hidden = true;
      panel.appendChild(iconNote);
      toggle.addEventListener("click", function () {
        panel.hidden = !panel.hidden;
        toggle.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      });
      ctx.actions.appendChild(toggle);
      ctx.header.parentNode.insertBefore(panel, ctx.header.nextSibling);
      paintRows();
    }
    buildPanel();

    // ---- states are read again, never asked: "unavailable" can mean "not known yet" (sign-in), and the person can grant
    // a permission from Claude's own menu. On focus and when the window shows again; while one reads "unavailable", a
    // bounded retry (5 attempts, 1 s doubling to 16 s), then no timer at all.
    var attempts = 0, retryTimer = null;
    function scheduleRetry() {
      if (retryTimer || attempts >= 5 || !wanted.some(function (n) { return perm[n] === "unavailable"; })) { return; }
      retryTimer = setTimeout(function () { retryTimer = null; attempts++; resync(); }, 1000 * Math.pow(2, attempts));
    }
    function resync() {
      if (pending) { return; }
      refresh().then(function () { paintRows(); scheduleRetry(); }, function () {});
    }
    window.addEventListener("focus", resync);
    document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") { resync(); } });
    scheduleRetry();

    // ---- the icon: drawn on the theme's accent, handed to the Dock; an installed copy that did not take it is told
    var iconAccent = null;
    function setIcon() {
      var dock = desktop.app && desktop.app.dock;
      if (!dock || typeof dock.setIcon !== "function") { return; }
      var theme = ctx.data ? ctx.data.theme : null, accent = accentOf(theme);
      if (accent === iconAccent) { return; }
      var url = drawIcon(profile.icon && profile.icon.glyph, theme);
      if (!url) { return; }
      iconAccent = accent;
      guard(function () {
        return dock.setIcon(url).then(function (r) { if (iconNote) { iconNote.hidden = !(isObj(r) && r.written === false); } });
      });
    }

    // ---- start: the menu, the icon, the tray; then keep them current
    updateAll();
    setIcon();
    checkThresholds(ctx.data);
    ctx.onData(function (snap) {
      checkThresholds(snap);
      setIcon();
      updateAll();
    });
    S.onView(updateAll);
    try {
      var root = document.querySelector(".gpm-modules");
      if (root && typeof MutationObserver === "function") {
        var queued = false;
        new MutationObserver(function () {
          if (queued) { return; }
          queued = true;
          Promise.resolve().then(function () { queued = false; updateAll(); });
        }).observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
      }
    } catch (e) { /* the menu follows the data and the tab clicks only */ }
  }
})();
