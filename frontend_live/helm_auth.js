/* HELM read-auth client helper (AC-3 / IA-2).
 *
 * When the API has read-auth ENABLED, GET /api/* requires a read token. This patches
 * window.fetch to attach the token (from localStorage) as a Bearer header on
 * same-origin /api/ requests. On a 401 it prompts once, stores the token, and retries.
 *
 * INERT when read-auth is disabled: no /api call returns 401, so nothing ever prompts
 * and every console behaves exactly as before. Safe to ship ahead of the cutover.
 *
 * The token is entered by the operator once per device and kept client-side only —
 * it is NEVER embedded in served HTML (that would let anyone who can load the page
 * read it, defeating the gate).
 */
(function () {
  "use strict";
  var KEY = "helm_read_token";
  var origFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!origFetch) return;

  function tok() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  function setTok(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function isApiGet(url, init) {
    var method = (init && init.method ? init.method : "GET").toUpperCase();
    if (method !== "GET") return false;            // read-auth only gates GET
    try {
      var u = new URL(url, location.href);
      return u.origin === location.origin && u.pathname.indexOf("/api/") === 0;
    } catch (e) { return false; }
  }

  function withToken(init, t) {
    init = Object.assign({}, init || {});
    var h = new Headers(init.headers || {});
    if (t) h.set("Authorization", "Bearer " + t);
    init.headers = h;
    return init;
  }

  window.fetch = function (input, init) {
    var url = (typeof input === "string") ? input : (input && input.url) || "";
    if (!isApiGet(url, init)) return origFetch(input, init);

    return origFetch(input, withToken(init, tok())).then(function (r) {
      if (r.status !== 401) return r;
      var entered = window.prompt("HELM read token required (read-only access):", "");
      if (!entered) return r;                       // cancelled -> surface the 401
      var t = entered.trim();
      setTok(t);
      return origFetch(input, withToken(init, t));   // retry once with the new token
    });
  };

  // Small manual API for setting/clearing the token from the console if needed.
  window.HELMAuth = {
    setToken: function (v) { setTok((v || "").trim()); },
    clear: function () { try { localStorage.removeItem(KEY); } catch (e) {} },
    hasToken: function () { return !!tok(); }
  };
})();
