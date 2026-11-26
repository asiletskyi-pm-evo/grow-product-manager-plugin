(function () {
  "use strict";
  // The app shell: one script, fixed bytes, no data in it. The profile comes from #gpm-profile; the parts below are
  // started one by one, each in its own try/catch — a part that fails or is refused switches itself off silently.

  var STRINGS = {
    uk: {
      install: "Встановити як застосунок",
      busy: "Виконується…",
      done: "Готово",
      cancelled: "Скасовано: ви відмовились встановлювати",
      unavailable: "Тут встановити не вийде",
      failed: "Не вдалося встановити",
      refused: "Відмовлено"
    },
    en: {
      install: "Install as an app",
      busy: "Working…",
      done: "Done",
      cancelled: "Cancelled: you declined to install",
      unavailable: "Cannot be installed here",
      failed: "Installation failed",
      refused: "Refused"
    }
  };
  var PARTS = [];
  var t = STRINGS.uk;            // the words of the page's language, set in init()

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
          var asked = desktop.install.request().then(function (answer) {
            if (answer === "installed") { return; }
            if (answer === "cancelled") { throw refusal(t.cancelled); }
            throw refusal(answer === "unavailable" ? t.unavailable : t.failed);
          });
          busy(button, asked).then(function (ok) { if (ok) { button.disabled = true; } });
        });
      });
    });
  });

  // ---- the start --------------------------------------------------------------------------------------------------
  function init() {
    var profile;
    try { profile = readProfile(); } catch (e) { return; }
    var lang = profile.lang === "en" ? "en" : "uk";
    t = STRINGS[lang];
    var header = document.querySelector("header.gpm-shell");
    if (!header) { return; }
    var title = header.querySelector(".gpm-title");
    var actions = header.querySelector(".gpm-actions");
    if (title && profile.title && profile.title[lang]) { title.textContent = profile.title[lang]; }
    if (!actions) { actions = el("div", "gpm-actions"); header.appendChild(actions); }
    var desktopPromise = null;
    var ctx = {
      profile: profile, lang: lang, t: t, header: header, actions: actions,
      desktop: function () {
        if (!desktopPromise) {
          desktopPromise = Promise.resolve().then(function () {
            return window.claude && typeof window.claude.use === "function" ? window.claude.use("desktop") : null;
          }).catch(function () { return null; });
        }
        return desktopPromise;
      }
    };
    return PARTS.reduce(function (chain, p) {
      return chain.then(function () {
        try { return Promise.resolve(p.run(ctx)).catch(function () {}); } catch (e) { return undefined; }
      });
    }, Promise.resolve());
  }

  try { init(); } catch (e) { /* the page stays as it is */ }
})();
