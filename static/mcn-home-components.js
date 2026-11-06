/* Scripture and Hymn of the Day dialogs only. Navigation has no JavaScript dependency. */
(() => {
  "use strict";
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
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"){
      const active=document.querySelector(".mcn-reading-dialog:not([hidden])");
      if(active)closeDialog(active);
    }
  });
})();