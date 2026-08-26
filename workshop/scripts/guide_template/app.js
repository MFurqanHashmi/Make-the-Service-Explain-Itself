/* Progressive enhancement only: with scripts off the page stays complete. */
(function () {
  "use strict";

  var guard = function (name, fn) {
    try { fn(); } catch (error) { console.warn(name + " unavailable:", error); }
  };

  /* Copy buttons ------------------------------------------------------- */
  guard("copy", function () {
    document.querySelectorAll(".copy").forEach(function (button) {
      button.hidden = false;
      button.addEventListener("click", function () {
        var text = button.getAttribute("data-copy") || "";
        var done = function () {
          button.textContent = "Copied";
          button.setAttribute("data-copied", "");
          window.setTimeout(function () {
            button.textContent = "Copy";
            button.removeAttribute("data-copied");
          }, 1500);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, fallback);
        } else {
          fallback();
        }
        function fallback() {
          var area = document.createElement("textarea");
          area.value = text;
          area.setAttribute("readonly", "");
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();
          try { document.execCommand("copy"); done(); } catch (error) { /* ignore */ }
          document.body.removeChild(area);
        }
      });
    });
  });

  /* Sidebar: scroll-spy and the investigation-state readout ------------- */
  guard("scroll-spy", function () {
    var steps = Array.prototype.slice.call(document.querySelectorAll(".step[data-step]"));
    var links = {};
    document.querySelectorAll("[data-nav]").forEach(function (link) {
      links[link.getAttribute("data-nav")] = link;
    });
    var readout = document.querySelectorAll("[data-readout]");
    if (!steps.length) { return; }

    var apply = function (step) {
      Object.keys(links).forEach(function (key) { links[key].classList.remove("current"); });
      var link = links[step.id];
      if (link) {
        link.classList.add("current");
        if (link.scrollIntoView) { link.scrollIntoView({ block: "nearest" }); }
      }
      readout.forEach(function (item) {
        var answered = step.getAttribute("data-" + item.getAttribute("data-readout")) || "unknown";
        item.setAttribute("data-answered", answered);
        item.querySelector(".readout-glyph").textContent =
          answered === "yes" ? "✅" : answered === "no" ? "❌" : "—";
      });
    };

    var current = null;
    var pick = function () {
      var best = steps[0];
      steps.forEach(function (step) {
        if (step.getBoundingClientRect().top <= window.innerHeight * 0.35) { best = step; }
      });
      if (best !== current) { current = best; apply(best); }
    };

    var ticking = false;
    window.addEventListener("scroll", function () {
      if (ticking) { return; }
      ticking = true;
      window.requestAnimationFrame(function () { pick(); ticking = false; });
    }, { passive: true });
    pick();
  });

  /* Mobile navigation --------------------------------------------------- */
  guard("nav-toggle", function () {
    var toggle = document.querySelector(".nav-toggle");
    var sidebar = document.getElementById("sidebar");
    if (!toggle || !sidebar) { return; }
    toggle.addEventListener("click", function () {
      var open = sidebar.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    sidebar.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        sidebar.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  });

  /* Printing: paper cannot be clicked, so every answer is opened for it --- */
  guard("print", function () {
    var opened = [];
    window.addEventListener("beforeprint", function () {
      opened = Array.prototype.slice.call(document.querySelectorAll("details:not([open])"));
      opened.forEach(function (item) { item.open = true; });
    });
    window.addEventListener("afterprint", function () {
      opened.forEach(function (item) { item.open = false; });
      opened = [];
    });
  });

  /* Screenshot lightbox -------------------------------------------------- */
  guard("lightbox", function () {
    var box = document.getElementById("lightbox");
    if (!box) { return; }
    var image = box.querySelector("img");
    var close = box.querySelector(".lightbox-close");
    var opener = null;

    var hide = function () {
      box.hidden = true;
      image.removeAttribute("src");
      if (opener) { opener.focus(); opener = null; }
    };

    document.querySelectorAll(".shot-zoom").forEach(function (button) {
      button.addEventListener("click", function () {
        var source = button.querySelector("img");
        opener = button;
        image.src = source.getAttribute("src");
        image.alt = source.getAttribute("alt") || "";
        box.hidden = false;
        close.focus();
      });
    });

    close.addEventListener("click", hide);
    box.addEventListener("click", function (event) {
      if (event.target === box) { hide(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !box.hidden) { hide(); }
      if (event.key === "Tab" && !box.hidden) { event.preventDefault(); close.focus(); }
    });
  });
})();
