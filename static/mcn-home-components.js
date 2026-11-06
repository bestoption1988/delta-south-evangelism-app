/* MCN Delta South — rebuilt homepage menu and daily Scripture/Hymn interactions. */
(() => {
  "use strict";
  const menuShell=document.getElementById("mcnMenuShell");
  const menu=document.getElementById("mcnMenuLinks");
  const nav=document.querySelector(".mcn-primary-nav");
  const fellowship=document.getElementById("mcnFellowshipsDropdown");
  const fellowshipButton=fellowship?.querySelector(".mcn-nav-drop-toggle");

  const setMenuOpen=(open)=>{ if(menuShell) menuShell.open=!!open; };
  fellowshipButton?.addEventListener("click",(event)=>{
    event.preventDefault();
    event.stopPropagation();
    const open=fellowship.classList.toggle("is-open");
    fellowshipButton.setAttribute("aria-expanded",String(open));
  });
  menu?.addEventListener("click",(event)=>{
    const link=event.target.closest("a");
    if(link){
      if(!fellowship?.contains(link)){
        fellowship?.classList.remove("is-open");
        fellowshipButton?.setAttribute("aria-expanded","false");
      }
      setMenuOpen(false);
    }
  });
  document.addEventListener("click",(event)=>{
    if(nav&&!nav.contains(event.target))setMenuOpen(false);
    if(fellowship&&!fellowship.contains(event.target)){
      fellowship.classList.remove("is-open");
      fellowshipButton?.setAttribute("aria-expanded","false");
    }
  });
  document.addEventListener("keydown",(event)=>{
    if(event.key==="Escape"){
      setMenuOpen(false);
      fellowship?.classList.remove("is-open");
      fellowshipButton?.setAttribute("aria-expanded","false");
      const active=document.querySelector(".mcn-reading-dialog:not([hidden])");
      if(active)closeDialog(active);
    }
  });
  window.addEventListener("resize",()=>{
    if(window.matchMedia("(min-width: 701px)").matches)setMenuOpen(false);
  });

  const dialogs=[...document.querySelectorAll(".mcn-reading-dialog")];
  let lastTrigger=null;
  function closeDialog(dialog){
    if(!dialog)return;
    dialog.hidden=true;
    dialog.setAttribute("aria-hidden","true");
    document.body.classList.remove("mcn-reading-open");
    dialog.querySelectorAll("audio").forEach(audio=>audio.pause());
    if(lastTrigger){lastTrigger.focus({preventScroll:true});lastTrigger=null;}
  }
  document.querySelectorAll("[data-mcn-reading-open]").forEach(trigger=>{
    trigger.addEventListener("click",()=>{
      const dialog=document.getElementById(trigger.dataset.mcnReadingOpen);
      if(!dialog)return;
      dialogs.forEach(item=>{if(item!==dialog)closeDialog(item);});
      lastTrigger=trigger;
      dialog.hidden=false;
      dialog.setAttribute("aria-hidden","false");
      document.body.classList.add("mcn-reading-open");
      const panel=dialog.querySelector(".mcn-reading-panel");
      if(panel)panel.scrollTop=0;
      dialog.querySelector(".mcn-reading-close")?.focus({preventScroll:true});
    });
  });
  dialogs.forEach(dialog=>{
    dialog.querySelector(".mcn-reading-close")?.addEventListener("click",()=>closeDialog(dialog));
    dialog.addEventListener("click",event=>{if(event.target===dialog)closeDialog(dialog);});
  });
})();
