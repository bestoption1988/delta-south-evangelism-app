/* Explicit click handlers: reliable in Android System WebView and mobile browsers. */
(() => {
  "use strict";
  const menu = document.querySelector(".ds-menu");
  if (!menu) return;
  const trigger = menu.querySelector(".ds-menu-trigger");
  const panel = menu.querySelector(".ds-menu-panel");
  const groupTrigger = menu.querySelector(".ds-menu-group-trigger");
  const submenu = menu.querySelector(".ds-menu-submenu");
  if (!trigger || !panel) return;

  const isMobile = () => window.matchMedia("(max-width: 700px)").matches;
  const setMenuOpen = (open) => {
    trigger.setAttribute("aria-expanded", String(open));
    panel.hidden = isMobile() ? !open : false;
    menu.classList.toggle("is-open", open);
  };
  const setGroupOpen = (open) => {
    if (!groupTrigger || !submenu) return;
    groupTrigger.setAttribute("aria-expanded", String(open));
    submenu.hidden = !open;
  };

  setMenuOpen(!isMobile());
  setGroupOpen(false);

  trigger.addEventListener("click", () => {
    if (!isMobile()) return;
    setMenuOpen(trigger.getAttribute("aria-expanded") !== "true");
  });

  if (groupTrigger) {
    groupTrigger.addEventListener("click", () => {
      setGroupOpen(groupTrigger.getAttribute("aria-expanded") !== "true");
    });
  }

  panel.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (link && isMobile()) setMenuOpen(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isMobile()) {
      setMenuOpen(false);
      setGroupOpen(false);
      trigger.focus();
    }
  });

  window.addEventListener("resize", () => {
    setMenuOpen(!isMobile());
    if (!isMobile()) setGroupOpen(false);
  }, { passive: true });
})();