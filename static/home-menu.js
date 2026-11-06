/* Desktop starts with its horizontal navigation expanded; mobile starts collapsed.
   The mobile menu itself opens natively through the HTML details/summary control. */
(() => {
  "use strict";
  const menu = document.querySelector(".ds-menu");
  if (!menu) return;
  const applyLayout = () => {
    menu.open = window.matchMedia("(min-width: 701px)").matches;
  };
  applyLayout();
  window.addEventListener("resize", applyLayout, {passive: true});
})();