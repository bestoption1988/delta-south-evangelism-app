(function(){
"use strict";
function init(){
var modal=document.getElementById("dailyReadingModal"),title=document.getElementById("dailyReadingModalTitle"),body=document.getElementById("dailyReadingModalBody");
if(!modal||!title||!body||modal.dataset.ready==="1")return;
modal.dataset.ready="1";
var lastTrigger=null;
function close(){modal.hidden=true;document.body.classList.remove("daily-reading-modal-open");if(lastTrigger)lastTrigger.focus();}
document.querySelectorAll("[data-reading-source]").forEach(function(trigger){
trigger.addEventListener("click",function(){
var source=document.getElementById(trigger.getAttribute("data-reading-source"));if(!source)return;
lastTrigger=trigger;title.textContent=trigger.getAttribute("data-reading-title")||"Daily Reading";body.textContent=source.textContent.trim();body.scrollTop=0;modal.hidden=false;document.body.classList.add("daily-reading-modal-open");window.setTimeout(function(){body.focus();},30);
});
});
modal.querySelectorAll("[data-daily-close]").forEach(function(el){el.addEventListener("click",close);});
document.addEventListener("keydown",function(event){if(event.key==="Escape"&&!modal.hidden)close();});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();