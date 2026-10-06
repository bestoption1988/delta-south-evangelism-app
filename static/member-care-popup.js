(function () {
  "use strict";

  if (window.__DS_MEMBER_CARE_POPUP__) return;
  window.__DS_MEMBER_CARE_POPUP__ = true;

  let currentThread = null;
  let pollTimer = null;

  function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, function (c) {
      return ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      })[c];
    });
  }

  async function careApi(url, options) {
    const r = await fetch(url, Object.assign({
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" }
    }, options || {}));

    let data = {};
    try {
      data = await r.json();
    } catch (_) {}

    if (!r.ok) {
      throw new Error(data.error || "Member Care request failed.");
    }

    return data;
  }

  function injectStyle() {
    if (document.getElementById("ds-member-care-popup-style")) return;

    const style = document.createElement("style");
    style.id = "ds-member-care-popup-style";

    style.textContent = `
      #dsMemberCareFloat{
        position:fixed;
        right:18px;
        bottom:20px;
        width:62px;
        height:62px;
        border:0;
        border-radius:50%;
        background:#086b3c;
        color:#fff;
        font-size:27px;
        box-shadow:0 8px 28px rgba(0,0,0,.25);
        z-index:99990;
        cursor:pointer;
      }

      #dsMemberCareUnread{
        position:absolute;
        right:-2px;
        top:-2px;
        min-width:21px;
        height:21px;
        padding:0 5px;
        border-radius:20px;
        background:#dc2626;
        color:#fff;
        font:bold 12px Arial;
        display:none;
        align-items:center;
        justify-content:center;
      }

      #dsMemberCareOverlay{
        position:fixed;
        inset:0;
        background:rgba(0,0,0,.48);
        z-index:99991;
        display:none;
        align-items:flex-end;
        justify-content:center;
      }

      #dsMemberCarePopup{
        width:min(620px,100%);
        height:min(760px,92vh);
        background:#fff;
        border-radius:22px 22px 0 0;
        box-shadow:0 -10px 40px rgba(0,0,0,.28);
        overflow:hidden;
        display:flex;
        flex-direction:column;
      }

      .ds-care-head{
        background:#086b3c;
        color:#fff;
        padding:16px 18px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
      }

      .ds-care-head strong{
        font-size:18px;
        display:block;
      }

      .ds-care-head small{
        opacity:.85;
      }

      .ds-care-close{
        border:0;
        background:rgba(255,255,255,.15);
        color:#fff;
        width:38px;
        height:38px;
        border-radius:50%;
        font-size:22px;
        cursor:pointer;
      }

      .ds-care-toolbar{
        padding:10px 14px;
        border-bottom:1px solid #e5e7eb;
        display:flex;
        gap:8px;
      }

      .ds-care-toolbar button{
        border:0;
        border-radius:10px;
        padding:9px 12px;
        cursor:pointer;
      }

      .ds-care-new{
        background:#086b3c;
        color:#fff;
      }

      .ds-care-refresh{
        background:#edf3ef;
        color:#14532d;
      }

      #dsCareList{
        overflow:auto;
        flex:1;
        padding:10px;
      }

      .ds-care-thread{
        padding:14px;
        margin-bottom:9px;
        border:1px solid #e3e8e5;
        border-radius:14px;
        cursor:pointer;
        background:#fff;
      }

      .ds-care-thread:hover{
        background:#f5faf7;
      }

      .ds-care-thread-top{
        display:flex;
        justify-content:space-between;
        gap:10px;
        font-weight:700;
      }

      .ds-care-thread-subject{
        margin-top:5px;
        color:#475569;
      }

      .ds-care-thread-meta{
        margin-top:7px;
        font-size:12px;
        color:#64748b;
      }

      .ds-care-status{
        display:inline-block;
        padding:3px 8px;
        border-radius:20px;
        background:#dcfce7;
        color:#166534;
        font-size:11px;
      }

      #dsCareConversation{
        display:none;
        flex:1;
        min-height:0;
        flex-direction:column;
      }

      .ds-care-conversation-head{
        padding:12px 15px;
        border-bottom:1px solid #e5e7eb;
      }

      .ds-care-back{
        border:0;
        background:none;
        color:#086b3c;
        font-weight:700;
        cursor:pointer;
        padding:4px 0 9px;
      }

      #dsCareMessages{
        flex:1;
        overflow:auto;
        padding:14px;
        background:#f7faf8;
      }

      .ds-care-message{
        max-width:82%;
        padding:10px 12px;
        border-radius:15px;
        margin-bottom:10px;
        line-height:1.4;
        white-space:pre-wrap;
        word-break:break-word;
      }

      .ds-care-message.member{
        margin-left:auto;
        background:#d9f4e5;
        color:#123b28;
        border-bottom-right-radius:4px;
      }

      .ds-care-message.staff{
        margin-right:auto;
        background:#fff;
        border:1px solid #e1e7e3;
        border-bottom-left-radius:4px;
      }

      .ds-care-message small{
        display:block;
        margin-top:5px;
        opacity:.6;
        font-size:10px;
      }

      #dsCareReply{
        border-top:1px solid #e5e7eb;
        padding:10px;
        background:#fff;
      }

      #dsCareReplyForm{
        display:flex;
        gap:8px;
      }

      #dsCareReplyInput{
        flex:1;
        min-height:44px;
        max-height:110px;
        resize:vertical;
        border:1px solid #cfd8d2;
        border-radius:12px;
        padding:10px;
        font:inherit;
      }

      #dsCareReplyForm button{
        width:82px;
        border:0;
        border-radius:12px;
        background:#086b3c;
        color:#fff;
        font-weight:700;
      }

      #dsCareNewForm{
        display:none;
        padding:15px;
        overflow:auto;
      }

      #dsCareNewForm input,
      #dsCareNewForm textarea,
      #dsCareNewForm select{
        width:100%;
        box-sizing:border-box;
        margin:5px 0 12px;
        padding:11px;
        border:1px solid #cfd8d2;
        border-radius:10px;
        font:inherit;
      }

      #dsCareNewForm textarea{
        min-height:110px;
      }

      .ds-care-form-actions{
        display:flex;
        gap:8px;
      }

      .ds-care-form-actions button{
        flex:1;
        padding:11px;
        border:0;
        border-radius:10px;
        cursor:pointer;
        font-weight:700;
      }

      .ds-care-submit{
        background:#086b3c;
        color:#fff;
      }

      .ds-care-cancel{
        background:#edf3ef;
        color:#14532d;
      }

      .ds-care-empty{
        text-align:center;
        color:#64748b;
        padding:40px 15px;
      }

      @media(max-width:600px){
        #dsMemberCareFloat{
          right:16px;
          bottom:18px;
          width:60px;
          height:60px;
        }

        #dsMemberCarePopup{
          height:94vh;
          border-radius:20px 20px 0 0;
        }

        .ds-care-message{
          max-width:88%;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function ensureUI() {
    if (document.getElementById("dsMemberCareOverlay")) return;

    const float = document.createElement("button");
    float.id = "dsMemberCareFloat";
    float.type = "button";
    float.title = "Member Care";
    float.innerHTML = "💬<span id=\"dsMemberCareUnread\">0</span>";

    const overlay = document.createElement("div");
    overlay.id = "dsMemberCareOverlay";

    overlay.innerHTML = `
      <div id="dsMemberCarePopup">
        <div class="ds-care-head">
          <div>
            <strong>🤝 Member Care</strong>
            <small>Support and conversation centre</small>
          </div>
          <button class="ds-care-close" id="dsCareClose">×</button>
        </div>

        <div class="ds-care-toolbar">
          <button class="ds-care-new" id="dsCareNew">+ New Conversation</button>
          <button class="ds-care-refresh" id="dsCareRefresh">Refresh</button>
        </div>

        <div id="dsCareList">
          <div class="ds-care-empty">Loading conversations...</div>
        </div>

        <div id="dsCareConversation">
          <div class="ds-care-conversation-head">
            <button class="ds-care-back" id="dsCareBack">← Back to conversations</button>
            <div id="dsCareTitle"><strong>Conversation</strong></div>
          </div>

          <div id="dsCareMessages"></div>

          <div id="dsCareReply">
            <div id="dsCareAttachmentName"
                 style="display:none;padding:6px 10px;margin-bottom:7px;background:#f0fdf4;border-radius:9px;font-size:12px;color:#166534;">
            </div>
            <form id="dsCareReplyForm">
              <input
                type="file"
                id="dsCareAttachment"
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt"
                style="display:none"
              >
              <button
                type="button"
                id="dsCareAttachBtn"
                title="Upload screenshot or file"
                style="width:52px;background:#edf3ef;color:#14532d;"
              >📎</button>
              <textarea id="dsCareReplyInput" placeholder="Type your response..."></textarea>
              <button type="submit">Send</button>
            </form>
          </div>
        </div>

        <form id="dsCareNewForm">
          <h3>New Member Care Conversation</h3>

          <label>Subject</label>
          <input id="dsCareSubject" required placeholder="How can we help?">

          <label>Category</label>
          <select id="dsCareCategory">
            <option>General Assistance</option>
            <option>Membership</option>
            <option>Church Information</option>
            <option>Pastoral Support</option>
            <option>Technical Support</option>
            <option>Finance / Giving</option>
            <option>Other</option>
          </select>

          <label>Priority</label>
          <select id="dsCarePriority">
            <option>Normal</option>
            <option>High</option>
            <option>Urgent</option>
          </select>

          <label>Message</label>
          <textarea id="dsCareMessage" required placeholder="Describe what you need help with..."></textarea>

          <div class="ds-care-form-actions">
            <button type="button" class="ds-care-cancel" id="dsCareCancelNew">Cancel</button>
            <button type="submit" class="ds-care-submit">Send Conversation</button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(float);
    document.body.appendChild(overlay);

    float.addEventListener("click", openPopup);

    document.getElementById("dsCareClose").onclick = closePopup;
    document.getElementById("dsCareRefresh").onclick = loadThreads;
    document.getElementById("dsCareBack").onclick = showList;
    document.getElementById("dsCareNew").onclick = showNewForm;
    document.getElementById("dsCareCancelNew").onclick = showList;

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closePopup();
    });

    document.getElementById("dsCareReplyForm").addEventListener("submit", sendReply);

    const attachBtn = document.getElementById("dsCareAttachBtn");
    const attachInput = document.getElementById("dsCareAttachment");
    const attachName = document.getElementById("dsCareAttachmentName");

    attachBtn.addEventListener("click", function () {
      attachInput.click();
    });

    attachInput.addEventListener("change", function () {
      const file = attachInput.files && attachInput.files[0];

      if (!file) {
        attachName.style.display = "none";
        attachName.textContent = "";
        return;
      }

      if (file.size > 8 * 1024 * 1024) {
        alert("Maximum attachment size is 8 MB.");
        attachInput.value = "";
        attachName.style.display = "none";
        return;
      }

      attachName.textContent = "📎 " + file.name;
      attachName.style.display = "block";
    });
    document.getElementById("dsCareNewForm").addEventListener("submit", createConversation);
  }

  function openPopup() {
    const overlay = document.getElementById("dsMemberCareOverlay");
    if (!overlay) return;

    overlay.style.display = "flex";
    showList();
    loadThreads();
  }

  function closePopup() {
    const overlay = document.getElementById("dsMemberCareOverlay");
    if (overlay) overlay.style.display = "none";

    currentThread = null;

    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function showList() {
    document.getElementById("dsCareList").style.display = "block";
    document.getElementById("dsCareConversation").style.display = "none";
    document.getElementById("dsCareNewForm").style.display = "none";
  }

  function showNewForm() {
    document.getElementById("dsCareList").style.display = "none";
    document.getElementById("dsCareConversation").style.display = "none";
    document.getElementById("dsCareNewForm").style.display = "block";
  }

  function showConversation() {
    document.getElementById("dsCareList").style.display = "none";
    document.getElementById("dsCareConversation").style.display = "flex";
    document.getElementById("dsCareNewForm").style.display = "none";
  }

  async function loadThreads() {
    const box = document.getElementById("dsCareList");
    if (!box) return;

    box.innerHTML = '<div class="ds-care-empty">Loading conversations...</div>';

    try {
      const data = await careApi("/api/customer-care");

      const rows =
        Array.isArray(data) ? data :
        Array.isArray(data.threads) ? data.threads :
        Array.isArray(data.conversations) ? data.conversations :
        Array.isArray(data.data) ? data.data : [];

      updateUnread(rows);

      if (!rows.length) {
        box.innerHTML = `
          <div class="ds-care-empty">
            <div style="font-size:35px">💬</div>
            <p>No Member Care conversations yet.</p>
            <button class="ds-care-new" onclick="document.getElementById('dsCareNew').click()">Start a conversation</button>
          </div>`;
        return;
      }

      box.innerHTML = rows.map(function (t) {
        const status = t.status || "Open";
        const priority = t.priority || "Normal";

        return `
          <div class="ds-care-thread" data-care-id="${esc(t.id)}">
            <div class="ds-care-thread-top">
              <span>${esc(t.subject || "Member Care Request")}</span>
              <span class="ds-care-status">${esc(status)}</span>
            </div>

            <div class="ds-care-thread-subject">
              ${esc(t.category || "General Assistance")}
              ${priority !== "Normal" ? " · " + esc(priority) : ""}
            </div>

            <div class="ds-care-thread-meta">
              ${esc(t.updated_at || t.created_at || "")}
              ${t.assigned_to ? " · " + esc(t.assigned_to) : ""}
            </div>
          </div>`;
      }).join("");

      box.querySelectorAll("[data-care-id]").forEach(function (el) {
        el.addEventListener("click", function () {
          openConversation(el.getAttribute("data-care-id"));
        });
      });

    } catch (e) {
      box.innerHTML = `
        <div class="ds-care-empty">
          Unable to load Member Care.<br>
          <small>${esc(e.message)}</small>
        </div>`;
    }
  }

  function updateUnread(rows) {
    let unread = 0;

    rows.forEach(function (t) {
      if (t.unread_count) unread += Number(t.unread_count) || 0;
      else if (t.unread) unread += Number(t.unread) || 0;
    });

    const badge = document.getElementById("dsMemberCareUnread");

    if (badge) {
      badge.textContent = unread > 99 ? "99+" : String(unread);
      badge.style.display = unread ? "flex" : "none";
    }
  }

  async function openConversation(id) {
    try {
      const data = await careApi("/api/customer-care/" + encodeURIComponent(id));

      const thread = data.thread || data.conversation || data;
      const messages =
        Array.isArray(data.messages) ? data.messages :
        Array.isArray(thread.messages) ? thread.messages : [];

      currentThread = thread;

      // Connect the active conversation to the
      // live typing and case-management modules.
      if (typeof window.setMemberCareTypingThread === "function") {
        window.setMemberCareTypingThread(thread);
      }

      if (typeof window.populateMemberCareCase === "function") {
        window.populateMemberCareCase(thread);
      }

      document.getElementById("dsCareTitle").innerHTML = `
        <strong>${esc(thread.subject || "Member Care Conversation")}</strong>
        <div style="font-size:12px;color:#64748b;margin-top:3px">
          ${esc(thread.category || "General Assistance")}
          · ${esc(thread.priority || "Normal")}
          · ${esc(thread.status || "Open")}
        </div>`;

      renderMessages(messages);
      showConversation();

      const messagesBox = document.getElementById("dsCareMessages");
      messagesBox.scrollTop = messagesBox.scrollHeight;

      if (pollTimer) clearInterval(pollTimer);

      pollTimer = setInterval(function () {
        if (currentThread) refreshConversation(false);
      }, 5000);

    } catch (e) {
      alert(e.message);
    }
  }

  function renderMessages(messages) {
    const box = document.getElementById("dsCareMessages");

    if (!messages.length) {
      box.innerHTML = '<div class="ds-care-empty">No messages yet.</div>';
      return;
    }

    box.innerHTML = messages.map(function (m) {
      const role = String(m.sender_role || "").toLowerCase();

      const isMember =
        role.includes("member") ||
        role.includes("user") ||
        role === "";

      return `
        <div class="ds-care-message ${isMember ? "member" : "staff"}">
          <div>${esc(m.message || "")}</div>

          ${
            m.attachment_url
              ? (
                String(m.attachment_type || "").startsWith("image/")
                  ? `
                    <div style="margin-top:8px;">
                      <a href="${esc(m.attachment_url)}" target="_blank">
                        <img
                          src="${esc(m.attachment_url)}"
                          alt="${esc(m.attachment_name || "Attachment")}"
                          style="max-width:100%;max-height:260px;border-radius:10px;display:block;"
                        >
                      </a>
                      <small>📎 ${esc(m.attachment_name || "Image")}</small>
                    </div>`
                  : `
                    <div style="margin-top:8px;">
                      📎
                      <a
                        href="${esc(m.attachment_url)}"
                        target="_blank"
                        rel="noopener"
                      >${esc(m.attachment_name || "Open attachment")}</a>
                    </div>`
              )
              : ""
          }

          <small>
            ${esc(m.sender_name || m.sender_role || "Member Care")}
            · ${esc(m.created_at || "")}
          </small>
        </div>`;
    }).join("");
  }

  async function refreshConversation(silent) {
    if (!currentThread) return;

    try {
      const data = await careApi(
        "/api/customer-care/" + encodeURIComponent(currentThread.id)
      );

      const thread = data.thread || data.conversation || data;

      const messages =
        Array.isArray(data.messages) ? data.messages :
        Array.isArray(thread.messages) ? thread.messages : [];

      const box = document.getElementById("dsCareMessages");
      const wasBottom =
        box.scrollHeight - box.scrollTop - box.clientHeight < 60;

      currentThread = thread;

      renderMessages(messages);

      if (wasBottom) {
        box.scrollTop = box.scrollHeight;
      }

      document.getElementById("dsCareTitle").innerHTML = `
        <strong>${esc(thread.subject || "Member Care Conversation")}</strong>
        <div style="font-size:12px;color:#64748b;margin-top:3px">
          ${esc(thread.category || "General Assistance")}
          · ${esc(thread.priority || "Normal")}
          · ${esc(thread.status || "Open")}
        </div>`;

    } catch (e) {
      if (!silent) alert(e.message);
    }
  }

  async function sendReply(e) {
    e.preventDefault();

    if (!currentThread) return;

    const input = document.getElementById("dsCareReplyInput");
    const attachment = document.getElementById("dsCareAttachment");
    const message = input.value.trim();
    const file = attachment.files && attachment.files[0];

    if (!message && !file) return;

    const button = e.submitter || e.target.querySelector("button[type='submit']");

    if (button) button.disabled = true;

    try {
      if (file) {
        const form = new FormData();

        form.append("file", file);

        if (message) {
          form.append("message", message);
        }

        const r = await fetch(
          "/api/customer-care/" +
          encodeURIComponent(currentThread.id) +
          "/attachment",
          {
            method: "POST",
            credentials: "same-origin",
            body: form
          }
        );

        let data = {};

        try {
          data = await r.json();
        } catch (_) {}

        if (!r.ok) {
          throw new Error(data.error || "Unable to upload attachment.");
        }

      } else {
        await careApi(
          "/api/customer-care/" +
          encodeURIComponent(currentThread.id) +
          "/message",
          {
            method: "POST",
            body: JSON.stringify({
              message: message
            })
          }
        );
      }

      input.value = "";
      attachment.value = "";

      const attachName =
        document.getElementById("dsCareAttachmentName");

      if (attachName) {
        attachName.style.display = "none";
        attachName.textContent = "";
      }

      await refreshConversation(true);

    } catch (err) {
      alert(err.message);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function createConversation(e) {
    e.preventDefault();

    const subject = document.getElementById("dsCareSubject").value.trim();
    const category = document.getElementById("dsCareCategory").value;
    const priority = document.getElementById("dsCarePriority").value;
    const message = document.getElementById("dsCareMessage").value.trim();

    if (!subject || !message) return;

    try {
      await careApi("/api/customer-care", {
        method: "POST",
        body: JSON.stringify({
          subject: subject,
          category: category,
          priority: priority,
          message: message
        })
      });

      document.getElementById("dsCareSubject").value = "";
      document.getElementById("dsCareMessage").value = "";
      document.getElementById("dsCarePriority").value = "Normal";

      showList();
      await loadThreads();

    } catch (e) {
      alert(e.message);
    }
  }

  function start() {
    injectStyle();
    ensureUI();

    // Keep the popup available on both the member dashboard
    // and the main diocesan/officer dashboard.
    setTimeout(loadThreads, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

/* =========================================================
   PROFESSIONAL MEMBER CARE CHAT UI
   ========================================================= */

(function () {
  const css = `
  #dsMemberCareOverlay {
    align-items: center !important;
    justify-content: center !important;
    padding: 12px !important;
    background: rgba(15, 23, 42, .58) !important;
    backdrop-filter: blur(3px);
  }

  #dsMemberCarePopup {
    width: min(720px, 100%) !important;
    height: min(760px, calc(100vh - 24px)) !important;
    max-height: calc(100vh - 24px) !important;
    border-radius: 20px !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    background: #fff !important;
    box-shadow: 0 24px 70px rgba(0,0,0,.28) !important;
  }

  #dsMemberCarePopup .ds-care-header {
    flex: 0 0 auto;
    padding: 16px 20px !important;
    background: linear-gradient(135deg,#087443,#0b8a51) !important;
    color: #fff !important;
  }

  #dsMemberCarePopup .ds-care-conversation {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    padding: 18px 16px 24px !important;
    background:
      radial-gradient(circle at 20% 10%, rgba(8,116,67,.035), transparent 28%),
      #f7f9f8 !important;
  }

  .ds-care-message {
    display: flex !important;
    flex-direction: column !important;
    margin: 8px 0 14px !important;
    max-width: 82% !important;
  }

  .ds-care-message.member {
    margin-left: auto !important;
    align-items: flex-end !important;
  }

  .ds-care-message.officer {
    margin-right: auto !important;
    align-items: flex-start !important;
  }

  .ds-care-bubble {
    padding: 11px 14px !important;
    border-radius: 16px !important;
    line-height: 1.45 !important;
    font-size: 15px !important;
    word-break: break-word !important;
    box-shadow: 0 2px 7px rgba(0,0,0,.06) !important;
  }

  .ds-care-message.member .ds-care-bubble {
    background: #087443 !important;
    color: #fff !important;
    border-bottom-right-radius: 5px !important;
  }

  .ds-care-message.officer .ds-care-bubble {
    background: #fff !important;
    color: #17221d !important;
    border: 1px solid #e2e9e5 !important;
    border-bottom-left-radius: 5px !important;
  }

  .ds-care-meta {
    font-size: 11px !important;
    color: #718078 !important;
    margin-top: 5px !important;
    padding: 0 5px !important;
  }

  .ds-care-attachment {
    margin-top: 4px !important;
    overflow: hidden !important;
    border-radius: 12px !important;
    background: #fff !important;
    border: 1px solid rgba(0,0,0,.08) !important;
  }

  .ds-care-attachment img {
    display: block !important;
    width: min(360px, 100%) !important;
    max-height: 280px !important;
    object-fit: contain !important;
    background: #eef2f0 !important;
    cursor: pointer !important;
  }

  .ds-care-attachment-info {
    padding: 9px 11px !important;
    font-size: 12px !important;
    color: #526159 !important;
  }

  #dsMemberCarePopup .ds-care-composer {
    flex: 0 0 auto !important;
    display: flex !important;
    align-items: flex-end !important;
    gap: 9px !important;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom)) !important;
    background: #fff !important;
    border-top: 1px solid #e5ebe7 !important;
  }

  #dsMemberCarePopup .ds-care-composer textarea {
    flex: 1 !important;
    min-height: 48px !important;
    max-height: 120px !important;
    resize: none !important;
    border: 1px solid #d7e0db !important;
    border-radius: 15px !important;
    padding: 13px 14px !important;
    font-size: 15px !important;
    outline: none !important;
    background: #f8faf9 !important;
  }

  #dsMemberCarePopup .ds-care-composer textarea:focus {
    border-color: #087443 !important;
    background: #fff !important;
    box-shadow: 0 0 0 3px rgba(8,116,67,.09) !important;
  }

  #dsMemberCarePopup .ds-care-composer button {
    min-width: 54px !important;
    height: 48px !important;
    border-radius: 14px !important;
  }

  @media (max-width: 600px) {
    #dsMemberCareOverlay {
      padding: 0 !important;
      align-items: stretch !important;
    }

    #dsMemberCarePopup {
      width: 100% !important;
      height: 100dvh !important;
      max-height: 100dvh !important;
      border-radius: 0 !important;
    }

    #dsMemberCarePopup .ds-care-conversation {
      padding: 14px 11px 20px !important;
    }

    .ds-care-message {
      max-width: 88% !important;
    }

    .ds-care-attachment img {
      width: min(300px, 100%) !important;
      max-height: 240px !important;
    }

    #dsMemberCarePopup .ds-care-composer {
      padding-left: 9px !important;
      padding-right: 9px !important;
    }
  }
  `;

  const style = document.createElement("style");
  style.id = "dsMemberCareProfessionalUI";
  style.textContent = css;
  document.head.appendChild(style);
})();


/* =========================================================
   MEMBER CARE - READ MESSAGE HANDLER
   ========================================================= */

async function markMemberCareRead(threadId) {
  if (!threadId) return;

  try {
    await fetch(
      `/api/customer-care/${encodeURIComponent(threadId)}/read`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        }
      }
    );
  } catch (err) {
    console.warn("Member Care read update failed:", err);
  }
}

/* =========================================================
   MEMBER CARE IMAGE LIGHTBOX
   ========================================================= */

(function () {
  function createMemberCareLightbox() {
    if (document.getElementById("dsCareLightbox")) return;

    const box = document.createElement("div");
    box.id = "dsCareLightbox";
    box.innerHTML = `
      <button id="dsCareLightboxClose" aria-label="Close image">×</button>
      <div class="ds-care-lightbox-stage">
        <img id="dsCareLightboxImage" src="" alt="Attachment preview">
      </div>
      <div id="dsCareLightboxCaption"></div>
    `;

    document.body.appendChild(box);

    const style = document.createElement("style");
    style.id = "dsCareLightboxStyle";
    style.textContent = `
      #dsCareLightbox {
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: none;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        padding: 18px;
        background: rgba(0,0,0,.92);
        backdrop-filter: blur(5px);
      }

      #dsCareLightbox.open {
        display: flex;
      }

      .ds-care-lightbox-stage {
        width: 100%;
        height: calc(100% - 45px);
        display: flex;
        align-items: center;
        justify-content: center;
      }

      #dsCareLightboxImage {
        display: block;
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 8px;
        box-shadow: 0 10px 45px rgba(0,0,0,.55);
        user-select: none;
        -webkit-user-select: none;
      }

      #dsCareLightboxClose {
        position: absolute;
        top: max(14px, env(safe-area-inset-top));
        right: 14px;
        z-index: 2;
        width: 48px;
        height: 48px;
        border: 0;
        border-radius: 50%;
        background: rgba(255,255,255,.16);
        color: #fff;
        font-size: 34px;
        line-height: 1;
        cursor: pointer;
      }

      #dsCareLightboxClose:active {
        background: rgba(255,255,255,.28);
      }

      #dsCareLightboxCaption {
        color: rgba(255,255,255,.85);
        font-size: 13px;
        text-align: center;
        max-width: 90%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      body.ds-care-lightbox-open {
        overflow: hidden !important;
      }

      @media (max-width: 600px) {
        #dsCareLightbox {
          padding: 10px;
        }

        .ds-care-lightbox-stage {
          height: calc(100% - 35px);
        }

        #dsCareLightboxImage {
          max-width: 100%;
          max-height: 88vh;
        }
      }
    `;

    document.head.appendChild(style);

    const close = () => {
      box.classList.remove("open");
      document.body.classList.remove("ds-care-lightbox-open");
      document.getElementById("dsCareLightboxImage").src = "";
    };

    document.getElementById("dsCareLightboxClose")
      .addEventListener("click", close);

    box.addEventListener("click", function (e) {
      if (
        e.target === box ||
        e.target.classList.contains("ds-care-lightbox-stage")
      ) {
        close();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    document.addEventListener("click", function (e) {
      const img = e.target.closest(
        '#dsMemberCarePopup .ds-care-attachment img, #dsMemberCarePopup img'
      );

      if (!img) return;

      e.preventDefault();
      e.stopPropagation();

      const viewerImage =
        document.getElementById("dsCareLightboxImage");

      const caption =
        document.getElementById("dsCareLightboxCaption");

      viewerImage.src = img.currentSrc || img.src;
      caption.textContent = img.alt || "Attachment preview";

      box.classList.add("open");
      document.body.classList.add("ds-care-lightbox-open");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      createMemberCareLightbox
    );
  } else {
    createMemberCareLightbox();
  }
})();

/* =========================================================
   MEMBER CARE - AUTOMATIC IMAGE COMPRESSION
   Compress large images before upload for faster mobile use.
   ========================================================= */

(function () {
  function setupMemberCareImageCompression() {
    const input = document.getElementById("dsCareAttachment");
    if (!input || input.dataset.compressionReady === "1") return;

    input.dataset.compressionReady = "1";

    input.addEventListener("change", async function () {
      const file = input.files && input.files[0];
      if (!file) return;

      if (!file.type.startsWith("image/")) return;

      // Keep already-small images unchanged.
      if (file.size <= 900 * 1024) return;

      try {
        const bitmap = await createImageBitmap(file);

        const maxWidth = 1600;
        const maxHeight = 1600;

        let width = bitmap.width;
        let height = bitmap.height;

        const scale = Math.min(
          1,
          maxWidth / width,
          maxHeight / height
        );

        width = Math.round(width * scale);
        height = Math.round(height * scale);

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d", {
          alpha: false
        });

        ctx.drawImage(bitmap, 0, 0, width, height);
        bitmap.close();

        const compressedBlob = await new Promise(resolve => {
          canvas.toBlob(
            resolve,
            "image/jpeg",
            0.78
          );
        });

        if (!compressedBlob || compressedBlob.size >= file.size) {
          return;
        }

        const compressedFile = new File(
          [compressedBlob],
          file.name.replace(/\.[^.]+$/, "") + ".jpg",
          {
            type: "image/jpeg",
            lastModified: Date.now()
          }
        );

        const transfer = new DataTransfer();
        transfer.items.add(compressedFile);
        input.files = transfer.files;

        const originalMB =
          (file.size / 1024 / 1024).toFixed(2);

        const newMB =
          (compressedFile.size / 1024 / 1024).toFixed(2);

        let notice =
          document.getElementById("dsCareCompressionNotice");

        if (!notice) {
          notice = document.createElement("div");
          notice.id = "dsCareCompressionNotice";

          notice.style.cssText = `
            position:fixed;
            left:50%;
            bottom:82px;
            transform:translateX(-50%);
            z-index:1000000;
            background:#087443;
            color:#fff;
            padding:9px 14px;
            border-radius:12px;
            font-size:13px;
            box-shadow:0 5px 20px rgba(0,0,0,.2);
            max-width:90%;
            text-align:center;
          `;

          document.body.appendChild(notice);
        }

        notice.textContent =
          `📷 Image optimized: ${originalMB} MB → ${newMB} MB`;

        clearTimeout(notice._timer);

        notice._timer = setTimeout(() => {
          notice.remove();
        }, 3000);

      } catch (err) {
        console.warn(
          "Member Care image compression skipped:",
          err
        );
      }
    });
  }

  function waitForAttachmentInput() {
    setupMemberCareImageCompression();

    if (!document.getElementById("dsCareAttachment")) {
      setTimeout(waitForAttachmentInput, 700);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      waitForAttachmentInput
    );
  } else {
    waitForAttachmentInput();
  }
})();

/* =========================================================
   MEMBER CARE - PROFESSIONAL DOCUMENT ATTACHMENT CARDS
   ========================================================= */

(function () {

  function initDocumentCards() {

    if (document.getElementById("dsCareDocumentCardStyle")) return;

    const style = document.createElement("style");
    style.id = "dsCareDocumentCardStyle";

    style.textContent = `
      .ds-care-document-card {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 240px;
        max-width: 360px;
        padding: 12px 14px;
        border-radius: 14px;
        background: #fff;
        border: 1px solid #e0e7e3;
        box-shadow: 0 2px 8px rgba(0,0,0,.05);
        text-decoration: none;
        color: inherit;
      }

      .ds-care-document-icon {
        width: 44px;
        height: 44px;
        flex: 0 0 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 11px;
        background: #edf5f0;
        font-size: 23px;
      }

      .ds-care-document-info {
        flex: 1;
        min-width: 0;
      }

      .ds-care-document-name {
        font-size: 14px;
        font-weight: 700;
        color: #183127;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .ds-care-document-meta {
        margin-top: 4px;
        font-size: 11px;
        color: #718078;
      }

      .ds-care-document-open {
        flex: 0 0 auto;
        padding: 7px 10px;
        border-radius: 9px;
        background: #087443;
        color: #fff;
        font-size: 11px;
        font-weight: 700;
      }

      .ds-care-document-card:hover {
        border-color: #087443;
      }

      @media (max-width:600px) {
        .ds-care-document-card {
          min-width: 210px;
          max-width: 300px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function getDocumentIcon(type, name) {

    const value =
      String(type || "") + " " + String(name || "");

    if (/pdf/i.test(value)) return "📕";
    if (/word|docx?/i.test(value)) return "📝";
    if (/excel|xlsx?/i.test(value)) return "📊";
    if (/text|txt/i.test(value)) return "📃";

    return "📎";
  }

  function formatFileSize(bytes) {

    const size = Number(bytes || 0);

    if (!size) return "";

    if (size < 1024)
      return size + " B";

    if (size < 1024 * 1024)
      return (size / 1024).toFixed(1) + " KB";

    return (size / (1024 * 1024)).toFixed(2) + " MB";
  }

  function formatFileType(type, name) {

    const value =
      String(type || "") + " " + String(name || "");

    if (/pdf/i.test(value)) return "PDF";
    if (/word|docx?/i.test(value)) return "WORD";
    if (/excel|xlsx?/i.test(value)) return "EXCEL";
    if (/text|txt/i.test(value)) return "TEXT";

    const nameValue = String(name || "");

    const match = nameValue.match(/\.([a-z0-9]+)$/i);

    return match
      ? match[1].toUpperCase()
      : "FILE";
  }

  window.dsCareDocumentCard = function (m) {

    if (!m || !m.attachment_url) return "";

    const name =
      m.attachment_name || "Attachment";

    const icon =
      getDocumentIcon(
        m.attachment_type,
        name
      );

    const type =
      formatFileType(
        m.attachment_type,
        name
      );

    const size =
      formatFileSize(
        m.attachment_size
      );

    return `
      <a
        class="ds-care-document-card"
        href="${String(m.attachment_url).replace(/"/g, "&quot;")}"
        target="_blank"
        rel="noopener"
      >
        <div class="ds-care-document-icon">
          ${icon}
        </div>

        <div class="ds-care-document-info">

          <div class="ds-care-document-name">
            ${String(name).replace(/</g, "&lt;")}
          </div>

          <div class="ds-care-document-meta">
            ${type}${size ? " • " + size : ""}
          </div>

        </div>

        <div class="ds-care-document-open">
          OPEN ↗
        </div>
      </a>
    `;
  };

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initDocumentCards
    );
  } else {
    initDocumentCards();
  }

})();

/* =========================================================
   MEMBER CARE - UNREAD BADGES
   ========================================================= */

(function () {

  let unreadTimer = null;

  function ensureUnreadStyles() {
    if (document.getElementById("dsCareUnreadStyles")) return;

    const style = document.createElement("style");
    style.id = "dsCareUnreadStyles";

    style.textContent = `
      #dsMemberCareFloat {
        position: relative !important;
      }

      #dsMemberCareUnread {
        position: absolute !important;
        top: -5px !important;
        right: -5px !important;
        min-width: 21px !important;
        height: 21px !important;
        padding: 0 5px !important;
        display: none;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 999px !important;
        background: #dc2626 !important;
        color: #fff !important;
        border: 2px solid #fff !important;
        font-size: 10px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        box-shadow: 0 3px 8px rgba(0,0,0,.25) !important;
      }

      .ds-care-list-unread {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 21px !important;
        height: 21px !important;
        padding: 0 5px !important;
        margin-left: 7px !important;
        border-radius: 999px !important;
        background: #dc2626 !important;
        color: #fff !important;
        font-size: 10px !important;
        font-weight: 800 !important;
      }
    `;

    document.head.appendChild(style);
  }

  async function updateUnreadUI() {
    try {
      const response = await fetch(
        "/api/customer-care/unread-count",
        {
          credentials: "same-origin",
          cache: "no-store"
        }
      );

      if (!response.ok) return;

      const data = await response.json();

      const total = Number(data.total || 0);

      // Floating button badge.
      let float = document.getElementById("dsMemberCareFloat");

      if (float) {
        let badge =
          document.getElementById("dsMemberCareUnread");

        if (!badge) {
          badge = document.createElement("span");
          badge.id = "dsMemberCareUnread";
          float.appendChild(badge);
        }

        badge.textContent =
          total > 99 ? "99+" : String(total);

        badge.style.display =
          total > 0 ? "flex" : "none";
      }

      // Conversation list badges.
      const counts = {};

      (data.conversations || []).forEach(function (item) {
        counts[String(item.id)] =
          Number(item.unread_count || 0);
      });

      document
        .querySelectorAll("[data-care-id]")
        .forEach(function (item) {

          const id =
            String(item.getAttribute("data-care-id"));

          const count = counts[id] || 0;

          let badge =
            item.querySelector(".ds-care-list-unread");

          if (count > 0) {

            if (!badge) {
              badge = document.createElement("span");
              badge.className =
                "ds-care-list-unread";

              item.appendChild(badge);
            }

            badge.textContent =
              count > 99 ? "99+" : String(count);

          } else if (badge) {

            badge.remove();

          }
        });

    } catch (err) {
      console.warn(
        "Member Care unread update failed:",
        err
      );
    }
  }

  function startUnreadPolling() {

    ensureUnreadStyles();

    updateUnreadUI();

    if (unreadTimer) {
      clearInterval(unreadTimer);
    }

    unreadTimer = setInterval(
      updateUnreadUI,
      5000
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      startUnreadPolling
    );
  } else {
    startUnreadPolling();
  }

  window.updateMemberCareUnread =
    updateUnreadUI;

})();

/* =========================================================
   MEMBER CARE - TYPING INDICATOR
   ========================================================= */

(function () {

  function addTypingStyles() {
    if (document.getElementById("dsCareTypingStyles")) return;

    const style = document.createElement("style");
    style.id = "dsCareTypingStyles";

    style.textContent = `
      .ds-care-typing {
        display: none;
        align-items: center;
        gap: 8px;
        padding: 5px 16px 9px;
        color: #718078;
        font-size: 12px;
        background: #fff;
      }

      .ds-care-typing.show {
        display: flex;
      }

      .ds-care-typing-dots {
        display: inline-flex;
        gap: 3px;
      }

      .ds-care-typing-dots span {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: #087443;
        animation: dsCareTyping 1.2s infinite;
      }

      .ds-care-typing-dots span:nth-child(2) {
        animation-delay: .2s;
      }

      .ds-care-typing-dots span:nth-child(3) {
        animation-delay: .4s;
      }

      @keyframes dsCareTyping {
        0%, 60%, 100% {
          transform: translateY(0);
          opacity: .35;
        }

        30% {
          transform: translateY(-3px);
          opacity: 1;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function ensureTypingElement() {
    if (document.getElementById("dsCareTyping")) return;

    const composer =
      document.querySelector(
        "#dsMemberCarePopup .ds-care-composer"
      );

    if (!composer) return;

    const typing = document.createElement("div");
    typing.id = "dsCareTyping";
    typing.className = "ds-care-typing";

    typing.innerHTML = `
      <span>Support is typing</span>
      <span class="ds-care-typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </span>
    `;

    composer.parentNode.insertBefore(
      typing,
      composer
    );
  }

  window.showMemberCareTyping = function (label) {
    ensureTypingElement();

    const el =
      document.getElementById("dsCareTyping");

    if (!el) return;

    const labelEl = el.querySelector("span:first-child");

    if (labelEl) {
      labelEl.textContent =
        label || "Support is typing";
    }

    el.classList.add("show");
  };

  window.hideMemberCareTyping = function () {
    const el =
      document.getElementById("dsCareTyping");

    if (el) el.classList.remove("show");
  };

  function watchComposer() {
    addTypingStyles();
    ensureTypingElement();

    const textarea =
      document.querySelector(
        "#dsMemberCarePopup .ds-care-composer textarea"
      );

    if (!textarea || textarea.dataset.typingReady === "1") {
      return;
    }

    textarea.dataset.typingReady = "1";

    textarea.addEventListener("input", function () {

      // Visual typing feedback while composing.
      if (textarea.value.trim()) {
        window.showMemberCareTyping();
      } else {
        window.hideMemberCareTyping();
      }

      clearTimeout(textarea._typingTimer);

      textarea._typingTimer = setTimeout(
        function () {
          window.hideMemberCareTyping();
        },
        1200
      );
    });
  }

  function start() {
    watchComposer();

    if (!document.querySelector(
      "#dsMemberCarePopup .ds-care-composer textarea"
    )) {
      setTimeout(start, 700);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      start
    );
  } else {
    start();
  }

})();

/* =========================================================
   MEMBER CARE - TWO-WAY LIVE TYPING
   ========================================================= */

(function () {

  let typingSendTimer = null;
  let typingPollTimer = null;
  let typingActive = false;

  async function sendTypingStatus(isTyping) {
    if (!window.currentThread && !window.memberCareCurrentThread) {
      return;
    }

    const thread =
      window.currentThread ||
      window.memberCareCurrentThread;

    const id = thread && thread.id;

    if (!id) return;

    try {
      await fetch(
        "/api/customer-care/" +
        encodeURIComponent(id) +
        "/typing",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            typing: Boolean(isTyping)
          })
        }
      );
    } catch (err) {
      console.warn(
        "Member Care typing update failed:",
        err
      );
    }
  }

  async function checkOtherTyping() {

    const thread =
      window.currentThread ||
      window.memberCareCurrentThread;

    if (!thread || !thread.id) return;

    try {

      const response = await fetch(
        "/api/customer-care/" +
        encodeURIComponent(thread.id) +
        "/typing",
        {
          credentials: "same-origin",
          cache: "no-store"
        }
      );

      if (!response.ok) return;

      const data = await response.json();

      if (data.typing) {

        const role =
          String(data.role || "").toLowerCase();

        const label =
          role === "member"
            ? "Member is typing"
            : "Support is typing";

        if (typeof window.showMemberCareTyping === "function") {
          window.showMemberCareTyping(label);
        }

      } else {

        if (typeof window.hideMemberCareTyping === "function") {
          window.hideMemberCareTyping();
        }
      }

    } catch (err) {
      // Silent failure keeps chat working normally.
    }
  }

  function setupTypingInput() {

    const textarea =
      document.querySelector(
        "#dsMemberCarePopup .ds-care-composer textarea"
      );

    if (!textarea || textarea.dataset.liveTypingReady === "1") {
      return;
    }

    textarea.dataset.liveTypingReady = "1";

    textarea.addEventListener("input", function () {

      if (!textarea.value.trim()) {

        typingActive = false;

        sendTypingStatus(false);

        return;
      }

      if (!typingActive) {
        typingActive = true;
        sendTypingStatus(true);
      }

      clearTimeout(typingSendTimer);

      typingSendTimer = setTimeout(
        function () {

          typingActive = false;

          sendTypingStatus(false);

        },
        2500
      );
    });
  }

  function start() {

    setupTypingInput();

    if (!typingPollTimer) {
      typingPollTimer = setInterval(
        checkOtherTyping,
        1500
      );
    }

    if (
      !document.querySelector(
        "#dsMemberCarePopup .ds-care-composer textarea"
      )
    ) {
      setTimeout(start, 700);
    }
  }

  // Expose a safe way for the existing popup to update
  // its current conversation.
  window.setMemberCareTypingThread = function (thread) {
    window.memberCareCurrentThread = thread;
    typingActive = false;
  };

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      start
    );
  } else {
    start();
  }

})();

/* =========================================================
   MEMBER CARE - PROFESSIONAL CASE CONTROLS
   ========================================================= */

(function () {

  function addCaseControlStyles() {
    if (document.getElementById("dsCareCaseStyles")) return;

    const style = document.createElement("style");
    style.id = "dsCareCaseStyles";

    style.textContent = `
      #dsCareCaseControls {
        display: none;
        padding: 10px 14px;
        background: #f8faf9;
        border-bottom: 1px solid #e2e9e5;
      }

      #dsCareCaseControls.show {
        display: block;
      }

      .ds-care-case-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }

      .ds-care-case-field {
        min-width: 0;
      }

      .ds-care-case-field label {
        display: block;
        margin-bottom: 4px;
        color: #607067;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
      }

      .ds-care-case-field select,
      .ds-care-case-field textarea {
        width: 100%;
        box-sizing: border-box;
        border: 1px solid #d7e0db;
        border-radius: 9px;
        background: #fff;
        padding: 8px 9px;
        font-size: 13px;
        outline: none;
      }

      .ds-care-case-field select:focus,
      .ds-care-case-field textarea:focus {
        border-color: #087443;
        box-shadow: 0 0 0 2px rgba(8,116,67,.08);
      }

      .ds-care-case-note {
        margin-top: 8px;
      }

      .ds-care-case-note textarea {
        min-height: 52px;
        resize: vertical;
      }

      .ds-care-case-actions {
        display: flex;
        justify-content: flex-end;
        gap: 7px;
        margin-top: 8px;
      }

      .ds-care-case-save {
        border: 0;
        border-radius: 9px;
        padding: 8px 13px;
        background: #087443;
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        cursor: pointer;
      }

      .ds-care-case-save:disabled {
        opacity: .6;
      }

      .ds-care-case-message {
        display: none;
        align-items: center;
        margin-right: auto;
        color: #087443;
        font-size: 11px;
        font-weight: 600;
      }

      .ds-care-case-message.show {
        display: flex;
      }

      @media (max-width: 600px) {
        #dsCareCaseControls {
          padding: 9px 10px;
        }

        .ds-care-case-grid {
          gap: 6px;
        }

        .ds-care-case-field select,
        .ds-care-case-field textarea {
          font-size: 12px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function ensureCaseControls() {

    if (document.getElementById("dsCareCaseControls")) {
      return;
    }

    const title =
      document.getElementById("dsCareTitle");

    if (!title) return;

    const controls =
      document.createElement("div");

    controls.id = "dsCareCaseControls";

    controls.innerHTML = `
      <div class="ds-care-case-grid">

        <div class="ds-care-case-field">
          <label>Status</label>

          <select id="dsCareCaseStatus">
            <option value="Open">Open</option>
            <option value="In Progress">In Progress</option>
            <option value="Pending">Pending</option>
            <option value="Resolved">Resolved</option>
          </select>
        </div>

        <div class="ds-care-case-field">
          <label>Priority</label>

          <select id="dsCareCasePriority">
            <option value="Normal">Normal</option>
            <option value="High">High</option>
            <option value="Urgent">Urgent</option>
          </select>
        </div>

      </div>

      <div class="ds-care-case-field ds-care-case-note">
        <label>Resolution note</label>

        <textarea
          id="dsCareCaseNote"
          placeholder="Add a resolution or internal case note..."
        ></textarea>
      </div>

      <div class="ds-care-case-actions">

        <span
          id="dsCareCaseMessage"
          class="ds-care-case-message"
        ></span>

        <button
          type="button"
          id="dsCareCaseSave"
          class="ds-care-case-save"
        >
          Save Case
        </button>

      </div>
    `;

    title.parentNode.insertBefore(
      controls,
      title.nextSibling
    );

    document
      .getElementById("dsCareCaseSave")
      .addEventListener(
        "click",
        saveCase
      );
  }

  function populateCaseControls(thread) {

    ensureCaseControls();

    const controls =
      document.getElementById(
        "dsCareCaseControls"
      );

    if (!controls) return;

    controls.classList.add("show");

    const status =
      document.getElementById(
        "dsCareCaseStatus"
      );

    const priority =
      document.getElementById(
        "dsCareCasePriority"
      );

    const note =
      document.getElementById(
        "dsCareCaseNote"
      );

    if (status) {
      status.value =
        thread.status || "Open";
    }

    if (priority) {
      priority.value =
        thread.priority || "Normal";
    }

    if (note) {
      note.value =
        thread.resolution_note || "";
    }
  }

  async function saveCase() {

    const thread =
      window.currentThread ||
      window.memberCareCurrentThread;

    if (!thread || !thread.id) return;

    const button =
      document.getElementById(
        "dsCareCaseSave"
      );

    const message =
      document.getElementById(
        "dsCareCaseMessage"
      );

    const status =
      document.getElementById(
        "dsCareCaseStatus"
      ).value;

    const priority =
      document.getElementById(
        "dsCareCasePriority"
      ).value;

    const resolution_note =
      document.getElementById(
        "dsCareCaseNote"
      ).value.trim();

    button.disabled = true;

    try {

      const response = await fetch(
        "/api/customer-care/" +
        encodeURIComponent(thread.id) +
        "/status",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            status,
            priority,
            resolution_note
          })
        }
      );

      const data =
        await response.json();

      if (!response.ok || !data.ok) {
        throw new Error(
          data.error ||
          "Unable to update case"
        );
      }

      thread.status =
        data.status;

      thread.priority =
        data.priority;

      thread.resolution_note =
        data.resolution_note;

      message.textContent =
        "✓ Case updated";

      message.classList.add("show");

      setTimeout(function () {
        message.classList.remove("show");
      }, 2500);

    } catch (err) {

      alert(
        err.message ||
        "Unable to update case"
      );

    } finally {

      button.disabled = false;

    }
  }

  window.populateMemberCareCase =
    populateCaseControls;

  if (document.readyState === "loading") {

    document.addEventListener(
      "DOMContentLoaded",
      addCaseControlStyles
    );

  } else {

    addCaseControlStyles();

  }

})();


/* =========================================================
   MEMBER CARE CASE ASSIGNMENT MODULE
   ========================================================= */

(function () {

  function escAssign(v) {
    return String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function loadAssignmentOfficers() {
    const select =
      document.getElementById("dsCareAssignedOfficer");

    if (!select) return;

    select.innerHTML =
      '<option value="">Loading officers...</option>';

    try {
      const response = await fetch(
        "/api/customer-care/officers",
        {
          credentials: "same-origin"
        }
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error || "Unable to load officers"
        );
      }

      const officers =
        Array.isArray(data.officers)
          ? data.officers
          : [];

      select.innerHTML =
        '<option value="">— Select Officer —</option>' +
        officers.map(function (officer) {
          return (
            '<option value="' +
            escAssign(officer.id) +
            '">' +
            escAssign(officer.username) +
            ' — ' +
            escAssign(officer.role) +
            '</option>'
          );
        }).join("");

    } catch (err) {

      console.error(
        "Member Care officers:",
        err
      );

      select.innerHTML =
        '<option value="">Unable to load officers</option>';
    }
  }


  function ensureAssignmentPanel() {

    const title =
      document.getElementById("dsCareTitle");

    if (!title || !title.parentNode) {
      return;
    }

    let panel =
      document.getElementById("dsCareAssignment");

    if (panel) {
      return;
    }

    panel =
      document.createElement("div");

    panel.id =
      "dsCareAssignment";

    panel.innerHTML = `
      <div style="
        border:1px solid #e2e8f0;
        border-radius:12px;
        padding:12px;
        margin:10px 0;
        background:#f8fafc;
      ">

        <div style="
          font-weight:700;
          font-size:13px;
          color:#0f172a;
          margin-bottom:8px;
        ">
          👤 Case Assignment
        </div>

        <div style="
          display:grid;
          grid-template-columns:minmax(0,1fr) auto;
          gap:8px;
          align-items:center;
        ">

          <select
            id="dsCareAssignedOfficer"
            style="
              width:100%;
              min-height:40px;
              border:1px solid #cbd5e1;
              border-radius:8px;
              padding:8px 10px;
              background:#fff;
              font-size:13px;
            "
          >
            <option value="">
              — Select Officer —
            </option>
          </select>

          <button
            id="dsCareAssignBtn"
            type="button"
            style="
              min-height:40px;
              border:0;
              border-radius:8px;
              padding:0 14px;
              background:#15803d;
              color:#fff;
              font-weight:700;
              cursor:pointer;
              white-space:nowrap;
            "
          >
            Assign Case
          </button>

        </div>

        <div
          id="dsCareAssignedInfo"
          style="
            margin-top:8px;
            font-size:12px;
            color:#64748b;
          "
        >
          No officer assigned yet.
        </div>

      </div>
    `;

    title.parentNode.insertBefore(
      panel,
      title.nextSibling
    );

    const button =
      document.getElementById(
        "dsCareAssignBtn"
      );

    if (button) {

      button.addEventListener(
        "click",
        assignCurrentCase
      );
    }

    loadAssignmentOfficers();
  }


  async function assignCurrentCase() {

    const thread =
      window.memberCareCurrentThread ||
      window.currentThread;

    if (!thread || !thread.id) {
      alert(
        "Open a conversation first."
      );
      return;
    }

    const select =
      document.getElementById(
        "dsCareAssignedOfficer"
      );

    const officerId =
      select ? select.value : "";

    if (!officerId) {
      alert(
        "Please select an officer."
      );
      return;
    }

    const button =
      document.getElementById(
        "dsCareAssignBtn"
      );

    if (button) {
      button.disabled = true;
      button.textContent = "Assigning...";
    }

    try {

      const response = await fetch(
        "/api/customer-care/" +
        encodeURIComponent(thread.id) +
        "/assign",
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            assigned_user_id:
              Number(officerId)
          })
        }
      );

      const data =
        await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Unable to assign case"
        );
      }

      thread.assigned_user_id =
        data.assigned_user_id;

      thread.assigned_user_name =
        data.assigned_user_name;

      thread.assigned_at =
        data.assigned_at;

      thread.assigned_by_name =
        data.assigned_by_name;

      populateAssignment(
        thread
      );

      if (button) {
        button.textContent =
          "Assigned ✓";

        setTimeout(function () {
          button.textContent =
            "Assign Case";
        }, 1800);
      }

    } catch (err) {

      alert(
        err.message ||
        "Unable to assign case"
      );

      if (button) {
        button.textContent =
          "Assign Case";
      }

    } finally {

      if (button) {
        button.disabled = false;
      }
    }
  }


  function populateAssignment(thread) {

    ensureAssignmentPanel();

    const select =
      document.getElementById(
        "dsCareAssignedOfficer"
      );

    const info =
      document.getElementById(
        "dsCareAssignedInfo"
      );

    if (!select || !info) {
      return;
    }

    if (
      thread &&
      thread.assigned_user_id
    ) {

      select.value =
        String(
          thread.assigned_user_id
        );

      info.innerHTML =
        "Currently assigned to <strong>" +
        escAssign(
          thread.assigned_user_name ||
          "Officer"
        ) +
        "</strong>" +
        (
          thread.assigned_at
            ? " · " +
              escAssign(
                thread.assigned_at
              )
            : ""
        ) +
        (
          thread.assigned_by_name
            ? " · Assigned by " +
              escAssign(
                thread.assigned_by_name
              )
            : ""
        );

    } else {

      select.value = "";

      info.textContent =
        "No officer assigned yet.";
    }
  }


  window.populateMemberCareAssignment =
    populateAssignment;


  /*
   * Extend the existing Case Controls
   * without replacing them.
   */
  const previousCasePopulate =
    window.populateMemberCareCase;

  window.populateMemberCareCase =
    function (thread) {

      if (
        typeof previousCasePopulate ===
        "function"
      ) {
        previousCasePopulate(
          thread
        );
      }

      populateAssignment(
        thread
      );
    };


  /*
   * If the popup is already open when
   * this module loads, prepare the panel.
   */
  if (
    document.readyState ===
    "loading"
  ) {

    document.addEventListener(
      "DOMContentLoaded",
      function () {

        const thread =
          window.memberCareCurrentThread ||
          window.currentThread;

        if (thread) {
          populateAssignment(
            thread
          );
        }
      }
    );

  } else {

    const thread =
      window.memberCareCurrentThread ||
      window.currentThread;

    if (thread) {
      populateAssignment(
        thread
      );
    }
  }

})();

/* =========================================================
   MEMBER CARE TIMELINE UI
   ========================================================= */

(function () {

  function escTimeline(v) {
    return String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function ensureTimelinePanel() {

    const title =
      document.getElementById("dsCareTitle");

    if (!title || !title.parentNode) return;

    let panel =
      document.getElementById("dsCareTimelinePanel");

    if (panel) return;

    panel =
      document.createElement("div");

    panel.id =
      "dsCareTimelinePanel";

    panel.innerHTML = `
      <div style="
        border:1px solid #e2e8f0;
        border-radius:12px;
        padding:12px;
        margin:10px 0;
        background:#ffffff;
      ">

        <div style="
          display:flex;
          justify-content:space-between;
          align-items:center;
          gap:10px;
          margin-bottom:10px;
        ">
          <div style="
            font-weight:700;
            font-size:13px;
            color:#0f172a;
          ">
            📋 Case Timeline
          </div>

          <button
            id="dsCareTimelineRefresh"
            type="button"
            style="
              border:1px solid #cbd5e1;
              background:#fff;
              border-radius:7px;
              padding:5px 9px;
              font-size:11px;
              cursor:pointer;
            "
          >
            Refresh
          </button>
        </div>

        <div
          id="dsCareTimelineList"
          style="
            max-height:260px;
            overflow-y:auto;
          "
        >
          <div style="
            color:#64748b;
            font-size:12px;
            padding:10px 0;
          ">
            Loading timeline...
          </div>
        </div>

      </div>

      <div style="
        border:1px solid #e2e8f0;
        border-radius:12px;
        padding:12px;
        margin:10px 0;
        background:#f8fafc;
      ">

        <div style="
          font-weight:700;
          font-size:13px;
          color:#0f172a;
          margin-bottom:8px;
        ">
          🔒 Internal Case Note
        </div>

        <textarea
          id="dsCareInternalNote"
          rows="3"
          placeholder="Write an internal note for officers..."
          style="
            width:100%;
            box-sizing:border-box;
            border:1px solid #cbd5e1;
            border-radius:8px;
            padding:9px;
            resize:vertical;
            font-size:13px;
            background:#fff;
          "
        ></textarea>

        <div style="
          display:flex;
          justify-content:flex-end;
          margin-top:8px;
        ">
          <button
            id="dsCareInternalNoteBtn"
            type="button"
            style="
              border:0;
              border-radius:8px;
              padding:9px 14px;
              background:#334155;
              color:#fff;
              font-weight:700;
              cursor:pointer;
            "
          >
            Add Internal Note
          </button>
        </div>

      </div>
    `;

    title.parentNode.insertBefore(
      panel,
      title.nextSibling
    );

    const refresh =
      document.getElementById(
        "dsCareTimelineRefresh"
      );

    if (refresh) {
      refresh.addEventListener(
        "click",
        function () {
          const thread =
            window.memberCareCurrentThread ||
            window.currentThread;

          if (thread) {
            loadTimeline(thread);
          }
        }
      );
    }

    const noteButton =
      document.getElementById(
        "dsCareInternalNoteBtn"
      );

    if (noteButton) {
      noteButton.addEventListener(
        "click",
        addInternalNote
      );
    }
  }


  async function loadTimeline(thread) {

    ensureTimelinePanel();

    const list =
      document.getElementById(
        "dsCareTimelineList"
      );

    if (!list || !thread || !thread.id) {
      return;
    }

    list.innerHTML = `
      <div style="
        color:#64748b;
        font-size:12px;
        padding:10px 0;
      ">
        Loading timeline...
      </div>
    `;

    try {

      const response =
        await fetch(
          "/api/customer-care/" +
          encodeURIComponent(thread.id) +
          "/timeline",
          {
            credentials:"same-origin"
          }
        );

      const data =
        await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Unable to load timeline"
        );
      }

      const items =
        Array.isArray(data.timeline)
          ? data.timeline
          : [];

      if (!items.length) {

        list.innerHTML = `
          <div style="
            color:#64748b;
            font-size:12px;
            padding:10px 0;
          ">
            No timeline activity yet.
          </div>
        `;

        return;
      }

      list.innerHTML =
        items.map(function (item) {

          const internal =
            item.visibility === "Internal";

          return `
            <div style="
              position:relative;
              padding:8px 8px 10px 18px;
              border-left:2px solid ${
                internal
                  ? "#94a3b8"
                  : "#16a34a"
              };
              margin-left:5px;
            ">

              <div style="
                font-weight:700;
                font-size:12px;
                color:#0f172a;
              ">
                ${internal ? "🔒 " : "● "}
                ${escTimeline(
                  item.action ||
                  "Case activity"
                )}
              </div>

              <div style="
                font-size:12px;
                color:#475569;
                margin-top:3px;
                white-space:pre-wrap;
                word-break:break-word;
              ">
                ${escTimeline(
                  item.details || ""
                )}
              </div>

              <div style="
                font-size:10px;
                color:#94a3b8;
                margin-top:4px;
              ">
                ${escTimeline(
                  item.actor_name || ""
                )}
                ${
                  item.actor_role
                    ? " · " +
                      escTimeline(
                        item.actor_role
                      )
                    : ""
                }
                ${
                  item.created_at
                    ? " · " +
                      escTimeline(
                        item.created_at
                      )
                    : ""
                }
              </div>

            </div>
          `;

        }).join("");

    } catch (err) {

      list.innerHTML = `
        <div style="
          color:#b91c1c;
          font-size:12px;
          padding:10px 0;
        ">
          ${escTimeline(
            err.message ||
            "Unable to load timeline"
          )}
        </div>
      `;
    }
  }


  async function addInternalNote() {

    const thread =
      window.memberCareCurrentThread ||
      window.currentThread;

    if (!thread || !thread.id) {
      alert(
        "Open a conversation first."
      );
      return;
    }

    const input =
      document.getElementById(
        "dsCareInternalNote"
      );

    const button =
      document.getElementById(
        "dsCareInternalNoteBtn"
      );

    const note =
      input
        ? input.value.trim()
        : "";

    if (!note) {
      alert(
        "Enter an internal note."
      );
      return;
    }

    if (button) {
      button.disabled = true;
      button.textContent =
        "Saving...";
    }

    try {

      const response =
        await fetch(
          "/api/customer-care/" +
          encodeURIComponent(thread.id) +
          "/internal-note",
          {
            method:"POST",
            credentials:"same-origin",
            headers:{
              "Content-Type":
                "application/json"
            },
            body:JSON.stringify({
              note:note
            })
          }
        );

      const data =
        await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Unable to save note"
        );
      }

      if (input) {
        input.value = "";
      }

      await loadTimeline(thread);

      if (button) {
        button.textContent =
          "Saved ✓";

        setTimeout(
          function () {
            button.textContent =
              "Add Internal Note";
          },
          1500
        );
      }

    } catch (err) {

      alert(
        err.message ||
        "Unable to save note"
      );

      if (button) {
        button.textContent =
          "Add Internal Note";
      }

    } finally {

      if (button) {
        button.disabled = false;
      }
    }
  }


  window.loadMemberCareTimeline =
    loadTimeline;

  window.ensureMemberCareTimeline =
    ensureTimelinePanel;


  const previousPopulate =
    window.populateMemberCareCase;

  window.populateMemberCareCase =
    function (thread) {

      if (
        typeof previousPopulate ===
        "function"
      ) {
        previousPopulate(thread);
      }

      ensureTimelinePanel();

      if (thread) {
        loadTimeline(thread);
      }
    };


})();
