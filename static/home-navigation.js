/* Independent close behaviour for the native HTML details menu. Opening does not rely on JavaScript. */
(() => {
  "use strict";
  const root=document.getElementById("dsMainMenu");
  if(!root)return;
  root.addEventListener("click",event=>{
    const link=event.target.closest("a");
    if(link){
      root.open=false;
      const fellowship=document.getElementById("dsFellowshipsGroup");
      if(fellowship)fellowship.open=false;
    }
  });
  document.addEventListener("click",event=>{
    if(!root.contains(event.target))root.open=false;
  });
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"){
      root.open=false;
      const fellowship=document.getElementById("dsFellowshipsGroup");
      if(fellowship)fellowship.open=false;
    }
  });
})();
