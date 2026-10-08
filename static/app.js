const $=s=>document.querySelector(s);
const labels={online_giving:"Online Giving",church_accounts:"Church Accounts",customer_care:"Customer Care",conference:"Conference",command_centre:"Command Centre",communications:"Communications",reports:"Reports & Analytics",testimonies:"Testimonies",appreciations:"Special Appreciation",churches:"Local Churches",members:"Church Membership",commitments:"Pledges & Commitments",income:"Income Receipts",expenses:"Expenses",equipment:"Equipment Inventory",trust_fund:"Evangelism Trust Fund",mission_budgets:"Mission Budgets",procurement_requests:"Procurement & Equipment Requests",planting_prospects:"Church Planting Prospects",church_plants:"Church Planting",outreach:"Outreach & Missions",mission_calendar:"Mission Calendar & Follow-up",mission_teams:"Mission Teams",mission_contacts:"Evangelism Contacts & Follow-up",sponsors:"Partners & Sponsors",users:"User Management",audit:"Audit Log",security:"Security & Backup",system_health:"System Health",report_periods:"Reporting Periods",circuit_reports:"Circuit Reports",action_points:"Action Points",meetings:"Meetings & Minutes",diocesan_reviews:"Diocesan Executive Reviews"};
const schemas={
 church_accounts:[["account_level","Account Level","select",["Diocese","Circuit","Local Church"]],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Local Church","select",[]],["bank_name","Bank Name","text"],["account_name","Account Name","text"],["account_number","Account Number","text"],["account_type","Account Type","select",["Current","Savings","Domiciliary","Other"]],["branch","Bank Branch","text"],["notes","Notes","textarea"]],
 members:[
  ["role_position","Church Position / Office","select",["Bishop","Lay President","Evangelism Minister","Circuit Presbyter","Circuit Steward","Local Church Minister","Local Church Steward","Other"]],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],
  ["church_name","Local Church","select",[]],["full_name","Full Name","text"],["address","Address","text"],["phone","Phone Number","tel"],
  ["birthday","Birthday","date"],["gender","Gender","select",["","Male","Female"]],["fellowship","Fellowship","select",["Men","Women","Youth","Sunday School","Ladies & Girls","Lay Preacher","Minister"]],
  ["conference_awardee","Conference Awardee","select",["No","Yes"]],["conference_award","Conference Award","text"],["conference_award_year","Conference Award Year","number"],
  ["diocesan_awardee","Diocesan Awardee","select",["No","Yes"]],["diocesan_award","Diocesan Award","text"],["diocesan_award_year","Diocesan Award Year","number"],
  ["baptised","Baptised","select",["No","Yes"]],["baptism_date","Baptism Date","date"],
  ["confirmed","Confirmed","select",["No","Yes"]],["confirmation_date","Confirmation Date","date"],
  ["marriage","Marriage","select",["No","Yes"]],["marriage_date","Marriage Date","date"],
  ["relocated","Relocated","select",["No","Yes"]],["relocation_destination","Relocation Destination","text"],["relocation_date","Relocation Date","date"],
  ["transfer","Transfer","select",["No","Yes"]],["transfer_from","Transfer From","text"],["transfer_to","Transfer To","text"],["transfer_date","Transfer Date","date"],
  ["work_address","Place of Work Address","text"],["profession_business_trade","Profession / Business / Trade","text"],
  ["death","Death","select",["No","Yes"]],["death_date","Death Date","date"],
  ["seed_of_faith_payment","Seed of Faith Payment (₦)","number"],["tithe_payment","Tithe Payment (₦)","number"],["notes","Notes","textarea"]
 ],
 churches:[["circuit","Circuit","select",["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Church name","text"],["annual_target","Annual target (₦)","number"],["contact_person","Contact person","text"],["phone","Phone","tel"],["notes","Notes","textarea"]],
 commitments:[["date","Date","date"],["donor_name","Donor / partner name","text"],["donor_type","Donor type","select",["Individual","Local Church","Business","Major Patron","Mission Partner"]],["phone","Phone","tel"],["purpose","Purpose","select",["General Evangelism","Equipment Fund","Outreach Fund","Church Planting Fund","Training Fund","Mission Support Fund"]],["amount","Amount pledged (₦)","number"],["frequency","Frequency","select",["One-time","Monthly","Quarterly","Annual"]],["status","Status","select",["Pledged","Part-paid","Paid","Cancelled"]],["notes","Notes","textarea"]],
 income:[["date","Date received","date"],["donor_name","Donor name","text"],["source","Source","select",["Local Church","Evangelism Partner","Major Patron","Business Sponsor","Special Offering","Fundraising Event","In-kind converted value","Other"]],["fund","Fund / purpose","select",["General Evangelism","Equipment Fund","Outreach Fund","Church Planting Fund","Training Fund","Mission Support Fund"]],["amount","Amount received (₦)","number"],["method","Payment method","select",["Transfer","Cash","POS","Cheque","In-kind"]],["reference","Receipt / transaction reference","text"],["received_by","Received by","text"],["notes","Notes","textarea"]],
 expenses:[["date","Date paid","date"],["category","Category","select",["Outreach","Church Planting","Transport","Equipment","Training","Publicity / Media","Mission Support","Administration","Maintenance","Other"]],["description","Description","text"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Local Church","select",[]],["amount","Amount (₦)","number"],["approved_by","Approved by","text"],["paid_by","Paid by","text"],["receipt_ref","Receipt / voucher reference","text"],["notes","Notes","textarea"]],
 equipment:[["item","Equipment item","text"],["category","Category","select",["Sound","Music","Power","Field","Furniture","Media","Other"]],["quantity","Quantity","number"],["unit_cost","Unit cost (₦)","number"],["condition","Status / condition","select",["Planned","Good","Needs repair","Damaged","Disposed"]],["priority","Priority","select",["High","Medium","Low"]],["phase","Procurement phase","select",["Phase 1","Phase 2","Phase 3"]],["location","Current location","text"],["purchase_date","Purchase date","date"],["notes","Notes","textarea"]],
 trust_fund:[["date","Date","date"],["transaction_type","Transaction Type","select",["Income","Expense"]],["source_or_payee","Source / Payee","text"],["purpose","Purpose","select",["General Evangelism Trust Fund","Outreach","Church Planting","Equipment Procurement","Training","Mission Support","Other"]],["amount","Amount (₦)","number"],["method","Payment Method","select",["Transfer","Cash","POS","Cheque","In-kind"]],["reference","Reference / Voucher","text"],["approved_by","Approved By","text"],["received_or_paid_by","Received / Paid By","text"],["notes","Notes","textarea"]],
 mission_budgets:[["year","Budget Year","number"],["budget_name","Budget Name","text"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["category","Category","select",["Outreach","Church Planting","Equipment","Training","Mission Support","Publicity","Other"]],["planned_amount","Planned Amount (₦)","number"],["spent_amount","Spent Amount (₦)","number"],["status","Status","select",["Planned","Active","Completed","On Hold"]],["notes","Notes","textarea"]],
 procurement_requests:[["request_date","Request Date","date"],["item","Item / Equipment","text"],["category","Category","select",["Sound","Music","Power","Microphones","Speakers","Amplifiers","Band Set","Media","Transport","Other"]],["quantity","Quantity","number"],["estimated_unit_cost","Estimated Unit Cost (₦)","number"],["priority","Priority","select",["Critical","High","Medium","Low"]],["needed_by","Needed By","date"],["requested_by","Requested By","text"],["approval_status","Approval Status","select",["Pending","Approved","Purchased","Rejected"]],["supplier","Supplier / Source","text"],["notes","Notes","textarea"]],
 planting_prospects:[
 ["prospect_id","Prospect ID","text"],
 ["year","Year Identified","number"],
 ["circuit","Circuit","select",["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],
 ["location","Community / Proposed Location","text"],
 ["proposed_church_name","Proposed Church Name","text"],
 ["population_estimate","Estimated Population","number"],
 ["existing_methodist_presence","Existing Methodist Presence","select",["None","Prayer Group","Society / Fellowship","Local Church","Other"]],
 ["nearest_methodist_distance","Distance from Nearest Methodist Church (km)","number"],
 ["contact_person","Community Contact Person","text"],
 ["phone","Contact Phone","tel"],
 ["evangelism_status","Evangelism Status","select",["Identified","Surveying","Community Entry","Evangelism Active","Follow-up","Ready for Planting"]],
 ["outreach_status","Outreach Status","select",["Not Started","Scheduled","In Progress","Completed","Follow-up"]],
 ["priority","Priority","select",["High","Medium","Low"]],
 ["proposed_planting_year","Proposed Planting Year","number"],
 ["responsible_officer","Responsible Officer","text"],
 ["status","Prospect Status","select",["Prospect","Under Assessment","Approved for Planting","Converted to Church Plant","On Hold","Closed"]],
 ["notes","Remarks","textarea"]
],
church_plants:[["year","Target year","number"],["circuit","Circuit","select",["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["axis","Church-planting axis","text"],["location","Proposed location","text"],["phase","Mission phase","select",["Surveying","Community entry","Outreach","Follow-up","Meeting point","Launch preparation","Launch","Consolidation"]],["status","Status","select",["Planned","Surveying","Outreach started","Meeting point","Launched","Growing","Active","On hold"]],["budget","Budget (₦)","number"],["leader","Mission leader","text"],["start_date","Start date","date"],["launch_date","Launch date","date"],["next_followup_date","Next follow-up date","date"],["followup_end_date","Follow-up end date","date"],["members","Current members / contacts","number"],["notes","Notes","textarea"]],
 outreach:[["date","Mission date","date"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["location","Location","text"],["activity","Activity","select",["Street evangelism","Crusade","House-to-house","Campus outreach","Community service","Follow-up","Church launch","Other"]],["mission_phase","Mission phase","select",["Preparation","Outreach","Follow-up","Consolidation","Launch"]],["church_plant_axis","Church-planting axis (optional)","text"],["attendance","Attendance","number"],["decisions","Decisions / converts","number"],["followups","Follow-ups required","number"],["cost","Cost (₦)","number"],["lead_person","Lead person","text"],["next_followup_date","Next follow-up date","date"],["notes","Notes","textarea"]],
 mission_calendar:[["event_date","Mission / Event Date","date"],["event_time","Time","time"],["event_type","Event Type","select",["Outreach","Follow-up Visit","Prayer Meeting","Training","Community Entry","Church Plant Preparation","Church Plant Launch","Consolidation","Leadership Meeting","Other"]],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["location","Location / Venue","text"],["activity","Activity / Mission","text"],["mission_phase","Mission Phase","select",["Preparation","Community Entry","Outreach","Follow-up","Launch Preparation","Launch","Consolidation"]],["church_plant_id","Church Plant Record ID (optional)","number"],["responsible_person","Responsible Person / Team","text"],["expected_outcome","Expected Outcome","textarea"],["followup_date","Follow-up Due Date","date"],["status","Status","select",["Scheduled","Preparation","In Progress","Follow-up Due","Completed","Cancelled"]],["notes","Notes","textarea"]],
 mission_teams:[["team_name","Team Name","text"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Base / Local Church","select",[]],["leader","Team Leader","text"],["members","Team Members","textarea"],["mission_type","Mission Type","select",["Outreach","Follow-up","Church Planting","Prayer","Community Service","Youth Evangelism","Children Evangelism","Other"]],["active","Active Team","select",["Yes","No"]],["phone","Team Contact Phone","tel"],["notes","Notes","textarea"]],
 mission_contacts:[["contact_name","Contact / Convert Name","text"],["phone","Phone Number","tel"],["address","Address","text"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Follow-up Local Church","select",[]],["source_mission","Source Mission / Event","text"],["mission_date","Date First Reached","date"],["status","Spiritual / Membership Status","select",["New Contact","New Convert","Under Discipleship","Ready for Church","Joined Local Church","Transferred","Inactive"]],["assigned_to","Follow-up Assigned To","text"],["next_followup_date","Next Follow-up Date","date"],["followup_status","Follow-up Status","select",["Pending","Visited","Rescheduled","Completed","Closed"]],["outcome","Latest Follow-up Outcome","textarea"],["member_id","Member ID (when registered)","text"],["church_plant_id","Church Plant Record ID (optional)","number"],["notes","Notes","textarea"]],
 testimonies:[["date","Date","date"],["member_name","Member Name","text"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Local Church","select",[]],["title","Testimony Title","text"],["testimony","Testimony","textarea"]],
 appreciations:[["date","Date","date"],["recipient","Recipient","text"],["role_position","Position / Office","select",["Bishop","Lay President","Evangelism Minister","Circuit Presbyter","Circuit Steward","Local Church Minister","Local Church Steward","Other"]],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Local Church","select",[]],["reason","Reason for Appreciation","text"],["message","Appreciation Message","textarea"]],
 sponsors:[["name","Contact / sponsor name","text"],["organization","Organization","text"],["phone","Phone","tel"],["email","Email","email"],["sponsorship_type","Support type","select",["Financial","Equipment","Transport","Venue","Media","Professional service","Other"]],["amount","Potential / agreed value (₦)","number"],["status","Status","select",["Prospect","Contacted","Meeting scheduled","Committed","Received","Not proceeding"]],["next_contact","Next contact date","date"],["notes","Notes","textarea"]],
 report_periods:[["period_name","Period Name","text"],["period_type","Period Type","select",["Monthly","Quarterly","Half-Year","Annual","Special Review"]],["start_date","Start Date","date"],["end_date","End Date","date"],["submission_due","Submission Due Date","date"],["status","Status","select",["Open","Closed","Under Review"]],["instructions","Submission Instructions","textarea"]],
 circuit_reports:[["period_id","Reporting Period ID (optional)","number"],["period_name","Reporting Period","text"],["circuit","Circuit","select",["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["outreach_missions","Outreach Missions","number"],["people_reached","People Reached","number"],["decisions","Decisions / Converts","number"],["followups_completed","Follow-ups Completed","number"],["church_plants_active","Active Church Plants","number"],["churches_launched","Churches Launched","number"],["testimonies","Testimonies","number"],["challenges","Challenges","textarea"],["achievements","Key Achievements","textarea"],["needs_support","Support Required","textarea"],["financial_note","Financial Note","textarea"]],
 action_points:[["period_id","Reporting Period ID (optional)","number"],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["action_item","Action Item","textarea"],["responsible_person","Responsible Person","text"],["due_date","Due Date","date"],["priority","Priority","select",["High","Medium","Low"]],["status","Status","select",["Open","In Progress","Completed","Deferred","Cancelled"]],["completion_note","Completion Note","textarea"]],
 meetings:[["meeting_date","Meeting Date","date"],["meeting_type","Meeting Type","select",["Diocesan Evangelism Committee","Circuit Evangelism Meeting","Church Planting Review","Finance Review","Leadership Meeting","Special Meeting","Other"]],["circuit","Circuit","select",["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["location","Location","text"],["chairperson","Chairperson","text"],["secretary","Secretary","text"],["attendance","Attendance / Participants","textarea"],["agenda","Agenda","textarea"],["minutes","Minutes","textarea"],["decisions","Decisions / Resolutions","textarea"],["next_meeting","Next Meeting","date"]],
 diocesan_reviews:[["period_id","Reporting Period ID (optional)","number"],["period_name","Reporting Period","text"],["review_date","Review Date","date"],["executive_summary","Executive Summary","textarea"],["key_achievements","Key Achievements","textarea"],["major_challenges","Major Challenges","textarea"],["decisions","Decisions / Directives","textarea"],["support_required","Support Required","textarea"],["status","Status","select",["Draft","Prepared","Approved"]],["notes","Notes","textarea"]],
 users:[["username","Username","text"],["password","Temporary password (min 8 characters)","password"],["role","Role","select",["Admin","Bishop / Diocesan Executive","Evangelism Minister","Planting Officer","Diocesan Secretary","Circuit Coordinator","Local Church Evangelism Officer","Finance Officer","Auditor"]],["circuit","Assigned circuit","select",["","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Assigned church (optional)","text"]]
};
let current="dashboard",records=[],me=null,circuitOptions=["Diocesan","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"];
const money=n=>n===null||n===undefined?"—":"₦"+Number(n||0).toLocaleString("en-NG",{maximumFractionDigits:0});
function setStatus(s){$("#status").textContent=s}
async function checkPaystackReturn(){
  const params = new URLSearchParams(window.location.search);
  const reference = params.get("reference") || params.get("trxref");
  if(!reference) return;

  const box = $("#paymentResult");
  const title = $("#paymentResultTitle");
  const message = $("#paymentResultMessage");
  const refEl = $("#paymentResultReference");
  const amountEl = $("#paymentResultAmount");

  if(box) box.hidden = false;
  if(title) title.textContent = "Verifying Payment";
  if(message) message.textContent = "Please wait while we verify your Paystack transaction.";
  if(refEl) refEl.textContent = reference;

  try{
    const result = await api("/api/payment/verify/" + encodeURIComponent(reference));

    if(result.paid){
      if(title) title.textContent = "Payment Successful";
      if(message) message.textContent = "Your payment has been verified and recorded successfully.";
      if(amountEl) amountEl.textContent = result.amount != null ? money(result.amount) : "Verified";
    }else{
      if(title) title.textContent = "Payment Not Completed";
      if(message) message.textContent = "Paystack has not marked this transaction as successful.";
      if(amountEl) amountEl.textContent = result.amount != null ? money(result.amount) : "Pending";
    }
  }catch(err){
    if(title) title.textContent = "Payment Verification Error";
    if(message) message.textContent = err.message;
  }
}

async function loadOnlineGiving(){
  try{
    const accounts=await api("/api/church-accounts");
    const select=$("#givingAccount");
    if(!select)return;

    const list=Array.isArray(accounts)?accounts:(
      accounts.accounts||accounts.data||[]
    );

    select.innerHTML='<option value="">Select church account</option>'+list.map(a=>{
      const scope=[a.account_level,a.circuit,a.church_name].filter(Boolean).join(" · ");
      return `<option value="${a.id}" data-level="${esc(a.account_level||"")}" data-circuit="${esc(a.circuit||"")}" data-church="${esc(a.church_name||"")}">${esc(a.account_name)} — ${esc(a.bank_name)} (${esc(a.account_number)})${scope?" · "+esc(scope):""}</option>`;
    }).join("");

    if(!list.length){
      select.innerHTML='<option value="">No active church accounts available</option>';
    }
  }catch(e){
    const select=$("#givingAccount");
    if(select)select.innerHTML='<option value="">Unable to load church accounts</option>';
    const status=$("#givingStatus");
    if(status)status.textContent=e.message;
  }
}

checkPaystackReturn();

document.addEventListener("submit",async function(e){
  if(e.target.id!=="onlineGivingForm")return;
  e.preventDefault();

  const account=$("#givingAccount");
  const selected=account?.selectedOptions?.[0];

  if(!selected || !selected.value){
    alert("Please select a church account.");
    return;
  }

  const amount=Number($("#givingAmount")?.value||0);
  if(amount<=0){
    alert("Please enter a valid payment amount.");
    return;
  }

  const email=$("#givingEmail")?.value.trim();
  if(!email){
    alert("Please enter your email address.");
    return;
  }

  const btn=$("#paystackPayBtn");
  const status=$("#givingStatus");

  try{
    if(btn)btn.disabled=true;
    if(status)status.textContent="Connecting securely to Paystack...";

    const result=await api("/api/payment/initiate",{
      method:"POST",
      body:JSON.stringify({
        amount:amount,
        purpose:$("#givingPurpose")?.value||"",
        account_level:selected.dataset.level||"",
        circuit:selected.dataset.circuit||"",
        church_name:selected.dataset.church||"",
        church_account_id:Number(selected.value),
        donor_name:$("#givingName")?.value.trim()||"",
        donor_email:email,
        donor_phone:$("#givingPhone")?.value.trim()||"",
        payment_method:"Paystack"
      })
    });

    if(!result.authorization_url){
      throw Error("Paystack did not return a checkout URL.");
    }

    if(status)status.textContent="Opening secure Paystack checkout...";
    window.location.href=result.authorization_url;
  }catch(err){
    if(status)status.textContent=err.message;
    alert(err.message);
    if(btn)btn.disabled=false;
  }
});


async function api(url,opts={}){let r;try{r=await fetch(url,{headers:{"Content-Type":"application/json",...(opts.headers||{})},...opts})}catch(e){throw Error("Cannot connect to the app server. Make sure Flask is running in Termux.")}const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(e){}if(r.status===401){location.href="/login";throw Error("Authentication required")};if(r.status===403&&d.code==="PASSWORD_CHANGE_REQUIRED"){location.href="/change-password";throw Error(d.error)};if(!r.ok)throw Error((d.error||`Request failed (HTTP ${r.status})`)+(d.detail?` — ${d.detail}`:""));return d}
function canPage(page){
  if(!me)return false;

  const role = me.role;

  const access = {
    Admin: [
      "dashboard","communications","conference","command_centre","churches",
      "members","mission_teams","mission_contacts","testimonies","appreciations",
      "commitments","income","church_accounts","online_giving","payment_management",
      "payment_reconciliation","finance_summary","financial_accountability","expenses",
      "equipment","trust_fund","mission_budgets","procurement_requests","planting_prospects",
      "church_plants","outreach","mission_calendar","sponsors","report_periods",
      "circuit_reports","action_points","meetings","diocesan_reviews","reports",
      "users","audit","security","system_health"
    ],

    "Member": [
      "dashboard","communications","conference","online_giving","reports"
    ],

    "Bishop / Diocesan Executive": [
      "dashboard","communications","conference","command_centre","churches",
      "members","mission_teams","mission_contacts","testimonies","appreciations",
      "planting_prospects","church_plants","outreach","mission_calendar",
      "report_periods","circuit_reports","action_points","meetings","diocesan_reviews",
      "reports","audit"
    ],

    "Evangelism Minister": [
      "dashboard","communications","conference","command_centre","churches",
      "members","mission_teams","mission_contacts","testimonies","appreciations",
      "commitments","income","expenses","equipment","sponsors","trust_fund",
      "mission_budgets","procurement_requests","planting_prospects","church_plants",
      "outreach","mission_calendar","report_periods","circuit_reports",
      "action_points","meetings","diocesan_reviews","reports"
    ],

    "Planting Officer": [
      "dashboard","communications","conference","command_centre","churches",
      "members","mission_teams","mission_contacts","testimonies","appreciations",
      "planting_prospects","church_plants","outreach","mission_calendar",
      "reports"
    ],

    "Diocesan Secretary": [
      "dashboard","communications","conference","command_centre","churches",
      "members","report_periods","circuit_reports","action_points","meetings",
      "diocesan_reviews","reports"
    ],

    "Circuit Coordinator": [
      "dashboard","communications","conference","command_centre","churches",
      "members","mission_teams","mission_contacts","testimonies","appreciations",
      "planting_prospects","church_plants","outreach","mission_calendar",
      "action_points","reports"
    ],

    "Local Church Evangelism Officer": [
      "dashboard","communications","conference","churches","members",
      "mission_teams","mission_contacts","testimonies","appreciations",
      "planting_prospects","outreach","mission_calendar","reports"
    ],

    "Finance Officer": [
      "dashboard","communications","conference","churches","members",
      "commitments","income","church_accounts","online_giving","payment_management",
      "payment_reconciliation","finance_summary","financial_accountability",
      "expenses","equipment","sponsors","trust_fund","mission_budgets",
      "procurement_requests","reports"
    ],

    "Auditor": [
      "dashboard","communications","conference","command_centre","churches",
      "members","testimonies","appreciations","commitments","income",
      "expenses","equipment","sponsors","trust_fund","mission_budgets",
      "procurement_requests","report_periods","circuit_reports","action_points",
      "meetings","diocesan_reviews","reports","audit","security","system_health"
    ]
  };

  return (access[role] || []).includes(page);
}

function configureNav(){
  document.querySelectorAll("#menuPanel button[data-page]").forEach(b=>{
    const allowed=canPage(b.dataset.page);b.hidden=!allowed;b.style.display=allowed?"":"none";
  });

  $("#exportBtn").hidden=!([
    "Admin",
    "Finance Officer",
    "Auditor",
    "Evangelism Minister",
    "Bishop / Diocesan Executive"
  ].includes(me.role));

  $("#backupBtn").hidden=!([
    "Admin",
    "Auditor"
  ].includes(me.role));

  $("#whoami").textContent=
    `Signed in: ${me.username} · ${me.role}`+
    `${me.circuit?" · "+me.circuit:""}`+
    `${me.church_name?" · "+me.church_name:""}`;

  $("#userLine").textContent=
    `${me.role}${me.circuit?" · "+me.circuit:""}`;
}

function nav(page){if(!canPage(page))return;current=page;document.querySelectorAll("#menuPanel button[data-page]").forEach(b=>b.classList.toggle("active",b.dataset.page===page));const chosen=document.querySelector(`#menuPanel button[data-page="${page}"]`);if(chosen){const label=$("#menuCurrent");if(label)label.textContent=chosen.textContent.trim();}closeMenu();document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));if(page==="dashboard"){$("#dashboard").classList.add("active");loadDashboard();loadReportingSummary();loadConnection()}else if(page==="command_centre"){$("#command_centre").classList.add("active");loadCommandCentre()}else if(page==="communications"){$("#communications").classList.add("active");loadCommunications()}else if(page==="customer_care"){$("#customer_care").classList.add("active");loadCustomerCare()}else if(page==="conference"){$("#conference").classList.add("active");loadConference()}else if(page==="reports"){$("#reports").classList.add("active");loadReports()}else if(page==="security"){$("#security").classList.add("active");loadSecurityCentre()}else if(page==="system_health"){$("#system_health").classList.add("active");loadSystemHealth()}else if(page==="online_giving"){$("#online_giving").classList.add("active");loadOnlineGiving()}else if(page==="payment_management"){$("#payment_management").classList.add("active");loadPaymentManagement()}else if(page==="payment_reconciliation"){$("#payment_reconciliation").classList.add("active");loadPaymentReconciliation()}else if(page==="finance_summary"){$("#finance_summary").classList.add("active");loadFinanceSummary()}else if(page==="financial_accountability"){$("#financial_accountability").classList.add("active");loadFinancialAccountabilityReport()}else{$("#dataPage").classList.add("active");$("#sectionTitle").textContent=labels[page];$("#sectionEyebrow").textContent=page==="audit"?"SECURITY & ACCOUNTABILITY":page==="users"?"SECURE ACCESS":"MANAGE RECORDS";$("#formWrap").hidden=true;$("#search").value="";$("#addBtn").hidden=page==="audit"||me.role==="Auditor";loadTable();if(page==="members")loadMemberRegistrations();else if(page==="users")loadAccountRequests();else{if($("#memberRegistrationsPanel"))$("#memberRegistrationsPanel").hidden=true;if($("#accountRequestsPanel"))$("#accountRequestsPanel").hidden=true}}}
document.querySelectorAll("#menuPanel button[data-page]").forEach(b=>b.addEventListener("click",()=>nav(b.dataset.page)));
function closeMenu(){const panel=$("#menuPanel"),toggle=$("#menuToggle");if(panel)panel.classList.remove("open");if(toggle){toggle.setAttribute("aria-expanded","false")}}
$("#menuToggle")?.addEventListener("click",()=>{const panel=$("#menuPanel"),toggle=$("#menuToggle");if(!panel||!toggle)return;const open=panel.classList.toggle("open");toggle.setAttribute("aria-expanded",String(open))});
document.addEventListener("click",e=>{if(!e.target.closest(".nav-dropdown"))closeMenu()});
async function loadMe(){me=await api("/api/me");configureNav()}
async function loadConnection(){try{const d=await api("/api/connection");$("#connectionUrl").textContent=d.url;$("#connectionStatus").textContent="Other phones must be on the same Wi-Fi or hotspot.";const img=$("#connectionQrImg");img.src="/api/qr?ts="+Date.now();img.onload=()=>$(".qr-box").classList.add("ready");img.onerror=()=>{$("#connectionStatus").textContent="QR image could not be loaded."}}catch(e){$("#connectionUrl").textContent="Unable to detect host address";$("#connectionStatus").textContent=e.message}}
$("#copyUrlBtn").onclick=async()=>{const url=$("#connectionUrl").textContent;if(!url.startsWith("http"))return;try{await navigator.clipboard.writeText(url);$("#copyUrlBtn").textContent="Copied";setTimeout(()=>$("#copyUrlBtn").textContent="Copy address",1500)}catch(e){alert("Copy failed. Long-press the address to copy it.")}};
async function loadCommandCentre(){try{const d=await api("/api/command-centre");$("#commandScope").textContent=`${d.year} · ${d.scope}`;const s=d.summary||{};const cards=[["Active members",s.members],["Local churches",s.churches],["Church plants",s.plants,`${s.launched} launched / active`],["Outreach missions",s.outreach],["People reached",s.contacts],["Decisions / converts",s.decisions],["Follow-ups due",s.followups_due],["Action points open",s.action_open]];$("#commandSummary").innerHTML=cards.map(x=>reportCard(x[0],x[1],x[2]||"")).join("");$("#commandCircuits").innerHTML=(d.circuits||[]).map(r=>{const pct=Math.min(100,(r.plants/5)*100);return `<div class="bar-row"><div class="bar-label"><strong>${esc(r.circuit)}</strong><span>${r.members} members · ${r.outreach} outreach · ${r.decisions} decisions</span></div><div class="progress"><span style="width:${pct}%"></span></div><div class="bar-meta"><span>Plants ${r.plants}/5</span><span>Launched ${r.launched}</span><span>Joined ${r.joined||0}</span><span>Gap ${r.plant_gap}</span></div></div>`}).join("")||'<div class="empty">No circuit data.</div>';
const alerts=[['Follow-ups overdue',s.followups_overdue,'mission_contacts'],['Action points overdue',s.action_overdue,'action_points'],['Reports needing attention',s.reports_pending,'circuit_reports']];$("#commandAlerts").innerHTML=alerts.map(a=>`<div class="alert-row ${a[1]>0?'alert-hot':''}"><div><strong>${a[0]}</strong><span>${a[1]>0?'Requires attention':'No outstanding item'}</span></div><button class="secondary" onclick="nav('${a[2]}')">Open</button></div>`).join("");
$("#commandFollowups").innerHTML=d.followups?.length?d.followups.map(r=>`<div class="simple-row"><div><strong>${esc(r.contact_name)}</strong><small>${esc(r.circuit||'Diocesan')} · ${esc(r.assigned_to||'Unassigned')}</small></div><span class="status-badge">${esc(r.next_followup_date)}</span></div>`).join(""):'<div class="empty">No follow-ups due.</div>';
$("#commandMissions").innerHTML=d.upcoming_missions?.length?d.upcoming_missions.map(r=>`<div class="simple-row"><div><strong>${esc(r.activity||r.event_type)}</strong><small>${esc(r.event_date)} · ${esc(r.location||'Venue not set')}</small></div><span>${esc(r.status||'Scheduled')}</span></div>`).join(""):'<div class="empty">No upcoming missions.</div>';
$("#commandActions").innerHTML=d.actions?.length?d.actions.map(r=>`<div class="simple-row"><div><strong>${esc(r.action_item)}</strong><small>${esc(r.circuit||'Diocesan')} · ${esc(r.responsible_person||'Unassigned')}</small></div><span>${esc(r.due_date||'No due date')} · ${esc(r.status)}</span></div>`).join(""):'<div class="empty">No open action points.</div>';
const fp=$("#commandFinancePanel");if(!d.finance_visible){fp.hidden=true}else{fp.hidden=false;const f=d.finance;$("#commandFinance").innerHTML=[['Operating balance',money(f.balance)],['Trust Fund balance',money(f.trust_balance)],['Operating income',money(f.income)],['Operating expenses',money(f.expenses)],['Procurement pipeline',money(f.procurement_pipeline)]].map(x=>`<div class="finance-report-row"><span>${x[0]}</span><strong>${x[1]}</strong></div>`).join("")}}catch(e){$("#commandSummary").innerHTML=`<div class="empty">${esc(e.message)}</div>`}}

async function loadMembershipStatistics(){
  try{
    const d = await api("/api/membership-statistics");
    const el = document.querySelector("#membershipStatistics");
    if(!el) return;

    const cards = [
      ["Total Members", d.total_members],
      ["Men", d.male],
      ["Women", d.female],
      ["Youth", d.youth],
      ["Children", d.children],
      ["Baptised", d.baptised],
      ["Confirmed", d.confirmed],
      ["Married", d.married],
      ["New Members", d.new_members],
      ["Transfers", d.transferred],
      ["Relocations", d.relocated],
      ["Conference Awardees", d.conference_awardees],
      ["Diocesan Awardees", d.diocesan_awardees]
    ];

    el.innerHTML = cards.map(c =>
      `<div class="report-card">
        <span>${esc(c[0])}</span>
        <strong>${Number(c[1] || 0)}</strong>
      </div>`
    ).join("");

    const circuitEl = document.querySelector("#membershipCircuitReport");
    if(circuitEl){
      const circuitRows = Object.entries(d.circuits || {});
      circuitEl.innerHTML = circuitRows.length
        ? circuitRows.map(([name,count]) =>
            `<div class="simple-row">
              <strong>${esc(name)}</strong>
              <span>${Number(count || 0)}</span>
            </div>`
          ).join("")
        : '<div class="empty">No circuit membership data.</div>';
    }

    const churchEl = document.querySelector("#membershipChurchReport");
    if(churchEl){
      const groups = Object.entries(d.churches || {});
      churchEl.innerHTML = groups.length
        ? groups.map(([circuit, churches]) =>
            `<div class="membership-church-group">
              <h4>${esc(circuit)}</h4>
              ${Object.entries(churches || {}).map(([church,count]) =>
                `<div class="simple-row">
                  <span>${esc(church)}</span>
                  <strong>${Number(count || 0)}</strong>
                </div>`
              ).join("")}
            </div>`
          ).join("")
        : '<div class="empty">No local church membership data.</div>';
    }
  }catch(e){
    const el = document.querySelector("#membershipStatistics");
    if(el) el.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}


async function loadReports(){
  await loadMembershipStatistics();
 const y=document.querySelector("#reportYear"), c=document.querySelector("#reportCircuit");
 if(!y)return;
 if(!y.options.length){const now=new Date().getFullYear();for(let i=now-2;i<=now+6;i++){const o=document.createElement("option");o.value=i;o.textContent=i;if(i===now)o.selected=true;y.appendChild(o)}}
 try{const reportUrl=`/api/reports?year=${encodeURIComponent(y.value)}&circuit=${encodeURIComponent(c.value)}`;const exportEl=document.querySelector("#reportExportBtn");if(exportEl)exportEl.href=`/api/reports/export?year=${encodeURIComponent(y.value)}&circuit=${encodeURIComponent(c.value)}`;const d=await api(reportUrl);renderReports(d)}catch(e){["reportSummary","circuitReport","fellowshipReport","fiveYearReport","funnelReport","financeReport"].forEach(id=>{const el=document.getElementById(id);if(el)el.innerHTML=`<div class="empty">${esc(e.message)}</div>`})}
}
function reportCard(label,value,sub=""){return `<div class="report-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(sub)}</small></div>`}
function renderReports(d){
 const s=d.summary||{};document.querySelector("#reportScope").textContent=`${d.year} · ${d.circuit}`;
 document.querySelector("#reportSummary").innerHTML=[reportCard("Active Members",s.members),reportCard("Local Churches",s.churches),reportCard("Church Plants",s.plants,`${s.launched_plants} launched / active`),reportCard("Outreach Missions",s.outreach),reportCard("People Reached",s.contacts),reportCard("Decisions / Converts",s.decisions),reportCard("Joined Local Church",s.joined),reportCard("Follow-ups Due",s.followups_due)].join("");
 document.querySelector("#circuitReport").innerHTML=d.circuits.length?`<div class="bar-table">${d.circuits.map(r=>{const pct=Math.min(100,(r.plants||0)/5*100);return `<div class="bar-row"><div class="bar-label"><strong>${esc(r.circuit)}</strong><span>${r.members} members · ${r.outreach} outreach · ${r.decisions} decisions</span></div><div class="progress"><span style="width:${pct}%"></span></div><div class="bar-meta"><span>Plants: ${r.plants}</span><span>Launched: ${r.launched}</span><span>Joined: ${r.joined}</span></div></div>`}).join("")}</div>`:'<div class="empty">No circuit data.</div>';
 document.querySelector("#fellowshipReport").innerHTML=d.fellowships.length?d.fellowships.map(r=>`<div class="simple-row"><strong>${esc(r.fellowship||"Not specified")}</strong><span>${r.count}</span></div>`).join(""):'<div class="empty">No membership data.</div>';
 document.querySelector("#fiveYearReport").innerHTML=d.five_year.map(r=>`<div class="roadmap-report-row"><div><strong>${r.year}</strong><span>Target ${r.target}</span></div><div class="progress"><span style="width:${Math.min(100,(r.planned/r.target)*100)}%"></span></div><div class="roadmap-numbers"><span>Planned ${r.planned}</span><span>Launched ${r.launched}</span><span>Remaining ${r.remaining}</span></div></div>`).join("");
 const funnel=[['People reached',s.contacts],['New/active converts',s.converts],['Joined local church',s.joined],['Follow-ups due',s.followups_due]];document.querySelector("#funnelReport").innerHTML=funnel.map((x,i)=>`<div class="funnel-row"><div class="funnel-label"><span>${esc(x[0])}</span><strong>${x[1]}</strong></div><div class="funnel-bar"><span style="width:${s.contacts?Math.min(100,Math.max(5,(x[1]/s.contacts)*100)):0}%;animation-delay:${i*.12}s"></span></div></div>`).join("");
 const fp=document.querySelector("#reportFinancePanel"); if(!d.finance_visible){fp.hidden=true}else{fp.hidden=false;const f=d.finance;document.querySelector("#financeReport").innerHTML=[['Operating income',money(f.income)],['Operating expenses',money(f.expenses)],['Operating balance',money(f.balance)],['Trust Fund income',money(f.trust_income)],['Trust Fund expenses',money(f.trust_expense)],['Trust Fund balance',money(f.trust_balance)],['Planned mission budget',money(f.planned_budget)],['Mission budget spent',money(f.spent_budget)],['Procurement pipeline',money(f.procurement_pipeline)]].map(x=>`<div class="finance-report-row"><span>${x[0]}</span><strong>${x[1]}</strong></div>`).join("")}
}
async function loadReportingSummary(){const el=document.getElementById("reportingControl");if(!el)return;try{const d=await api("/api/admin/reporting-summary");const rs=Object.fromEntries((d.report_status||[]).map(x=>[x.status,x.count]));const as=Object.fromEntries((d.action_status||[]).map(x=>[x.status,x.count]));el.innerHTML=`<div><span>OPEN PERIODS</span><strong>${(d.periods||[]).filter(x=>x.status==="Open").length}</strong></div><div><span>SUBMITTED</span><strong>${rs.Submitted||0}</strong></div><div><span>APPROVED</span><strong>${rs.Approved||0}</strong></div><div><span>RETURNED</span><strong>${rs.Returned||0}</strong></div><div><span>ACTION POINTS OPEN</span><strong>${(as.Open||0)+(as["In Progress"]||0)}</strong></div><div><span>MEETINGS RECORDED</span><strong>${d.meetings||0}</strong></div>`}catch(e){el.innerHTML=`<div><span>ACCOUNTABILITY</span><strong>Use reporting centre</strong></div>`}}
async function loadDashboard(){try{const d=await api("/api/dashboard");let stats=[["Local churches",d.churches],["Church members",d.members],["Church plants planned",d.plants],["Active / launched",d.active_plants],["Outreach records",d.outreach],["Mission calendar",d.calendar],["Testimonies",d.testimonies],["Special Appreciation",d.appreciations],["Annual planting target","5 / year"]];if(d.finance_visible)stats=[["Local churches",d.churches],["Church members",d.members],["Total income",money(d.income)],["Total expenses",money(d.expenses)],["Available balance",money(d.balance)],["Trust Fund balance",money(d.trust_balance)],["Trust Fund income",money(d.trust_income)],["Trust Fund expenses",money(d.trust_expense)],["Pledges outstanding",money(d.pledges)],["Testimonies",d.testimonies],["Special Appreciation",d.appreciations],["Church plants planned",d.plants],["Active / launched",d.active_plants],["Upcoming missions",d.calendar],["Annual planting target","5 / year"]];$("#stats").innerHTML=stats.map(([a,b])=>`<div class="stat"><span>${a}</span><strong>${b}</strong></div>`).join("");$("#incomePanel").hidden=!d.finance_visible;$("#expensePanel").hidden=!d.finance_visible;$("#recentIncome").innerHTML=miniTable(d.recent_income,["date","donor_name","fund","amount"]);$("#recentExpenses").innerHTML=miniTable(d.recent_expenses,["date","category","description","amount"]);
const trust=document.getElementById("trustFinance");if(trust)trust.innerHTML=`<div class="finance-spotlight"><div><span>TRUST FUND BALANCE</span><strong>${money(d.trust_balance||0)}</strong></div><div><span>INCOME</span><strong>${money(d.trust_income||0)}</strong></div><div><span>EXPENSE</span><strong>${money(d.trust_expense||0)}</strong></div></div>${miniTable(d.recent_trust||[],["date","transaction_type","source_or_payee","amount"])}`;
const proc=document.getElementById("procurementSummary");if(proc)proc.innerHTML=`<div class="finance-spotlight"><div><span>PENDING / APPROVED REQUESTS</span><strong>${(d.pending_procurement||[]).length}</strong></div><div><span>ESTIMATED VALUE</span><strong>${money(d.procurement_value||0)}</strong></div><div><span>MISSION BUDGET PLANNED</span><strong>${money(d.planned_budget||0)}</strong></div><div><span>BUDGET SPENT</span><strong>${money(d.spent_budget||0)}</strong></div></div>`;
spotlightCard(d.recent_testimonies,"testimony");spotlightCard(d.recent_appreciations,"appreciation");renderPlantPlan(d.plant_plan||[]);renderMissionCalendar(d.upcoming_missions||[],d.overdue_followups||[]);renderContactFollowups(d.contact_followups||[],d.recent_contacts||[])}catch(e){setStatus(e.message)}}
function renderPlantPlan(plan){const el=$("#plantPlan");if(!el)return;const totalTarget=plan.reduce((a,x)=>a+x.target,0), totalPlanned=plan.reduce((a,x)=>a+x.planned,0), totalLaunched=plan.reduce((a,x)=>a+x.launched,0);el.innerHTML=`<div class="plant-summary"><div><span>5-year target</span><strong>${totalTarget} churches</strong></div><div><span>Planned</span><strong>${totalPlanned}</strong></div><div><span>Launched / growing</span><strong>${totalLaunched}</strong></div></div><div class="plant-roadmap">${plan.map(x=>{const pct=Math.min(100,Math.round((x.planned/x.target)*100));return `<div class="plant-year"><div class="plant-year-head"><strong>${x.year}</strong><span>${x.planned}/${x.target} planned · ${x.launched} launched</span></div><div class="progress"><span style="width:${pct}%"></span></div><div class="plant-meta"><span>Growing: ${x.growing}</span><span>Remaining: ${x.remaining}</span><span>Budget: ${money(x.budget)}</span></div></div>`}).join("")}</div>`}
function renderMissionCalendar(upcoming,overdue){const el=$("#missionCalendar");if(!el)return;const fmt=r=>{const d=r.event_date||"";return d?new Date(d+"T00:00:00").toLocaleDateString("en-NG",{day:"2-digit",month:"short",year:"numeric"}):"Date not set"};const item=r=>`<div class="mission-event"><div class="mission-date"><strong>${esc(fmt(r))}</strong><span>${esc(r.event_time||"")}</span></div><div class="mission-event-main"><div class="mission-event-top"><strong>${esc(r.event_type||"Mission")}</strong><span class="mission-status ${String(r.status||"").toLowerCase().replaceAll(" ","-")}">${esc(r.status||"Scheduled")}</span></div><div class="mission-location">${esc(r.location||"Location not set")} · ${esc(r.circuit||"Diocesan")}</div><div class="mission-activity">${esc(r.activity||"")}</div>${r.followup_date?`<div class="mission-followup">Follow-up: ${esc(r.followup_date)}</div>`:""}</div></div>`;const upcomingHtml=upcoming&&upcoming.length?upcoming.map(item).join(""):'<div class="empty">No upcoming missions scheduled.</div>';const overdueHtml=overdue&&overdue.length?overdue.map(r=>item(r).replace('class="mission-event"','class="mission-event overdue"')).join(""):'<div class="empty">No overdue follow-ups. Good work!</div>';el.innerHTML=`<div class="calendar-columns"><div><div class="calendar-subhead"><span>UPCOMING MISSIONS</span><strong>${upcoming?upcoming.length:0}</strong></div>${upcomingHtml}</div><div><div class="calendar-subhead overdue-head"><span>FOLLOW-UPS NEEDING ATTENTION</span><strong>${overdue?overdue.length:0}</strong></div>${overdueHtml}</div></div>`}
function renderContactFollowups(items,recent){const el=$("#contactFollowups");if(!el)return;const follow=items&&items.length?items.map(r=>`<div class="contact-follow-item"><div class="contact-avatar">${esc((r.contact_name||"?").trim().charAt(0).toUpperCase())}</div><div class="contact-main"><strong>${esc(r.contact_name||"Contact")}</strong><span>${esc(r.assigned_to||"Unassigned")} · ${esc(r.next_followup_date||"Date not set")}</span><small>${esc(r.outcome||r.status||"Follow-up pending")}</small></div><span class="contact-pill">${esc(r.followup_status||"Pending")}</span></div>`).join(""):'<div class="empty">No follow-ups needing attention.</div>';const recentHtml=recent&&recent.length?recent.slice(0,4).map(r=>`<div class="contact-recent"><strong>${esc(r.contact_name||"Contact")}</strong><span>${esc(r.status||"New Contact")} · ${esc(r.circuit||"Diocesan")}</span></div>`).join(""):'<div class="empty">No contacts recorded yet.</div>';el.innerHTML=`<div class="contact-summary"><div><span>FOLLOW-UP QUEUE</span><strong>${items?items.length:0}</strong></div><div><span>RECENT CONTACTS</span><strong>${recent?recent.length:0}</strong></div></div><div class="contact-list">${follow}</div><div class="contact-recent-head">Recent people reached</div>${recentHtml}`}
function miniTable(data,cols){if(!data.length)return '<div class="empty">No records yet. Add the first record from the relevant section.</div>';return `<div class="table-wrap"><table><thead><tr>${cols.map(c=>`<th>${c.replaceAll("_"," ")}</th>`).join("")}</tr></thead><tbody>${data.map(r=>`<tr>${cols.map(c=>`<td>${c==="amount"?money(r[c]):esc(r[c]??"—")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`}
function spotlightCard(data,type){const el=type==="testimony"?$("#recentTestimonies"):$("#recentAppreciations");const badge=type==="testimony"?$("#testimonyBadge"):$("#appreciationBadge");if(!el)return;if(!data||!data.length){el.innerHTML='<div class="feature-story empty">No record yet — this space will light up when the first record is added.</div>';if(badge)badge.textContent="READY";return}const r=data[0];if(badge)badge.textContent=`${data.length} ${data.length===1?'RECORD':'RECORDS'}`;if(type==="testimony"){el.innerHTML=`<div class="feature-story spotlight-new"><div class="story-date">${esc(r.date||"Recent")}</div><div class="story-name">${esc(r.member_name||"Church Member")}</div><div class="story-title">${esc(r.title||"Testimony")}</div><div class="story-text">${esc(r.testimony||"")}</div></div>`}else{el.innerHTML=`<div class="feature-story spotlight-new"><div class="story-date">${esc(r.date||"Recent")}</div><div class="story-name">${esc(r.recipient||"Recipient")}</div><div class="story-title">${esc(r.role_position||"Special Appreciation")}</div><div class="story-text">${esc(r.reason||r.message||"")}</div></div>`}}
function esc(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}


async function loadConference(){
  try{
    const rooms = await api("/api/conference");
    const list = Array.isArray(rooms) ? rooms : [];

    const scheduled = list.filter(x => x.status === "Scheduled").length;
    const live = list.filter(x => x.status === "Live").length;
    const completed = list.filter(x => x.status === "Completed").length;

    $("#conferenceSummary").innerHTML = [
      ["Total Conferences", list.length],
      ["Scheduled", scheduled],
      ["Live", live],
      ["Completed", completed]
    ].map(x => reportCard(x[0], x[1])).join("");

    $("#conferenceRooms").innerHTML = list.length
      ? list.map(x => `
        <div class="comm-alert conference-room-item">
          <div>
            <span class="status-badge">${esc(x.status || "Scheduled")}</span>
            <strong>${esc(x.title || "Conference")}</strong>
            <small>
              ${esc(x.meeting_date || "Date not set")}
              ${x.start_time ? " · " + esc(x.start_time) : ""}
              · ${esc(x.meeting_type || "General Conference")}
            </small>
            <small>
              ${esc(x.circuit || "Diocesan")}
              ${x.organizer ? " · Organizer: " + esc(x.organizer) : ""}
            </small>
          </div>
          <div class="comm-actions">
            ${x.meeting_url
              ? `<button type="button" class="secondary conf-join" data-url="${esc(x.meeting_url)}">Join</button>`
              : ""}
            <button type="button" class="primary conf-open" data-id="${x.id}"
              onclick="openConference(${x.id}); return false;">Open</button>
            ${me && me.role === "Admin"
              ? `<button type="button" class="secondary conf-edit" data-id="${x.id}">Edit</button>
                 <button type="button" class="danger conf-delete" data-id="${x.id}">Delete</button>`
              : ""}
          </div>
        </div>
      `).join("")
      : '<div class="empty">No conferences have been scheduled yet.</div>';

    document.querySelectorAll(".conf-open").forEach(btn => {
      btn.onclick = async event => {
        event.preventDefault();
        event.stopPropagation();
        await openConference(btn.dataset.id);
      };
    });

    document.querySelectorAll(".conf-join").forEach(btn => {
      btn.onclick = event => {
        event.preventDefault();
        if(btn.dataset.url) window.open(new URL(btn.dataset.url, window.location.origin).href, "_blank");
      };
    });

  }catch(e){
    $("#conferenceRooms").innerHTML =
      `<div class="empty">${esc(e.message)}</div>`;
  }
}


async function openConference(id){
  const box = $("#conferenceRoom");
  if(!box) return;

  box.innerHTML = '<div class="empty">Loading conference room…</div>';

  try{
    const data = await api("/api/conference/" + id);
    const room = data.room;
    const participants = Array.isArray(data.participants) ? data.participants : [];
    const messages = Array.isArray(data.messages) ? data.messages : [];

    const joinButton = room.meeting_url
      ? `<button type="button" class="primary conf-room-join"
           data-url="${esc(room.meeting_url)}">Join Meeting</button>`
      : "";

    box.innerHTML = `
      <div class="conversation-header">
        <div>
          <span class="status-badge">${esc(room.status || "Scheduled")}</span>
          <strong>${esc(room.title || "Conference")}</strong>
          <small>
            ${esc(room.meeting_date || "Date not set")}
            ${room.start_time ? " · " + esc(room.start_time) : ""}
            ${room.end_time ? " - " + esc(room.end_time) : ""}
          </small>
          <small>
            ${esc(room.meeting_type || "General Conference")}
            · ${esc(room.circuit || "Diocesan")}
          </small>
        </div>

        <div class="comm-actions">
          ${joinButton}
          <button type="button" class="secondary conf-status"
            data-id="${room.id}" data-status="Live">Start</button>
          <button type="button" class="secondary conf-status"
            data-id="${room.id}" data-status="Completed">End</button>
        </div>
      </div>

      ${room.meeting_url ? `
        <div class="conference-link-box">
          <strong>Conference Join Link</strong>
          <div class="conference-link-row">
            <input id="conferenceJoinLink" readonly value="${esc(window.location.origin + "/conference/" + room.room_code)}">
            <button type="button" class="secondary" id="conferenceCopyLink">Copy Link</button>
            <button type="button" class="secondary" id="conferenceShareLink">Share</button>
          </div>
          <small>Share this link with people invited to this conference.</small>
        </div>
      ` : ""}

      <div class="conference-live-panel">
      <div class="panel-head">
        <strong>Live Conference Call</strong>
        <span id="conferenceCallStatus">Ready to join.</span>
      </div>
      <div class="conference-call-controls">
        <button type="button" class="primary" id="conferenceVideoBtn">🎥 Start Video Call</button>
        <button type="button" class="secondary" id="conferenceAudioBtn">🎙️ Start Audio Call</button>
        <button type="button" class="secondary" id="conferenceMuteBtn">🔇 Mute</button>
        <button type="button" class="secondary" id="conferenceCameraBtn">📷 Camera Off</button>
        <button type="button" class="danger" id="conferenceLeaveBtn">📞 Leave Call</button>
      </div>
      <div class="conference-video-grid">
        <div class="conference-video-card">
          <span>You</span>
          <video id="conferenceLocalVideo" autoplay playsinline muted></video>
        </div>
        <div class="conference-video-card">
          <span>Remote Participant</span>
          <video id="conferenceRemoteVideo" autoplay playsinline></video>
        </div>
      </div>
    </div>

    ${room.agenda ? `
        <div class="conference-agenda">
          <strong>Agenda</strong>
          <div>${esc(room.agenda).replace(/\n/g,"<br>")}</div>
        </div>
      ` : ""}

      <div class="conference-room-grid">

        <div>
          <div class="panel-head">
            <strong>Conference Chat</strong>
          </div>

          <div class="conversation-messages conference-messages">
            ${
              messages.length
              ? messages.map(m => `
                <div class="conversation-message">
                  <strong>${esc(m.sender_name || "Member")}</strong>
                  <small>
                    ${esc(m.sender_role || "")}
                    · ${esc(m.created_at || "")}
                  </small>
                  <div>${esc(m.message || "")}</div>
                </div>
              `).join("")
              : '<div class="empty">No conference messages yet.</div>'
            }
          </div>

          <form id="conferenceMessageForm" class="conversation-reply">
            <textarea name="message" rows="2"
              placeholder="Write a conference message…" required></textarea>
            <button type="submit" class="primary">Send</button>
          </form>
        </div>

        <div>
          <div class="panel-head">
            <strong>Participants (${participants.length})</strong>
          </div>

          <div class="conference-participants">
            ${
              participants.length
              ? participants.map(p => `
                <div class="conference-participant">
                  <strong>${esc(p.participant_name || "Participant")}</strong>
                  <small>
                    ${esc(p.participant_role || "")}
                    ${p.phone ? " · " + esc(p.phone) : ""}
                  </small>
                </div>
              `).join("")
              : '<div class="empty">No participants added yet.</div>'
            }
          </div>

          <form id="conferenceParticipantForm" class="form-grid compact-form">
            <label>Participant Name
              <input name="participant_name" required>
            </label>

            <label>Role
              <input name="participant_role">
            </label>

            <label>Phone
              <input name="phone" type="tel">
            </label>

            <div class="form-actions full">
              <button type="submit" class="primary">Add Participant</button>
            </div>
          </form>
        </div>

      </div>
    `;

    $("#conferenceVideoBtn")?.addEventListener("click", async () => {
      await window.DSConferenceCall.start(room.id, false);
    });

    $("#conferenceAudioBtn")?.addEventListener("click", async () => {
      await window.DSConferenceCall.start(room.id, true);
    });

    $("#conferenceMuteBtn")?.addEventListener("click", () => {
      window.DSConferenceCall.toggleMute();
    });

    $("#conferenceCameraBtn")?.addEventListener("click", () => {
      window.DSConferenceCall.toggleCamera();
    });

    $("#conferenceLeaveBtn")?.addEventListener("click", () => {
      window.DSConferenceCall.stop();
    });

    box.querySelector(".conf-room-join")?.addEventListener("click", e => {
      if(e.currentTarget.dataset.url)
        window.open(e.currentTarget.dataset.url, "_blank");
    });

    box.querySelectorAll(".conf-status").forEach(btn => {
      btn.addEventListener("click", async () => {
        try{
          await api("/api/conference/" + room.id + "/status", {
            method:"POST",
            body:JSON.stringify({status:btn.dataset.status})
          });
          await loadConference();
          await openConference(room.id);
          setStatus("Conference status updated.");
        }catch(e){
          setStatus(e.message);
        }
      });
    });

    $("#conferenceMessageForm")?.addEventListener("submit", async e => {
      e.preventDefault();

      const message = e.target.elements.message.value.trim();
      if(!message) return;

      try{
        await api("/api/conference/" + room.id + "/message", {
          method:"POST",
          body:JSON.stringify({message})
        });

        e.target.reset();
        await openConference(room.id);
        setStatus("Conference message sent.");
      }catch(err){
        setStatus(err.message);
      }
    });

    $("#conferenceParticipantForm")?.addEventListener("submit", async e => {
      e.preventDefault();

      const data = Object.fromEntries(new FormData(e.target).entries());

      try{
        await api("/api/conference/" + room.id + "/participant", {
          method:"POST",
          body:JSON.stringify(data)
        });

        e.target.reset();
        await openConference(room.id);
        setStatus("Participant added.");
      }catch(err){
        setStatus(err.message);
      }
    });

  }catch(e){
    box.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}


document.addEventListener("click", async e => {
  const refresh = e.target.closest("#conferenceRefreshBtn");
  const create = e.target.closest("#conferenceNewBtn");
  const cancel = e.target.closest("#conferenceCancelBtn");
  const open = e.target.closest(".conf-open");
  const join = e.target.closest(".conf-join");
  const edit = e.target.closest(".conf-edit");
  const del = e.target.closest(".conf-delete");

  if(refresh){
    e.preventDefault();
    await loadConference();
    setStatus("Conference refreshed.");
    return;
  }

  if(open){
    e.preventDefault();
    e.stopPropagation();
    await openConference(open.dataset.id);
    return;
  }

  if(join){
    e.preventDefault();
    if(join.dataset.url) window.open(join.dataset.url, "_blank");
    return;
  }

  if(edit){
    e.preventDefault();
    e.stopPropagation();

    try{
      const room = await api("/api/conference/" + edit.dataset.id);
      const data = room.room || room.data || room;

      const wrap = $("#conferenceFormWrap");
      const form = $("#conferenceForm");

      if(!wrap || !form) throw Error("Conference form not found.");

      wrap.hidden = false;

      for(const [key,value] of Object.entries(data)){
        if(form.elements[key]){
          form.elements[key].value = value ?? "";
        }
      }

      form.dataset.editingId = edit.dataset.id;
      form.scrollIntoView({behavior:"smooth",block:"start"});
      setStatus("Editing conference.");
    }catch(err){
      alert(err.message);
    }
    return;
  }

  if(del){
    e.preventDefault();
    e.stopPropagation();

    if(!confirm("Delete this conference? This cannot be undone.")) return;

    try{
      await api("/api/conference/" + del.dataset.id, {
        method:"DELETE"
      });

      await loadConference();
      setStatus("Conference deleted.");
    }catch(err){
      alert(err.message);
    }
    return;
  }

  const statusBtn = e.target.closest(".conf-status");
  const copyLink = e.target.closest("#conferenceCopyLink");
  const shareLink = e.target.closest("#conferenceShareLink");

  if(statusBtn){
    e.preventDefault();
    e.stopPropagation();

    try{
      await api("/api/conference/" + statusBtn.dataset.id + "/status", {
        method:"POST",
        body:JSON.stringify({status: statusBtn.dataset.status})
      });

      await openConference(statusBtn.dataset.id);
      setStatus(
        statusBtn.dataset.status === "Live"
          ? "Conference started."
          : "Conference ended."
      );
    }catch(err){
      alert(err.message);
    }
    return;
  }

  if(copyLink){
    e.preventDefault();
    e.stopPropagation();

    const input = $("#conferenceJoinLink");
    if(!input || !input.value){
      alert("Conference link is not available.");
      return;
    }

    try{
      await navigator.clipboard.writeText(input.value);
      setStatus("Conference link copied.");
    }catch(err){
      input.focus();
      input.select();
      document.execCommand("copy");
      setStatus("Conference link copied.");
    }
    return;
  }

  if(shareLink){
    e.preventDefault();
    e.stopPropagation();

    const input = $("#conferenceJoinLink");
    if(!input || !input.value){
      alert("Conference link is not available.");
      return;
    }

    try{
      if(navigator.share){
        await navigator.share({
          title:"Conference Join Link",
          text:"Join this conference",
          url:input.value
        });
      }else{
        await navigator.clipboard.writeText(input.value);
        setStatus("Sharing is not available here. Link copied instead.");
      }
    }catch(err){
      if(err.name !== "AbortError"){
        alert(err.message);
      }
    }
    return;
  }

  if(create){
    $("#conferenceFormWrap").hidden = false;
    $("#conferenceForm")?.scrollIntoView({behavior:"smooth",block:"start"});
    return;
  }

  if(cancel){
    e.preventDefault();
    $("#conferenceFormWrap").hidden = true;
    $("#conferenceForm")?.reset();
    return;
  }
});


$("#conferenceForm")?.addEventListener("submit", async e => {
  e.preventDefault();

  const data = Object.fromEntries(new FormData(e.target).entries());

  try{
    const editingId = e.target.dataset.editingId;

    if(editingId){
      await api("/api/conference/" + editingId, {
        method:"PUT",
        body:JSON.stringify(data)
      });

      delete e.target.dataset.editingId;
      e.target.reset();
      $("#conferenceFormWrap").hidden = true;

      await loadConference();
      setStatus("Conference updated successfully.");
      return;
    }

    const created = await api("/api/conference", {
      method:"POST",
      body:JSON.stringify(data)
    });

    e.target.reset();

    const generatedLink = created?.room_code
      ? window.location.origin + "/conference/" + created.room_code
      : "";

    $("#conferenceFormWrap").hidden = true;

    await loadConference();

    if(generatedLink){
      const room = await api("/api/conference");
      const createdRoom = (Array.isArray(room) ? room : []).find(
        x => x.room_code === created.room_code
      );

      if(createdRoom){
        await openConference(createdRoom.id);
      }

      setStatus("Conference created. Your automatic meeting link is ready.");
    }else{
      setStatus("Conference created successfully.");
    }
  }catch(err){
    setStatus(err.message);
  }
});

async function loadCustomerCare(){
  try{
    const threads = await api("/api/customer-care");
    const list = Array.isArray(threads) ? threads : [];

    const open = list.filter(x => x.status === "Open").length;
    const closed = list.filter(x => x.status === "Closed").length;
    const urgent = list.filter(x => x.priority === "Urgent").length;
    const high = list.filter(x => x.priority === "High").length;

    $("#customerCareSummary").innerHTML = [
      ["Total Conversations", list.length],
      ["Open", open],
      ["Closed", closed],
      ["Urgent", urgent],
      ["High Priority", high]
    ].map(x => reportCard(x[0], x[1])).join("");

    $("#customerCareThreads").innerHTML = list.length
      ? list.map(x => `
        <div class="comm-alert customer-care-thread" data-id="${x.id}">
          <div>
            <span class="status-badge">${esc(x.status || "Open")}</span>

            <strong>${esc(x.customer_name || "Member")}</strong>

            <small>
              ${esc(x.subject || "Member Care Request")}
              · ${esc(x.category || "General Assistance")}
              · Priority: ${esc(x.priority || "Normal")}
            </small>

            <small>
              ${x.member_id ? "Member ID: " + esc(x.member_id) : ""}
              ${x.assigned_to ? " · Assigned: " + esc(x.assigned_to) : ""}
            </small>
          </div>

          <div class="comm-actions">
            ${x.phone ? `<button class="secondary cc-call"
              data-phone="${esc(x.phone)}">Call</button>` : ""}

            ${x.phone ? `<button class="secondary cc-wa"
              data-phone="${esc(x.phone)}"
              data-name="${esc(x.customer_name || "Member")}">
              WhatsApp
            </button>` : ""}

            <button type="button"
              class="primary cc-open"
              data-id="${x.id}">
              Open
            </button>
          </div>
        </div>
      `).join("")
      : '<div class="empty">No Member Care conversations yet.</div>';

    document.querySelectorAll(".cc-open").forEach(btn => {
      btn.onclick = async event => {
        event.preventDefault();
        event.stopPropagation();
        await openCustomerCareConversation(btn.dataset.id);
      };
    });

    document.querySelectorAll(".cc-call").forEach(btn => {
      btn.onclick = () => {
        window.location.href = "tel:" + btn.dataset.phone;
      };
    });

    document.querySelectorAll(".cc-wa").forEach(btn => {
      btn.onclick = () => {
        const msg =
          "Dear " + btn.dataset.name +
          ", thank you for contacting Methodist Church Nigeria, Delta South Diocese Evangelism Department. How may we assist you?";

        openWhatsApp(btn.dataset.phone, msg);
      };
    });

  }catch(e){
    $("#customerCareThreads").innerHTML =
      `<div class="empty">${esc(e.message)}</div>`;
  }
}



function ensureMemberCarePopup(){
  if(document.getElementById("memberCareChatModal")) return;

  const style=document.createElement("style");
  style.id="memberCarePopupStyle";
  style.textContent=`
    #memberCareChatModal{
      position:fixed;
      inset:0;
      z-index:99999;
      display:flex;
      align-items:center;
      justify-content:center;
      padding:14px;
      background:rgba(0,0,0,.58);
      box-sizing:border-box;
    }

    #memberCareChatModal .mc-chat{
      width:min(720px,100%);
      height:min(760px,94vh);
      background:#fff;
      border-radius:18px;
      box-shadow:0 20px 70px rgba(0,0,0,.35);
      display:flex;
      flex-direction:column;
      overflow:hidden;
    }

    #memberCareChatModal .mc-head{
      padding:15px 17px;
      background:#075c35;
      color:#fff;
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      flex-shrink:0;
    }

    #memberCareChatModal .mc-head-title{
      min-width:0;
    }

    #memberCareChatModal .mc-head-title strong{
      display:block;
      font-size:1.05rem;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }

    #memberCareChatModal .mc-head-title small{
      display:block;
      margin-top:4px;
      opacity:.9;
      line-height:1.35;
    }

    #memberCareChatModal .mc-close{
      border:0;
      background:rgba(255,255,255,.16);
      color:#fff;
      width:38px;
      height:38px;
      border-radius:50%;
      font-size:20px;
      cursor:pointer;
      flex-shrink:0;
    }

    #memberCareChatModal .mc-meta{
      padding:9px 15px;
      background:#f5f7fa;
      border-bottom:1px solid #e3e7ed;
      font-size:.84rem;
      color:#667085;
      flex-shrink:0;
    }

    #memberCareChatModal .mc-messages{
      flex:1;
      overflow-y:auto;
      padding:15px;
      background:#f7f9fc;
      min-height:0;
    }

    #memberCareChatModal .mc-message{
      max-width:84%;
      margin:8px 0;
      padding:11px 13px;
      border-radius:13px;
      background:#fff;
      border:1px solid #e2e6eb;
      box-shadow:0 1px 3px rgba(0,0,0,.04);
    }

    #memberCareChatModal .mc-message.mine{
      margin-left:auto;
      background:#e8f5e9;
      border-color:#c8e6c9;
    }

    #memberCareChatModal .mc-sender{
      font-weight:700;
      font-size:.9rem;
    }

    #memberCareChatModal .mc-time{
      display:block;
      margin-top:2px;
      color:#667085;
      font-size:.72rem;
    }

    #memberCareChatModal .mc-body{
      margin-top:7px;
      white-space:pre-wrap;
      word-break:break-word;
      line-height:1.5;
    }

    #memberCareChatModal .mc-compose{
      padding:10px 12px;
      border-top:1px solid #e2e6eb;
      background:#fff;
      flex-shrink:0;
    }

    #memberCareChatModal .mc-compose textarea{
      width:100%;
      min-height:65px;
      max-height:150px;
      box-sizing:border-box;
      resize:vertical;
      border:1px solid #ccd3dd;
      border-radius:11px;
      padding:10px 12px;
      font:inherit;
      outline:none;
    }

    #memberCareChatModal .mc-actions{
      display:flex;
      gap:8px;
      flex-wrap:wrap;
      margin-top:8px;
    }

    #memberCareChatModal .mc-actions button{
      border:0;
      border-radius:9px;
      padding:9px 13px;
      cursor:pointer;
    }

    #memberCareChatModal .mc-send{
      background:#075c35;
      color:#fff;
    }

    #memberCareChatModal .mc-secondary{
      background:#eef1f5;
      color:#344054;
    }

    @media(max-width:600px){
      #memberCareChatModal{
        padding:0;
      }

      #memberCareChatModal .mc-chat{
        width:100%;
        height:100%;
        max-height:none;
        border-radius:0;
      }

      #memberCareChatModal .mc-message{
        max-width:91%;
      }
    }
  `;
  document.head.appendChild(style);

  const modal=document.createElement("div");
  modal.id="memberCareChatModal";
  modal.style.display="none";
  modal.innerHTML=`
    <div class="mc-chat">
      <div id="mcChatHead" class="mc-head"></div>
      <div id="mcChatMeta" class="mc-meta"></div>
      <div id="mcChatMessages" class="mc-messages"></div>
      <div id="mcChatCompose" class="mc-compose"></div>
    </div>
  `;

  modal.addEventListener("click",e=>{
    if(e.target===modal) closeMemberCarePopup();
  });

  document.body.appendChild(modal);
}

function closeMemberCarePopup(){
  const modal=document.getElementById("memberCareChatModal");
  if(modal) modal.style.display="none";
  document.body.style.overflow="";
}

async function openMemberCarePopup(id){
  ensureMemberCarePopup();

  const modal=document.getElementById("memberCareChatModal");
  const head=document.getElementById("mcChatHead");
  const meta=document.getElementById("mcChatMeta");
  const messagesBox=document.getElementById("mcChatMessages");
  const compose=document.getElementById("mcChatCompose");

  modal.style.display="flex";
  document.body.style.overflow="hidden";

  messagesBox.innerHTML='<div style="text-align:center;padding:30px;color:#667085;">Loading conversation...</div>';

  try{
    const d=await api("/api/customer-care/"+id+"?_="+Date.now());
    const t=d.thread||{};
    const messages=d.messages||[];

    head.innerHTML=`
      <div class="mc-head-title">
        <strong>💬 ${esc(t.customer_name||"Member Care")}</strong>
        <small>${esc(t.subject||"Member Care Conversation")}</small>
      </div>
      <button class="mc-close" type="button" onclick="closeMemberCarePopup()">✕</button>
    `;

    meta.innerHTML=`
      <b>Status:</b> ${esc(t.status||"Open")}
      &nbsp; • &nbsp;
      <b>Category:</b> ${esc(t.category||"General Assistance")}
      &nbsp; • &nbsp;
      <b>Priority:</b> ${esc(t.priority||"Normal")}
      ${t.member_id ? `&nbsp; • &nbsp;<b>Member ID:</b> ${esc(t.member_id)}` : ""}
    `;

    messagesBox.innerHTML=messages.length
      ? messages.map(m=>`
          <div class="mc-message">
            <div class="mc-sender">${esc(m.sender_name||"User")}</div>
            <span class="mc-time">
              ${esc(m.sender_role||"")} ${m.created_at ? "• "+esc(m.created_at) : ""}
            </span>
            <div class="mc-body">${esc(m.message||"")}</div>
          </div>
        `).join("")
      : '<div style="text-align:center;padding:30px;color:#667085;">No messages yet.</div>';

    if(t.status==="Open"){
      compose.innerHTML=`
        <textarea id="mcReplyBox"
          placeholder="Type your response..."
          autocomplete="off"></textarea>

        <div class="mc-actions">
          <button type="button" class="mc-send" id="mcSendBtn">
            📤 Send Reply
          </button>

          ${t.phone ? `
            <button type="button" class="mc-secondary" id="mcCallBtn">
              📞 Call
            </button>
            <button type="button" class="mc-secondary" id="mcWhatsAppBtn">
              WhatsApp
            </button>
          ` : ""}

          <button type="button" class="mc-secondary" id="mcStatusBtn">
            Resolve Request
          </button>
        </div>
      `;

      document.getElementById("mcSendBtn").onclick=async()=>{
        const box=document.getElementById("mcReplyBox");
        const message=box.value.trim();
        if(!message)return;

        const btn=document.getElementById("mcSendBtn");
        btn.disabled=true;
        btn.textContent="Sending...";

        try{
          await api("/api/customer-care/"+id+"/message",{
            method:"POST",
            body:JSON.stringify({message})
          });

          setStatus("Member Care response sent.");
          await openMemberCarePopup(id);
          if(typeof loadCustomerCare==="function") await loadCustomerCare();
          if(typeof loadMemberCareRequests==="function") await loadMemberCareRequests();

        }catch(e){
          alert(e.message);
          btn.disabled=false;
          btn.textContent="📤 Send Reply";
        }
      };

      document.getElementById("mcStatusBtn").onclick=async()=>{
        try{
          await api("/api/customer-care/"+id+"/status",{
            method:"POST",
            body:JSON.stringify({status:"Closed"})
          });

          setStatus("Member Care request resolved.");
          await openMemberCarePopup(id);
          if(typeof loadCustomerCare==="function") await loadCustomerCare();
          if(typeof loadMemberCareRequests==="function") await loadMemberCareRequests();
        }catch(e){
          alert(e.message);
        }
      };

      if(t.phone){
        document.getElementById("mcCallBtn").onclick=()=>{
          window.location.href="tel:"+t.phone;
        };

        document.getElementById("mcWhatsAppBtn").onclick=()=>{
          openWhatsApp(
            t.phone,
            "Dear "+(t.customer_name||"Member")+
            ", thank you for contacting Methodist Church Nigeria, Delta South Diocese Evangelism Department."
          );
        };
      }

    }else{
      compose.innerHTML=`
        <div style="color:#667085;margin-bottom:8px;">
          This conversation is closed.
        </div>
        <button type="button" class="mc-secondary" id="mcReopenBtn">
          Reopen Conversation
        </button>
      `;

      document.getElementById("mcReopenBtn").onclick=async()=>{
        try{
          await api("/api/customer-care/"+id+"/status",{
            method:"POST",
            body:JSON.stringify({status:"Open"})
          });

          setStatus("Member Care conversation reopened.");
          await openMemberCarePopup(id);
          if(typeof loadCustomerCare==="function") await loadCustomerCare();
          if(typeof loadMemberCareRequests==="function") await loadMemberCareRequests();
        }catch(e){
          alert(e.message);
        }
      };
    }

    setTimeout(()=>{
      messagesBox.scrollTop=messagesBox.scrollHeight;
      document.getElementById("mcReplyBox")?.focus();
    },50);

  }catch(e){
    messagesBox.innerHTML=
      `<div style="padding:25px;text-align:center;color:#9b0000;">${esc(e.message)}</div>`;
  }
}

async function openCustomerCareConversation(id){
  await openMemberCarePopup(id);
}

$("#customerCareNewBtn")?.addEventListener("click",()=>{
  $("#customerCareFormWrap").hidden = false;
  $("#customerCareForm")?.reset();

  $("#customerCareFormWrap").scrollIntoView({
    behavior:"smooth",
    block:"start"
  });
});


$("#customerCareCancelBtn")?.addEventListener("click",()=>{
  $("#customerCareFormWrap").hidden = true;
  $("#customerCareForm")?.reset();
});


$("#customerCareRefreshBtn")?.addEventListener(
  "click",
  loadCustomerCare
);


$("#customerCareForm")?.addEventListener("submit",async e=>{
  e.preventDefault();

  const form = e.target;
  const data = Object.fromEntries(
    new FormData(form).entries()
  );

  try{
    const result = await api("/api/customer-care",{
      method:"POST",
      body:JSON.stringify(data)
    });

    form.reset();
    $("#customerCareFormWrap").hidden = true;

    await loadCustomerCare();

    if(result.id){
      await openCustomerCareConversation(result.id);
    }

    setStatus("Member Care conversation created.");

  }catch(err){
    alert(err.message);
  }
});


async function loadCommunications(){try{const d=await api("/api/communications");$("#commScope").textContent=`Today: ${d.today}`;const a=d.alerts||[];$("#commSummary").innerHTML=[["Alerts",a.length],["Unread reminders",d.unread||0],["Follow-ups",a.filter(x=>x.kind==='Follow-up').length],["Missions",a.filter(x=>x.kind==='Mission').length]].map(x=>reportCard(x[0],x[1])).join("");$("#commAlerts").innerHTML=a.length?a.map((x,i)=>`<div class="comm-alert"><div><span class="status-badge">${esc(x.kind)}</span><strong>${esc(x.title)}</strong><small>${esc(x.date)} · ${esc(x.circuit||'Diocesan')} · ${esc(x.detail||'')}</small></div><div class="comm-actions">${x.phone?`<button class="secondary comm-wa" data-phone="${esc(x.phone)}" data-msg="${esc('Dear '+x.title+', this is a reminder from Methodist Church Nigeria, Delta South Diocese Evangelism Department. '+x.detail)}">WhatsApp</button>`:''}</div></div>`).join(''):'<div class="empty">No current communication alerts.</div>';document.querySelectorAll('.comm-wa').forEach(b=>b.onclick=()=>openWhatsApp(b.dataset.phone,b.dataset.msg))}catch(e){$("#commAlerts").innerHTML=`<div class="empty">${esc(e.message)}</div>`}}
function normalizePhone(v){let p=String(v||'').replace(/[^0-9+]/g,'');if(p.startsWith('+'))p=p.slice(1);if(p.startsWith('0'))p='234'+p.slice(1);return p}
function openWhatsApp(phone,msg){const p=normalizePhone(phone);if(!p)return alert('Enter a recipient phone number.');window.open(`https://wa.me/${p}?text=${encodeURIComponent(msg||'')}`,'_blank')}
function openSms(phone,msg){const p=String(phone||'').trim();if(!p)return alert('Enter a recipient phone number.');location.href=`sms:${p}?body=${encodeURIComponent(msg||'')}`}

async function loadSecurityCentre(){try{const [s,b]=await Promise.all([api("/api/security/status"),api("/api/security/backups")]);$("#securitySummary").innerHTML=[["Database","Healthy"],["Users",s.users],["Audit entries",s.audit_entries],["Backups",s.backups]].map(x=>reportCard(x[0],x[1])).join("");$("#securityIntegrity").innerHTML=`<div class="security-status ${s.integrity==='ok'?'ok':'bad'}"><strong>${esc(s.integrity)}</strong><span>${s.integrity==='ok'?'SQLite integrity check passed.':'Database integrity requires attention.'}</span></div><div class="security-mini">Inactive users: <b>${s.inactive_users}</b> · Password changes required: <b>${s.password_change_required}</b></div>`;$("#latestBackup").innerHTML=s.latest_backup?`<div class="simple-row"><div><strong>${esc(s.latest_backup.filename)}</strong><small>${esc(s.latest_backup.created_at)} · ${esc(s.latest_backup.created_by)}</small></div><span class="status-badge">Verified</span></div><small class="hash">SHA-256: ${esc(s.latest_backup.sha256)}</small>`:'<div class="empty">No backup has been created yet.</div>';$("#backupHistory").innerHTML=b.length?`<table><thead><tr><th>Date</th><th>Created by</th><th>Filename</th><th>Size</th><th>Type</th><th>Action</th></tr></thead><tbody>${b.map(r=>`<tr><td>${esc(r.created_at)}</td><td>${esc(r.created_by)}</td><td>${esc(r.filename)}</td><td>${Math.round((r.size_bytes||0)/1024)} KB</td><td>${esc(r.backup_type)}</td><td><button class="secondary" data-restore="${r.id}">Restore</button></td></tr>`).join('')}</tbody></table>`:'<div class="empty">No backup history yet.</div>';document.querySelectorAll('[data-restore]').forEach(btn=>btn.onclick=async()=>{if(!confirm('Restore this backup? The current database will first be backed up automatically.'))return;try{const d=await api(`/api/security/restore/${btn.dataset.restore}`,{method:'POST'});alert(d.message||'Database restored.');location.href='/logout'}catch(e){alert(e.message)}})}catch(e){$("#securitySummary").innerHTML=`<div class="empty">${esc(e.message)}</div>`}}

async function loadTable(){try{if(current!=="audit"&&current!=="users"){await loadCircuits()}records=current==="audit"?await api("/api/audit"):current==="users"?await api("/api/users"):await api("/api/"+current);renderTable();setStatus("Synced with host database")}catch(e){$("#tableWrap").innerHTML=`<div class="empty">${esc(e.message)}</div>`;setStatus("Connection error")}}

async function loadSystemHealth(){try{const [h,i,d]=await Promise.all([api("/api/system/health"),api("/api/system/info"),api("/api/system/deployment-check")]);const items=[['Database integrity',h.checks.database_integrity],['Required tables',h.checks.required_tables],['Required columns',h.checks.required_columns],['Backup directory',h.checks.backup_directory]];$("#healthSummary").innerHTML=items.map(x=>reportCard(x[0],x[1]?'PASS':'ATTENTION',x[1]?'Ready':'Needs attention')).join('');$("#healthDetails").innerHTML=items.map(x=>`<div class="simple-row"><span>${esc(x[0])}</span><b class="status-badge">${x[1]?'PASS':'ATTENTION'}</b></div>`).join('');$("#systemInfo").innerHTML=`<div class="simple-row"><span>Application</span><b>${esc(i.application)}</b></div><div class="simple-row"><span>Version</span><b>${esc(i.version)}</b></div><div class="simple-row"><span>Stage</span><b>${esc(i.stage)}</b></div><div class="simple-row"><span>Database</span><b>${esc(i.database)}</b></div><div class="simple-row"><span>Churches baseline</span><b>${i.local_church_target}</b></div><div class="simple-row"><span>Planting target / year</span><b>${i.church_plant_target_per_year}</b></div><div class="simple-row"><span>Circuits</span><b>${i.circuits.length}</b></div>`;$("#healthCounts").innerHTML=Object.entries(h.counts||{}).map(([k,v])=>`<div class="simple-row"><span>${esc(k.replaceAll('_',' '))}</span><b>${v===null?'—':v}</b></div>`).join('');$("#healthIssues").innerHTML=(h.missing_tables.length||h.schema_issues.length)?`<div class="health-warning"><b>Items requiring attention</b><ul>${h.missing_tables.map(x=>`<li>Missing table: ${esc(x)}</li>`).join('')}${h.schema_issues.map(x=>`<li>Missing column: ${esc(x)}</li>`).join('')}</ul></div>`:'<div class="empty">No integration issues detected.</div>';document.getElementById("deploymentReadiness")?.replaceChildren(...(d.checks||[]).map(x=>{const el=document.createElement("div");el.className="simple-row";el.innerHTML=`<div><strong>${esc(x.name)}</strong><small>${esc(x.detail||"")}</small></div><span class="status-badge">${x.ok?"PASS":"ATTENTION"}</span>`;return el;}));await loadDataQuality();await loadWorkflowCheck();}catch(e){$("#healthSummary").innerHTML=`<div class="empty">${esc(e.message)}</div>`}}
async function loadDataQuality(){try{const d=await api('/api/system/data-quality');$("#qualityResults").innerHTML=d.issues.length?d.issues.map(x=>`<div class="alert-row alert-hot"><div><strong>${esc(x.name)}</strong><span>${x.count} record(s) need attention</span></div><span class="status-badge">${esc(x.severity)}</span></div>`).join(''):'<div class="empty">No data-quality issues detected.</div>';}catch(e){$("#qualityResults").innerHTML=`<div class="health-warning">${esc(e.message)}</div>`}}
async function loadQualityDetails(){try{const d=await api('/api/system/data-quality/details');$("#qualityDetails").innerHTML=d.details.map(g=>g.records.length?`<div class="panel quality-group"><h4>${esc(g.issue)} <span class="status-badge">${g.records.length} shown</span></h4><div class="table-wrap"><table><thead><tr>${Object.keys(g.records[0]).map(k=>`<th>${esc(k.replaceAll('_',' '))}</th>`).join('')}</tr></thead><tbody>${g.records.map(r=>`<tr>${Object.keys(g.records[0]).map(k=>`<td>${esc(r[k]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`:'').join('')||'<div class="empty">No detailed exceptions found.</div>';}catch(e){$("#qualityDetails").innerHTML=`<div class="health-warning">${esc(e.message)}</div>`}}
async function loadWorkflowCheck(){try{const d=await api('/api/system/workflow-check');$("#workflowResults").innerHTML=(d.results||[]).map(x=>`<div class="simple-row"><div><strong>${esc(x.workflow)}</strong><small>${x.detail?esc(x.detail):`${x.records??0} record(s) available`}</small></div><span class="status-badge">${esc(x.status)}</span></div>`).join('');}catch(e){$("#workflowResults").innerHTML=`<div class="health-warning">${esc(e.message)}</div>`}}

document.addEventListener("change",e=>{if(e.target&&e.target.name==="role")setTimeout(applyUserAssignmentRules,0)});
function renderTable(){const q=$("#search").value.toLowerCase();const list=records.filter(r=>Object.values(r).some(v=>String(v??"").toLowerCase().includes(q)));$("#rowCount").textContent=`${list.length} records`;if(!list.length){$("#tableWrap").innerHTML='<div class="empty">No matching records yet.</div>';return}if(current==="audit"){const keys=["happened_at","username","action","table_name","record_id","details"];$("#tableWrap").innerHTML=`<table><thead><tr>${keys.map(k=>`<th>${esc(k.replaceAll("_"," "))}</th>`).join("")}</tr></thead><tbody>${list.map(r=>`<tr>${keys.map(k=>`<td>${esc(r[k]??"—")}</td>`).join("")}</tr>`).join("")}</tbody></table>`;return}let keys;
if(current==="members"){
  const memberOrder=[
    "full_name","church_name","circuit","phone","member_id","address","birthday","gender",
    "fellowship","baptised","baptism_date","confirmed","confirmation_date","marriage","marriage_date",
    "relocated","relocation_destination","relocation_date","transfer","transfer_from","transfer_to",
    "transfer_date","work_address","profession_business_trade","death","death_date",
    "seed_of_faith_payment","tithe_payment","conference_awardee","conference_award","conference_award_year",
    "diocesan_awardee","diocesan_award","diocesan_award_year","notes"
  ];
  keys=memberOrder.filter(k=>list.some(r=>Object.prototype.hasOwnProperty.call(r,k)));
}else{
  keys=[...new Set(list.flatMap(r=>Object.keys(r)))].filter(k=>!( ["id","password"].includes(k) ));
}let showAction=current!=="audit"&&me.role!=="Auditor";let canUpgrade=current==="churches"&&me.role==="Admin";$("#tableWrap").innerHTML=`<table><thead><tr>${keys.map(k=>`<th>${esc(k.replaceAll("_"," "))}</th>`).join("")}${showAction?"<th>Action</th>":""}</tr></thead><tbody>${list.map(r=>`<tr>${keys.map(k=>`<td class="${["amount","budget","annual_target","unit_cost","cost","seed_of_faith_payment","tithe_payment"].includes(k)?"amount":""}">${["amount","budget","annual_target","unit_cost","cost","seed_of_faith_payment","tithe_payment"].includes(k)?money(r[k]):esc(r[k]??"—")}</td>`).join("")}${showAction?`<td class="actions-cell">${canUpgrade&&r.church_status!=="Circuit Headquarters"?`<button class="upgrade" data-upgrade="${r.id}">Upgrade to Circuit</button>`:""}${canUpgrade&&r.church_status==="Circuit Headquarters"?`<span class="status-badge">Circuit HQ</span>`:""}${current==="circuit_reports"&&me.role==="Admin"?`<button class="upgrade" data-review="${r.id}" data-status="Approved">Approve</button><button class="delete" data-review="${r.id}" data-status="Returned">Return</button>`:""}${current==="users"&&me.role==="Admin"?`<button class="secondary" data-edit-user="${r.id}">Edit access</button><button class="secondary" data-toggle-user="${r.id}">${r.active?"Deactivate":"Activate"}</button>`:""}${current==="planting_prospects"&&me.role!=="Local Church Evangelism Officer"&&r.status!=="Converted to Church Plant"&&r.status!=="Closed"?`<button class="upgrade" data-convert-prospect="${r.id}">Convert to Church Plant</button>`:""}${current==="members"?`<button class="secondary" data-edit-member="${r.id}">Edit Member</button><button class="upgrade" data-manage-offices="${r.id}">Manage Offices</button>`:""}<button class="delete" data-del="${r.id}">Delete</button></td>`:""}</tr>`).join("")}</tbody></table>`;document.querySelectorAll("[data-convert-prospect]").forEach(b=>b.onclick=async()=>{
const row=list.find(x=>String(x.id)===String(b.dataset.convertProspect));
if(!row)return;

const proposedYear=row.proposed_planting_year||row.year||new Date().getFullYear();
const budget=prompt("Initial church-plant budget (₦):","0");
if(budget===null)return;

const year=prompt("Church-plant target year:",proposedYear);
if(year===null)return;

const phase=prompt("Initial mission phase:","Surveying");
if(phase===null)return;

if(!confirm(`Convert "${row.location}" into a Church Plant?\\n\\nThis will create a Church Plant record and mark the prospect as Converted to Church Plant.`))return;

try{
await api(`/api/planting_prospects/${row.id}/convert-to-church-plant`,{
method:"POST",
body:JSON.stringify({
year:Number(year)||proposedYear,
budget:Number(budget)||0,
phase:phase||"Surveying",
status:"Planned"
})
});
alert(`Success. "${row.location}" has been converted to a Church Plant.`);
await loadTable();
await loadDashboard();
setStatus("Planting prospect converted to church plant.");
}catch(e){
alert(e.message);
}
});
document.querySelectorAll("[data-del]").forEach(b=>b.onclick=async()=>{if(confirm("Delete this record? This cannot be undone.")){try{if(current==="users")await api(`/api/users/${b.dataset.del}`,{method:"DELETE"});else await api(`/api/${current}/${b.dataset.del}`,{method:"DELETE"});loadTable();loadDashboard()}catch(e){alert(e.message)}}});document.querySelectorAll("[data-edit-member]").forEach(b=>b.onclick=async()=>{
  const row=list.find(x=>String(x.id)===String(b.dataset.editMember));
  if(!row)return;

  current="members";
  await openForm();

  const form=document.querySelector("#recordForm");
  if(!form)return;

  let editMarker=form.elements["__editing_member_id"];
  if(!editMarker){
    editMarker=document.createElement("input");
    editMarker.type="hidden";
    editMarker.name="__editing_member_id";
    form.appendChild(editMarker);
  }
  editMarker.value=String(row.id);

  const circuitEl=form.elements["circuit"];
  const churchEl=form.elements["church_name"];

  if(circuitEl && row.circuit){
    circuitEl.value=row.circuit;
    circuitEl.dispatchEvent(new Event("change"));
    await new Promise(resolve=>setTimeout(resolve,50));
  }

  Object.keys(row).forEach(key=>{
    if(key==="id"||key==="member_id"||key==="created_at"||key==="circuit"||key==="church_name")return;
    const el=form.elements[key];
    if(el && row[key]!==undefined && row[key]!==null)el.value=row[key];
  });

  if(churchEl && row.church_name){
    churchEl.value=row.church_name;
  }

  const memberId=document.querySelector('#fields input[disabled]');
  if(memberId)memberId.value=row.member_id||"Automatic — generated when the member is saved";

  const ca=form.elements["conference_awardee"];
  const da=form.elements["diocesan_awardee"];
  const sync=()=>{
    const cEnabled=ca?.value==="Yes";
    const dEnabled=da?.value==="Yes";
    ["conference_award","conference_award_year"].forEach(k=>{
      const el=form.elements[k];
      if(el){el.disabled=!cEnabled;}
    });
    ["diocesan_award","diocesan_award_year"].forEach(k=>{
      const el=form.elements[k];
      if(el){el.disabled=!dEnabled;}
    });
  };
  sync();

  $("#formTitle").textContent=`Edit Church Member — ${row.member_id||row.full_name}`;
  $("#formWrap").hidden=false;
  $("#formWrap").scrollIntoView({behavior:"smooth",block:"start"});
});document.querySelectorAll("[data-edit-user]").forEach(b=>b.onclick=async()=>{const row=list.find(x=>String(x.id)===String(b.dataset.editUser));if(!row)return;const roles=["Admin","Bishop / Diocesan Executive","Evangelism Minister","Planting Officer","Diocesan Secretary","Circuit Coordinator","Local Church Evangelism Officer","Finance Officer","Auditor"];const role=prompt("Enter role exactly:\n"+roles.join("\n"),row.role);if(role===null)return;if(!roles.includes(role))return alert("Invalid role. Use one of the listed roles.");const circuits=["","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"];const circuit=prompt("Assigned circuit (leave blank for diocesan roles):\n"+circuits.filter(Boolean).join("\n"),row.circuit||"");if(circuit===null)return;if(circuit!==""&&!circuits.includes(circuit))return alert("Invalid circuit.");const church=prompt("Assigned local church (required only for Local Church Evangelism Officer):",row.church_name||"");if(church===null)return;try{await api(`/api/users/${row.id}`,{method:"PUT",body:JSON.stringify({role,circuit,church_name:church})});setStatus("User access updated.");await loadTable()}catch(e){alert(e.message)}});
document.querySelectorAll("[data-toggle-user]").forEach(b=>b.onclick=async()=>{try{const d=await api(`/api/security/users/${b.dataset.toggleUser}/toggle`,{method:"POST"});setStatus(d.active?"User activated.":"User deactivated.");await loadTable()}catch(e){alert(e.message)}});document.querySelectorAll("[data-upgrade]").forEach(b=>b.onclick=async()=>{const row=list.find(x=>String(x.id)===String(b.dataset.upgrade));if(!row)return;let proposed=(row.church_name||"").trim()+" Circuit";let name=prompt("Enter the new circuit name for this church.\nExample: Enerhen Circuit",proposed);if(name===null)return;name=name.trim();if(!name)return alert("A circuit name is required.");if(!confirm(`Upgrade "${row.church_name}" to circuit headquarters and create "${name}"?`))return;try{const d=await api(`/api/churches/${row.id}/upgrade-to-circuit`,{method:"POST",body:JSON.stringify({circuit_name:name})});alert(`Success. ${row.church_name} is now the headquarters of ${d.circuit_name}.`);await loadTable();await loadDashboard()}catch(e){alert(e.message)}});document.querySelectorAll("[data-review]").forEach(b=>b.onclick=async()=>{const action=b.dataset.status;let note="";if(action==="Returned"){note=prompt("Reason for returning this report (optional):","");if(note===null)return}if(!confirm(action==="Approved"?"Approve this circuit report?":"Return this circuit report for correction?"))return;try{await api(`/api/circuit_reports/${b.dataset.review}/review`,{method:"POST",body:JSON.stringify({status:action,review_note:note})});await loadTable();setStatus(`Report ${action.toLowerCase()}.`)}catch(e){alert(e.message)}})}
async function loadCircuits(){try{const data=await api("/api/circuits");const names=data.filter(x=>x.status!=="Inactive").map(x=>x.name);circuitOptions=["Diocesan",...names.filter(n=>n!=="Diocesan")];}catch(e){/* keep baseline options if circuits endpoint is unavailable */}}
 

async function loadMemberRegistrations(){
  const panel = $("#memberRegistrationsPanel");
  const wrap = $("#memberRegistrationsWrap");

  if(!panel || !wrap) return;

  if(current !== "members" || !["Admin","Evangelism Minister"].includes(me?.role)){
    panel.hidden = true;
    return;
  }

  panel.hidden = false;

  try{
    const registrations = await api("/api/member-registrations");

    const pending = registrations.filter(r =>
      ["Pending","Under Review"].includes(r.status)
    );

    if(!pending.length){
      wrap.innerHTML = '<div class="empty">No pending member registrations.</div>';
      return;
    }

    wrap.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Applicant</th>
            <th>Username</th>
            <th>Phone</th>
            <th>Circuit</th>
            <th>Church</th>
            <th>Photo</th>
            <th>Status</th>
            <th>Date</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${pending.map(r => `
            <tr>
              <td>
                <strong>${esc(r.full_name)}</strong>
                <small>${esc(r.gender || "")}</small>
              </td>
              <td>${esc(r.username || "—")}</td>
              <td>${esc(r.phone || "—")}</td>
              <td>${esc(r.circuit || "—")}</td>
              <td>${esc(r.church_name || "—")}</td>
              <td>
                ${r.passport_photo
                  ? `<a href="/api/member-registration-photo/${encodeURIComponent(String(r.passport_photo).split("/").pop())}" target="_blank" rel="noopener">View</a>`
                  : "—"}
              </td>
              <td><span class="status-badge">${esc(r.status)}</span></td>
              <td>${esc(r.created_at || "—")}</td>
              <td class="actions-cell">
                <button class="secondary" data-review-member="${r.id}" data-member-status="Under Review">Review</button>
                <button class="upgrade" data-review-member="${r.id}" data-member-status="Approved">Approve</button>
                <button class="delete" data-review-member="${r.id}" data-member-status="Rejected">Reject</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

    document.querySelectorAll("[data-review-member]").forEach(btn => {
      btn.onclick = async () => {
        const id = btn.dataset.reviewMember;
        const status = btn.dataset.memberStatus;
        const row = registrations.find(x => String(x.id) === String(id));

        if(!row) return;

        let role = "";
        let circuit = row.circuit || "";
        let church = row.church_name || "";
        let note = "";

        if(status === "Approved"){
          const roles = [
            "Member",
            "Bishop / Diocesan Executive",
            "Evangelism Minister",
            "Planting Officer",
            "Diocesan Secretary",
            "Circuit Coordinator",
            "Local Church Evangelism Officer",
            "Finance Officer",
            "Auditor"
          ];

          role = prompt(
            "Select the system role for this applicant:\n\n" +
            roles.join("\n"),
            "Member"
          );

          if(role === null) return;

          if(!roles.includes(role)){
            alert("Invalid role. Please enter one of the listed roles.");
            return;
          }

          const diocesanRoles = [
            "Bishop / Diocesan Executive",
            "Evangelism Minister",
            "Planting Officer",
            "Diocesan Secretary",
            "Finance Officer",
            "Auditor"
          ];

          if(diocesanRoles.includes(role)){
            circuit = "";
            church = "";
          }else if(role === "Circuit Coordinator"){
            circuit = prompt(
              "Assigned circuit:",
              row.circuit || ""
            );

            if(circuit === null) return;

            church = "";
          }else if(
            role === "Member" ||
            role === "Local Church Evangelism Officer"
          ){
            circuit = prompt(
              role === "Member"
                ? "Member's assigned circuit:"
                : "Assigned circuit:",
              row.circuit || ""
            );

            if(circuit === null) return;

            church = prompt(
              role === "Member"
                ? "Member's assigned local church:"
                : "Assigned local church:",
              row.church_name || ""
            );

            if(church === null) return;
          }else{
            circuit = row.circuit || "";
            church = row.church_name || "";
          }

          if(!confirm(
            `Approve ${row.full_name} and create the official member record plus login account as ${role}?`
          )){
            return;
          }
        }else if(status === "Rejected"){
          note = prompt(
            `Reason for rejecting ${row.full_name}'s registration (optional):`,
            ""
          );

          if(note === null) return;

          if(!confirm(`Reject ${row.full_name}'s registration?`)){
            return;
          }
        }else{
          note = prompt(
            `Review note for ${row.full_name}:`,
            ""
          );

          if(note === null) return;
        }

        try{
          const d = await api(
            `/api/member-registrations/${id}/review`,
            {
              method:"POST",
              body:JSON.stringify({
                status,
                review_note:note,
                role,
                circuit,
                church_name:church
              })
            }
          );

          alert(d.message || "Registration reviewed successfully.");

          await loadMemberRegistrations();
          await loadTable();

          if(current === "members"){
            await loadMembershipStatistics();
          }

          setStatus(
            status === "Approved"
              ? "Member registration approved and login account created."
              : `Member registration marked ${status}.`
          );

        }catch(e){
          alert(e.message);
        }
      };
    });

  }catch(e){
    wrap.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

async function loadAccountRequests(){
  const panel = $("#accountRequestsPanel");
  const wrap = $("#accountRequestsWrap");

  if (!panel || !wrap) return;

  if (current !== "users" || me?.role !== "Admin") {
    panel.hidden = true;
    return;
  }

  panel.hidden = false;

  try {
    const requests = await api("/api/account-requests");

    if (!requests.length) {
      wrap.innerHTML = '<div class="empty">No account registration requests.</div>';
      return;
    }

    wrap.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Applicant</th>
            <th>Username</th>
            <th>Phone</th>
            <th>Email</th>
            <th>Circuit</th>
            <th>Church</th>
            <th>Status</th>
            <th>Date</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${requests.map(r => `
            <tr>
              <td><strong>${esc(r.full_name)}</strong></td>
              <td>${esc(r.username)}</td>
              <td>${esc(r.phone)}</td>
              <td>${esc(r.email || "—")}</td>
              <td>${esc(r.circuit)}</td>
              <td>${esc(r.church_name)}</td>
              <td><span class="status-badge">${esc(r.status)}</span></td>
              <td>${esc(r.created_at)}</td>
              <td class="actions-cell">
                ${
                  r.status === "Pending"
                  ? `
                    <button class="upgrade" data-approve-account="${r.id}">
                      Approve
                    </button>
                    <button class="delete" data-reject-account="${r.id}">
                      Reject
                    </button>
                  `
                  : `
                    <span class="status-badge">
                      ${esc(r.status)}
                    </span>
                  `
                }
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

    document.querySelectorAll("[data-approve-account]").forEach(btn => {
      btn.onclick = async () => {
        const id = btn.dataset.approveAccount;
        const row = requests.find(x => String(x.id) === String(id));

        if (!row) return;

        const roles = [
          "Bishop / Diocesan Executive",
          "Evangelism Minister",
          "Planting Officer",
          "Diocesan Secretary",
          "Circuit Coordinator",
          "Local Church Evangelism Officer",
          "Finance Officer",
          "Auditor"
        ];

        const role = prompt(
          "Select the role for this account.\n\n" +
          roles.join("\n"),
          "Auditor"
        );

        if (role === null) return;

        if (!roles.includes(role)) {
          alert("Invalid role. Please enter one of the listed roles.");
          return;
        }

        let circuit = "";
        let church = "";

        const diocesanRoles = [
          "Admin",
          "Bishop / Diocesan Executive",
          "Evangelism Minister",
          "Planting Officer",
          "Diocesan Secretary",
          "Finance Officer",
          "Auditor"
        ];

        if (diocesanRoles.includes(role)) {
          circuit = "";
          church = "";
        } else if (role === "Circuit Coordinator") {
          circuit = prompt(
            "Assigned circuit:",
            row.circuit || ""
          );

          if (circuit === null) return;

          church = "";
        } else if (role === "Local Church Evangelism Officer") {
          circuit = prompt(
            "Assigned circuit:",
            row.circuit || ""
          );

          if (circuit === null) return;

          church = prompt(
            "Assigned local church:",
            row.church_name || ""
          );

          if (church === null) return;
        } else {
          circuit = row.circuit || "";
          church = row.church_name || "";
        }

        if (!confirm(
          `Approve ${row.full_name} (${row.username}) as ${role}?`
        )) {
          return;
        }

        try {
          const d = await api(
            `/api/account-requests/${id}/approve`,
            {
              method: "POST",
              body: JSON.stringify({
                role,
                circuit,
                church_name: church
              })
            }
          );

          alert(d.message || "Account approved successfully.");

          await loadAccountRequests();
          await loadTable();

          setStatus("Account registration approved.");
        } catch (e) {
          alert(e.message);
        }
      };
    });

    document.querySelectorAll("[data-reject-account]").forEach(btn => {
      btn.onclick = async () => {
        const id = btn.dataset.rejectAccount;
        const row = requests.find(x => String(x.id) === String(id));

        if (!row) return;

        const note = prompt(
          `Reason for rejecting ${row.full_name}'s registration:`,
          ""
        );

        if (note === null) return;

        if (!confirm(
          `Reject the registration request for ${row.full_name}?`
        )) {
          return;
        }

        try {
          const d = await api(
            `/api/account-requests/${id}/reject`,
            {
              method: "POST",
              body: JSON.stringify({
                review_note: note
              })
            }
          );

          alert(d.message || "Registration request rejected.");

          await loadAccountRequests();

          setStatus("Account registration rejected.");
        } catch (e) {
          alert(e.message);
        }
      };
    });

  } catch (e) {
    wrap.innerHTML = `
      <div class="empty">
        ${esc(e.message)}
      </div>
    `;
  }
}


function applyUserAssignmentRules(){
  if(current!=="users") return;

  const roleEl = document.querySelector('[name="role"]');
  const circuitEl = document.querySelector('[name="circuit"]');
  const churchEl = document.querySelector('[name="church_name"]');

  if(!roleEl || !circuitEl || !churchEl) return;

  const diocesanRoles=[
    "Admin",
    "Bishop / Diocesan Executive",
    "Evangelism Minister",
    "Planting Officer",
    "Diocesan Secretary",
    "Finance Officer",
    "Auditor"
  ];

  const diocesan=diocesanRoles.includes(roleEl.value);
  const circuitRole=roleEl.value==="Circuit Coordinator";
  const localRole=roleEl.value==="Local Church Evangelism Officer";

  if(diocesan){
    circuitEl.value="";
    churchEl.value="";
    circuitEl.disabled=true;
    churchEl.disabled=true;
    circuitEl.title="Not applicable to diocesan roles";
    churchEl.title="Not applicable to diocesan roles";
  }else if(circuitRole){
    circuitEl.disabled=false;
    churchEl.value="";
    churchEl.disabled=true;
    circuitEl.title="Select the assigned circuit";
    churchEl.title="Not applicable to Circuit Coordinator";
  }else if(localRole){
    circuitEl.disabled=false;
    churchEl.disabled=false;
    circuitEl.title="Select the assigned circuit";
    churchEl.title="Select the assigned local church";
  }else{
    circuitEl.disabled=false;
    churchEl.disabled=false;
    circuitEl.title="";
    churchEl.title="";
  }
}


async function openForm(){if(current==="audit"||me.role==="Auditor")return;const fields=schemas[current];if(!fields){return}if(fields.some(x=>x[0]==="circuit")){await loadCircuits()}
let churchOptions=[];
if(["members","testimonies","appreciations","mission_teams","mission_contacts","expenses"].includes(current)){try{churchOptions=await api("/api/membership/churches");}catch(e){alert(e.message);return;}}
$("#fields").innerHTML=(current==="members"?'<div class="field field-wide"><label>Member ID</label><input value="Automatic — generated when the member is saved" disabled></div>':'')+fields.map(([key,label,type,opts])=>{let control;if(type==="select"){let choices=key==="circuit"?circuitOptions:opts;if(current==="users"&&key==="circuit")choices=["","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"];if(["members","testimonies","appreciations","mission_teams","mission_contacts","expenses"].includes(current)&&key==="church_name")choices=churchOptions.map(x=>x.church_name);control=`<select name="${key}">${choices.map(o=>`<option value="${esc(o)}">${esc(o||"Diocesan / Not assigned to a circuit")}</option>`).join("")}</select>`}else if(type==="textarea")control=`<textarea name="${key}"></textarea>`;else control=`<input name="${key}" type="${type}" ${type==="number"?'step="any"':''} ${key==="member_id"?'placeholder="e.g. DSD-00001"':''}>`;return `<div class="field"><label>${label}</label>${control}</div>`}).join("");
if(["members","testimonies","appreciations","mission_teams","mission_contacts","expenses"].includes(current)){
 const circuitEl=document.querySelector('#fields select[name="circuit"]'), churchEl=document.querySelector('#fields select[name="church_name"]');
 const refreshChurches=()=>{const selected=circuitEl.value;const choices=selected==="Diocesan"?[{church_name:"Diocesan Office",circuit:"Diocesan"}]:churchOptions.filter(x=>x.circuit===selected);churchEl.innerHTML=choices.map(x=>`<option>${esc(x.church_name)}</option>`).join("");};
 circuitEl.addEventListener("change",refreshChurches);refreshChurches();
}if(current==="members"){
  const ca=document.querySelector('#fields select[name="conference_awardee"]');
  const cn=document.querySelector('#fields input[name="conference_award"]');
  const cy=document.querySelector('#fields input[name="conference_award_year"]');
  const da=document.querySelector('#fields select[name="diocesan_awardee"]');
  const dn=document.querySelector('#fields input[name="diocesan_award"]');
  const dy=document.querySelector('#fields input[name="diocesan_award_year"]');

  const syncAwardFields=()=>{
    const cEnabled=ca?.value==="Yes";
    const dEnabled=da?.value==="Yes";
    [cn,cy].forEach(x=>{if(x){x.disabled=!cEnabled;if(!cEnabled)x.value="";}});
    [dn,dy].forEach(x=>{if(x){x.disabled=!dEnabled;if(!dEnabled)x.value="";}});
  };

  ca?.addEventListener("change",syncAwardFields);
  da?.addEventListener("change",syncAwardFields);
  syncAwardFields();
}
if(current==="users")setTimeout(applyUserAssignmentRules,0);$("#formTitle").textContent=current==="members"?"Add Church Member — Member ID is automatic":"Add "+labels[current].toLowerCase().replace(/s$/ ,"");$("#formWrap").hidden=false;$("#formWrap").scrollIntoView({behavior:"smooth",block:"start"})}
$("#commandRefreshBtn")?.addEventListener("click",loadCommandCentre);$("#healthRefreshBtn")?.addEventListener("click",async()=>{setStatus("Checking system health…");const b=$("#healthRefreshBtn");if(b){b.disabled=true;b.textContent="Checking…"}try{await loadSystemHealth();setStatus("System health check completed.")}finally{if(b){b.disabled=false;b.textContent="Run Check Again"}}});$("#qualityCheckBtn")?.addEventListener("click",loadDataQuality);$("#qualityDetailsBtn")?.addEventListener("click",loadQualityDetails);$("#qualityCleanupBtn")?.addEventListener("click",async()=>{if(me.role!=="Admin")return alert("Only an Administrator can run safe cleanup.");if(!confirm("Run safe cleanup? It only trims whitespace and fills a missing member circuit when the church-to-circuit match is unambiguous. Ambiguous records will not be changed."))return;try{const d=await api("/api/system/data-quality/safe-cleanup",{method:"POST"});alert(`${d.message} ${d.total_updated} field(s)/record updates made.`);await loadDataQuality();await loadQualityDetails();}catch(e){alert(e.message)}});$("#workflowCheckBtn")?.addEventListener("click",loadWorkflowCheck);$("#securityRefreshBtn")?.addEventListener("click",loadSecurityCentre);$("#securityBackupBtn")?.addEventListener("click",async()=>{try{const d=await api("/api/security/backup",{method:"POST"});alert(`Backup created: ${d.filename}`);loadSecurityCentre()}catch(e){alert(e.message)}});$("#runReportBtn")?.addEventListener("click",loadReports);$("#reportPrintBtn")?.addEventListener("click",()=>window.print());$("#addBtn").onclick=openForm;$("#cancelBtn").onclick=()=>$("#formWrap").hidden=true;
$("#recordForm").onsubmit=async e=>{e.preventDefault();const data={};new FormData(e.target).forEach((v,k)=>{const f=schemas[current].find(x=>x[0]===k);data[k]=f&&["number"].includes(f[2])?(v===""?0:Number(v)):v});if(current==="users"){const diocesanRoles=["Admin","Bishop / Diocesan Executive","Evangelism Minister","Planting Officer","Diocesan Secretary","Finance Officer","Auditor"];if(diocesanRoles.includes(data.role)){data.circuit="";data.church_name="";}else if(data.role==="Circuit Coordinator"){data.church_name="";}}try{
  const form=e.target;const editingMemberId=form.elements["__editing_member_id"]?.value||"";
  if(current==="members" && editingMemberId){
    delete data.member_id;
    delete data.created_at;
    await api(`/api/members/${editingMemberId}`,{method:"PUT",body:JSON.stringify(data)});
    form.elements["__editing_member_id"].remove();
    e.target.reset();
    $("#formWrap").hidden=true;
    await loadTable();
    await loadMembershipStatistics();
    setStatus("Member updated successfully.");
  }else{
    const endpoint=current==="users"?"/api/users":"/api/"+current;
    await api(endpoint,{method:"POST",body:JSON.stringify(data)});
    e.target.reset();
    $("#formWrap").hidden=true;
    await loadTable();
    if(current==="members")await loadMembershipStatistics();
    setStatus(current==="users"?"User created. They must change the temporary password on first login.":"Record saved");
  }
}catch(err){alert(err.message)}};
$("#commRefreshBtn")?.addEventListener("click",loadCommunications);$("#commGenerateBtn")?.addEventListener("click",async()=>{try{const d=await api('/api/notifications/generate',{method:'POST'});await loadCommunications();setStatus(`${d.created} reminder(s) generated.`)}catch(e){alert(e.message)}});$("#commNotifyBtn")?.addEventListener("click",async()=>{if(!('Notification' in window))return alert('Browser notifications are not supported on this device/browser.');const p=await Notification.requestPermission();alert(p==='granted'?'Browser notifications enabled.':'Notification permission was not granted.')});$("#waBtn")?.addEventListener("click",()=>openWhatsApp($("#msgPhone").value,$("#msgText").value));$("#smsBtn")?.addEventListener("click",()=>openSms($("#msgPhone").value,$("#msgText").value));$("#copyMsgBtn")?.addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("#msgText").value);setStatus('Message copied.')}catch(e){alert('Copy failed.')}});

function closeMemberOfficeManager(){
  const el = document.getElementById("memberOfficeModal");
  if(el) el.remove();
}

function memberOfficeModalHtml(member, appointments, offices, levels, statuses){
  const active = appointments.filter(x => x.status === "Active");
  const history = appointments.filter(x => x.status !== "Active");

  const officeOptions = offices.map(x =>
    `<option value="${esc(x)}">${esc(x)}</option>`
  ).join("");

  const levelOptions = levels.map(x =>
    `<option value="${esc(x)}">${esc(x)}</option>`
  ).join("");

  const statusOptions = statuses.map(x =>
    `<option value="${esc(x)}">${esc(x)}</option>`
  ).join("");

  const appointmentRows = appointments.length
    ? appointments.map(a => `
      <div class="simple-row" style="display:block;margin-bottom:10px;padding:14px;border:1px solid #dce8df;border-radius:12px;background:#fff">
        <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">
          <div>
            <strong>${esc(a.office)}</strong>
            <small style="display:block;margin-top:4px">
              ${esc(a.level)}
              ${a.circuit ? " · " + esc(a.circuit) : ""}
              ${a.church_name ? " · " + esc(a.church_name) : ""}
            </small>
          </div>
          <span class="status-badge">${esc(a.status)}</span>
        </div>

        <div style="margin-top:8px;font-size:.9rem">
          <strong>Start:</strong> ${esc(a.start_date || "—")}
          &nbsp; · &nbsp;
          <strong>End:</strong> ${esc(a.end_date || "—")}
        </div>

        ${a.notes ? `<div style="margin-top:7px"><strong>Notes:</strong> ${esc(a.notes)}</div>` : ""}

        <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
          <button class="secondary" data-office-edit="${a.id}">Edit</button>
          ${a.status === "Active"
            ? `<button class="delete" data-office-terminate="${a.id}">Terminate</button>`
            : ""}
        </div>
      </div>
    `).join("")
    : `<div class="empty">No church office appointments recorded for this member yet.</div>`;

  return `
    <div id="memberOfficeModal"
         style="position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);padding:18px;overflow:auto">

      <div style="max-width:850px;margin:25px auto;background:#fff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,.25);overflow:hidden">

        <div style="background:#075d35;color:#fff;padding:20px">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
            <div>
              <div style="font-size:.8rem;opacity:.85;text-transform:uppercase;letter-spacing:.08em">
                Church Office Management
              </div>
              <h2 style="margin:5px 0">${esc(member.full_name)}</h2>
              <div>${esc(member.member_id || "")} · ${esc(member.circuit || "")} · ${esc(member.church_name || "")}</div>
            </div>
            <button id="closeMemberOfficeModal"
                    style="background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.35);border-radius:10px;padding:8px 12px;font-size:20px">
              ×
            </button>
          </div>
        </div>

        <div style="padding:20px">

          <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:20px">
            <div style="padding:16px;border-radius:14px;background:#f0faf4">
              <small>Active Offices</small>
              <strong style="display:block;font-size:1.5rem">${active.length}</strong>
            </div>
            <div style="padding:16px;border-radius:14px;background:#f7f7f7">
              <small>Appointment History</small>
              <strong style="display:block;font-size:1.5rem">${appointments.length}</strong>
            </div>
          </div>

          <div style="border:1px solid #dce8df;border-radius:16px;padding:18px;margin-bottom:20px">
            <h3 style="margin-top:0">Add Church Office / Appointment</h3>

            <form id="memberOfficeForm">

              <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">

                <div class="field">
                  <label>Church Office</label>
                  <select name="office" required>
                    <option value="">Select office</option>
                    ${officeOptions}
                  </select>
                </div>

                <div class="field">
                  <label>Appointment Level</label>
                  <select name="level" required>
                    ${levelOptions}
                  </select>
                </div>

                <div class="field">
                  <label>Circuit</label>
                  <select name="circuit">
                    <option value="">Select circuit</option>
                    <option>Effurun Circuit</option>
                    <option>Warri Circuit</option>
                    <option>Sapele Circuit</option>
                    <option>Steel Town Circuit</option>
                  </select>
                </div>

                <div class="field">
                  <label>Local Church</label>
                  <select name="church_name">
                    <option value="">Select local church</option>
                  </select>
                </div>

                <div class="field">
                  <label>Start Date</label>
                  <input name="start_date" type="date" required>
                </div>

                <div class="field">
                  <label>Status</label>
                  <select name="status">
                    ${statusOptions}
                  </select>
                </div>

                <div class="field field-wide" style="grid-column:1/-1">
                  <label>End Date</label>
                  <input name="end_date" type="date">
                </div>

                <div class="field field-wide" style="grid-column:1/-1">
                  <label>Notes / Appointment Information</label>
                  <textarea name="notes" rows="3" placeholder="Appointment details, reason, reference, etc."></textarea>
                </div>

              </div>

              <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:12px">
                <button type="submit" class="upgrade">Add Appointment</button>
              </div>

            </form>
          </div>

          <div>
            <h3>Appointment History</h3>
            ${appointmentRows}
          </div>

        </div>
      </div>
    </div>
  `;
}

async function openMemberOfficeManager(memberId){
  if(me?.role !== "Admin"){
    alert("Only an Administrator can manage church offices.");
    return;
  }

  try{
    const d = await api(`/api/members/${memberId}/appointments`);

    closeMemberOfficeManager();

    document.body.insertAdjacentHTML(
      "beforeend",
      memberOfficeModalHtml(
        d.member,
        d.appointments || [],
        d.offices || [],
        d.levels || [],
        d.statuses || []
      )
    );

    const modal = document.getElementById("memberOfficeModal");
    const form = document.getElementById("memberOfficeForm");
    const circuit = form?.elements["circuit"];
    const church = form?.elements["church_name"];
    const level = form?.elements["level"];

    async function loadOfficeChurches(){
      if(!circuit || !church) return;

      if(level?.value === "Diocesan"){
        circuit.value = "";
        church.innerHTML = '<option value="">Diocesan Office</option>';
        circuit.disabled = true;
        church.disabled = true;
        return;
      }

      circuit.disabled = false;

      if(level?.value === "Circuit"){
        church.innerHTML = '<option value="">Circuit appointment</option>';
        church.disabled = true;
        return;
      }

      church.disabled = false;

      try{
        const list = await api("/api/membership/churches");
        const selected = circuit.value;

        const filtered = (list || []).filter(
          x => x.circuit === selected
        );

        church.innerHTML =
          '<option value="">Select local church</option>' +
          filtered.map(x =>
            `<option value="${esc(x.church_name)}">${esc(x.church_name)}</option>`
          ).join("");
      }catch(e){
        church.innerHTML = '<option value="">Unable to load churches</option>';
      }
    }

    level?.addEventListener("change", loadOfficeChurches);
    circuit?.addEventListener("change", loadOfficeChurches);

    await loadOfficeChurches();

    document.getElementById("closeMemberOfficeModal")?.addEventListener(
      "click",
      closeMemberOfficeManager
    );

    modal?.addEventListener("click", e => {
      if(e.target === modal) closeMemberOfficeManager();
    });

    form?.addEventListener("submit", async e => {
      e.preventDefault();

      const data = {};
      new FormData(form).forEach((v,k) => {
        data[k] = v;
      });

      try{
        await api(`/api/members/${memberId}/appointments`, {
          method:"POST",
          body:JSON.stringify(data)
        });

        alert("Church office appointment added successfully.");

        await openMemberOfficeManager(memberId);

      }catch(err){
        alert(err.message);
      }
    });

    document.querySelectorAll("[data-office-edit]").forEach(btn => {
      btn.onclick = async () => {
        const appointment = (d.appointments || []).find(
          x => String(x.id) === String(btn.dataset.officeEdit)
        );

        if(!appointment) return;

        const office = prompt(
          "Church office:",
          appointment.office
        );
        if(office === null) return;

        const levelValue = prompt(
          "Appointment level (Diocesan, Circuit, Local Church):",
          appointment.level
        );
        if(levelValue === null) return;

        const start = prompt(
          "Start date (YYYY-MM-DD):",
          appointment.start_date || ""
        );
        if(start === null) return;

        const end = prompt(
          "End date (leave blank if active):",
          appointment.end_date || ""
        );
        if(end === null) return;

        const status = prompt(
          "Status (Active or Terminated):",
          appointment.status
        );
        if(status === null) return;

        const notes = prompt(
          "Notes:",
          appointment.notes || ""
        );
        if(notes === null) return;

        try{
          await api(`/api/member-appointments/${appointment.id}`, {
            method:"PUT",
            body:JSON.stringify({
              office:office,
              level:levelValue,
              circuit:appointment.circuit || "",
              church_name:appointment.church_name || "",
              start_date:start,
              end_date:end,
              status:status,
              notes:notes
            })
          });

          alert("Appointment updated successfully.");
          await openMemberOfficeManager(memberId);

        }catch(err){
          alert(err.message);
        }
      };
    });

    document.querySelectorAll("[data-office-terminate]").forEach(btn => {
      btn.onclick = async () => {
        const appointment = (d.appointments || []).find(
          x => String(x.id) === String(btn.dataset.officeTerminate)
        );

        if(!appointment) return;

        if(!confirm(
          `Terminate "${appointment.office}" for ${d.member.full_name}?\n\n` +
          "The person's church membership will remain active."
        )) return;

        const endDate = prompt(
          "Termination date (YYYY-MM-DD):",
          new Date().toISOString().slice(0,10)
        );

        if(endDate === null) return;

        const notes = prompt(
          "Reason / termination note:",
          "Appointment terminated."
        );

        if(notes === null) return;

        try{
          await api(`/api/member-appointments/${appointment.id}/terminate`, {
            method:"POST",
            body:JSON.stringify({
              end_date:endDate,
              notes:notes
            })
          });

          alert(
            "Appointment terminated successfully.\n\n" +
            "Membership remains active."
          );

          await openMemberOfficeManager(memberId);

        }catch(err){
          alert(err.message);
        }
      };
    });

  }catch(err){
    alert(err.message);
  }
}

document.addEventListener("click", e => {
  const button = e.target.closest("[data-manage-offices]");
  if(!button) return;

  openMemberOfficeManager(button.dataset.manageOffices);
});

async function start(){
  try{
    await loadMe();
    await loadDashboard();
    await loadReportingSummary();
    await loadConnection();

    const conferenceCode = new URLSearchParams(window.location.search).get("conference");

    if(conferenceCode){
      const rooms = await api("/api/conference");
      const room = (Array.isArray(rooms) ? rooms : []).find(
        x => x.room_code === conferenceCode
      );

      if(room){
        nav("conference");
        await openConference(room.id);
      }else{
        setStatus("Conference room not found.");
      }
    }else if(current==="customer_care"){
      await loadCustomerCare();
    }
  }catch(e){
    setStatus(e.message);
  }
}
start();
let installPrompt;window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();installPrompt=e;$("#installBtn").hidden=false});$("#installBtn").onclick=async()=>{if(installPrompt){installPrompt.prompt();await installPrompt.userChoice;installPrompt=null}else alert("Open this app in Chrome, then use menu ⋮ → Add to Home screen.")};

document.addEventListener("click", async e => {
  const refresh = e.target.closest("#customerCareRefreshBtn");
  const create = e.target.closest("#customerCareNewBtn");
  const cancel = e.target.closest("#customerCareCancelBtn");

  if(refresh){
    e.preventDefault();
    await loadCustomerCare();
    setStatus("Member Care refreshed.");
    return;
  }

  if(create){
    e.preventDefault();
    const wrap = $("#customerCareFormWrap");
    if(wrap) wrap.hidden = false;
    $("#customerCareForm")?.reset();
    wrap?.scrollIntoView({behavior:"smooth",block:"start"});
    return;
  }

  if(cancel){
    e.preventDefault();
    const wrap = $("#customerCareFormWrap");
    if(wrap) wrap.hidden = true;
    $("#customerCareForm")?.reset();
  }
});

if("serviceWorker" in navigator)navigator.serviceWorker.register("/static/sw.js").catch(()=>{});

/* Member Care floating button */
document.addEventListener("click", function(e){
  const button = e.target.closest("#memberCareFloat");
  if(!button) return;
  e.preventDefault();
  const page = document.getElementById("customer_care");
  if(page){
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    page.classList.add("active");
  }
});

/* Payment Management */
async function loadPaymentManagement(){
  const body=$("#paymentHistoryBody");
  if(!body)return;

  body.innerHTML='<tr><td colspan="8">Loading payment history...</td></tr>';

  try{
    const params=new URLSearchParams();

    const search=$("#paymentSearch")?.value.trim();
    const status=$("#paymentStatus")?.value;
    const purpose=$("#paymentPurpose")?.value;
    const circuit=$("#paymentCircuit")?.value;
    const dateFrom=$("#paymentDateFrom")?.value;
    const dateTo=$("#paymentDateTo")?.value;

    if(search)params.set("search",search);
    if(status)params.set("status",status);
    if(purpose)params.set("purpose",purpose);
    if(circuit)params.set("circuit",circuit);
    if(dateFrom)params.set("date_from",dateFrom);
    if(dateTo)params.set("date_to",dateTo);

    const result=await api("/api/payment-history?"+params.toString());
    const payments=Array.isArray(result)?result:(result.payments||[]);
    const summary=result.summary||{};

    if($("#paymentTotalPaid"))
      $("#paymentTotalPaid").textContent=money(summary.total_paid||0);

    if($("#paymentPaidCount"))
      $("#paymentPaidCount").textContent=summary.paid_count||0;

    if($("#paymentPendingCount"))
      $("#paymentPendingCount").textContent=summary.pending_count||0;

    if($("#paymentAbandonedCount"))
      $("#paymentAbandonedCount").textContent=summary.abandoned_count||0;

    if(!payments.length){
      body.innerHTML='<tr><td colspan="8">No payment transactions found.</td></tr>';
      return;
    }

    body.innerHTML=payments.map(p=>{
      const account=[
        p.account_name,
        p.bank_name,
        p.account_number
      ].filter(Boolean).join(" — ");

      const status=String(p.status||"").toLowerCase();

      return `<tr>
        <td>${esc(p.paid_at||p.created_at||"")}</td>
        <td><strong>${esc(p.reference||"")}</strong></td>
        <td>${esc(p.donor_name||"Anonymous")}</td>
        <td>${esc(p.purpose||"")}</td>
        <td>${esc(account||p.church_name||p.circuit||"")}</td>
        <td>${money(p.amount||0)}</td>
        <td><span class="status-badge ${esc(status)}">${esc(p.status||"")}</span></td>
        <td>${esc(p.gateway||"")}</td>
        <td><button type="button" class="secondary payment-details-btn" data-reference="${esc(p.reference||"")}">View</button></td>
      </tr>`;
    }).join("");

  }catch(err){
    body.innerHTML=`<tr><td colspan="9">Error: ${esc(err.message)}</td></tr>`;
  }
}

async function viewPaymentDetails(reference){
  if(!reference)return;

  try{
    const p=await api("/api/payment-history/"+encodeURIComponent(reference));

    const account=[
      p.account_name,
      p.bank_name,
      p.account_number
    ].filter(Boolean).join(" — ");

    let modal=document.getElementById("paymentDetailsModal");

    if(!modal){
      modal=document.createElement("div");
      modal.id="paymentDetailsModal";
      modal.className="modal-overlay";
      modal.innerHTML=`
        <div class="modal-card payment-details-card">
          <div class="modal-head">
            <div>
              <div class="eyebrow">FINANCE & ACCOUNTABILITY</div>
              <h2>Payment Details</h2>
            </div>
            <button type="button" class="secondary" id="closePaymentDetails">Close</button>
          </div>

          <div id="paymentDetailsContent"></div>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById("closePaymentDetails").addEventListener("click",function(){
        modal.remove();
      });

      modal.addEventListener("click",function(e){
        if(e.target===modal) modal.remove();
      });
    }

    const status=String(p.status||"").toLowerCase();

    document.getElementById("paymentDetailsContent").innerHTML=`
      <div class="payment-detail-status ${esc(status)}">
        <span>Status</span>
        <strong>${esc(p.status||"Unknown")}</strong>
      </div>

      <div class="payment-detail-grid">
        <div class="detail-item">
          <span>Reference</span>
          <strong>${esc(p.reference||"")}</strong>
        </div>

        <div class="detail-item">
          <span>Amount</span>
          <strong>${money(p.amount||0)}</strong>
        </div>

        <div class="detail-item">
          <span>Purpose</span>
          <strong>${esc(p.purpose||"")}</strong>
        </div>

        <div class="detail-item">
          <span>Gateway</span>
          <strong>${esc(p.gateway||"")}</strong>
        </div>

        <div class="detail-item">
          <span>Payment Method</span>
          <strong>${esc(p.payment_method||"")}</strong>
        </div>

        <div class="detail-item">
          <span>Transaction ID</span>
          <strong>${esc(p.gateway_transaction_id||"")}</strong>
        </div>
      </div>

      <div class="detail-section">
        <h3>Donor Information</h3>
        <div class="payment-detail-grid">
          <div class="detail-item">
            <span>Name</span>
            <strong>${esc(p.donor_name||"Anonymous")}</strong>
          </div>

          <div class="detail-item">
            <span>Email</span>
            <strong>${esc(p.donor_email||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Phone</span>
            <strong>${esc(p.donor_phone||"")}</strong>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>Church Account</h3>
        <div class="payment-detail-grid">
          <div class="detail-item">
            <span>Account</span>
            <strong>${esc(account||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Account Level</span>
            <strong>${esc(p.account_level||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Circuit</span>
            <strong>${esc(p.circuit||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Local Church</span>
            <strong>${esc(p.church_name||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Account Type</span>
            <strong>${esc(p.account_type||"")}</strong>
          </div>

          <div class="detail-item">
            <span>Branch</span>
            <strong>${esc(p.branch||"")}</strong>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>Transaction Dates</h3>
        <div class="payment-detail-grid">
          <div class="detail-item">
            <span>Paid At</span>
            <strong>${esc(p.paid_at||"Not yet paid")}</strong>
          </div>

          <div class="detail-item">
            <span>Created At</span>
            <strong>${esc(p.created_at||"")}</strong>
          </div>
        </div>
      </div>
    `;

    modal.style.display="flex";

  }catch(err){
    alert("Unable to load payment details: "+err.message);
  }
}

document.addEventListener("click",function(e){
  const btn=e.target.closest(".payment-details-btn");
  if(!btn)return;
  e.preventDefault();
  viewPaymentDetails(btn.dataset.reference||"");
});

function clearPaymentFilters(){
  ["paymentSearch","paymentDateFrom","paymentDateTo"].forEach(id=>{
    const el=$("#"+id);
    if(el)el.value="";
  });

  ["paymentStatus","paymentPurpose","paymentCircuit"].forEach(id=>{
    const el=$("#"+id);
    if(el)el.value="";
  });

  loadPaymentManagement();
}

/* Payment History Excel Export */
function exportPaymentHistory(){
  const params=new URLSearchParams();

  const fields={
    paymentSearch:"search",
    paymentStatus:"status",
    paymentPurpose:"purpose",
    paymentCircuit:"circuit",
    paymentDateFrom:"date_from",
    paymentDateTo:"date_to"
  };

  Object.entries(fields).forEach(([id,key])=>{
    const el=$("#"+id);
    if(el && el.value) params.set(key,el.value);
  });

  window.location.href="/api/payment-history/export?"+params.toString();
}

/* Payment Reconciliation */
async function loadPaymentReconciliation(){
  const body=$("#paymentReconciliationBody");
  if(!body)return;

  body.innerHTML='<tr><td colspan="9">Loading reconciliation...</td></tr>';

  try{
    const params=new URLSearchParams();

    const search=$("#reconSearch")?.value.trim();
    const status=$("#reconStatus")?.value;
    const circuit=$("#reconCircuit")?.value;

    if(search)params.set("search",search);
    if(status)params.set("status",status);
    if(circuit)params.set("circuit",circuit);

    const result=await api("/api/payment-reconciliation?"+params.toString());

    const payments=Array.isArray(result)
      ? result
      : (result.payments||[]);

    const summary=result.summary||{};

    if($("#reconPaidTotal"))
      $("#reconPaidTotal").textContent=money(summary.paid_total||0);

    if($("#reconMatchedCount"))
      $("#reconMatchedCount").textContent=summary.matched_count||0;

    if($("#reconUnmatchedCount"))
      $("#reconUnmatchedCount").textContent=summary.unmatched_count||0;

    if($("#reconMatchedTotal"))
      $("#reconMatchedTotal").textContent=money(summary.matched_income_total||0);

    if(!payments.length){
      body.innerHTML='<tr><td colspan="9">No reconciliation records found.</td></tr>';
      return;
    }

    body.innerHTML=payments.map(p=>{
      const status=String(p.reconciliation_status||"").toLowerCase();

      const account=[
        p.account_name,
        p.bank_name,
        p.account_number
      ].filter(Boolean).join(" — ");

      return `<tr>
        <td>${esc(p.paid_at||p.payment_created_at||"")}</td>
        <td><strong>${esc(p.reference||"")}</strong></td>
        <td>${esc(p.donor_name||"Anonymous")}</td>
        <td>${esc(p.purpose||"")}</td>
        <td>${money(p.payment_amount||0)}</td>
        <td>${p.income_id ? money(p.income_amount||0) : "—"}</td>
        <td>${esc(account||p.church_name||p.circuit||"")}</td>
        <td><span class="status-badge ${esc(status)}">${esc(p.reconciliation_status||"")}</span></td>\
        <td>
          <button type="button" class="secondary recon-details-btn" data-reference="${esc(p.reference||"")}">Details</button>
          ${String(p.reconciliation_status||"").toLowerCase()==="unmatched"
            ? `<button type="button" class="primary recon-reconcile-btn" data-reference="${esc(p.reference||"")}">Reconcile</button>`
            : ""}
        </td>
      </tr>`;
    }).join("");

  }catch(err){
    body.innerHTML=`<tr><td colspan="9">Error: ${esc(err.message)}</td></tr>`;
  }
}


async function viewReconciliationDetails(reference){
  if(!reference)return;

  try{
    const p=await api(
      "/api/payment-reconciliation/"+encodeURIComponent(reference)
    );

    const paymentAmount=money(p.payment_amount||0);
    const incomeAmount=p.income_id
      ? money(p.income_amount||0)
      : "Not posted";

    const difference=money(
      Math.abs(Number(p.amount_difference||0))
    );

    alert(
      "RECONCILIATION DETAILS\n\n"+
      "Status: "+(p.reconciliation_status||"")+"\n"+
      "Reference: "+(p.reference||"")+"\n\n"+
      "ONLINE PAYMENT\n"+
      "Amount: "+paymentAmount+"\n"+
      "Gateway: "+(p.gateway||"")+"\n"+
      "Purpose: "+(p.purpose||"")+"\n"+
      "Donor: "+(p.donor_name||"Anonymous")+"\n"+
      "Paid At: "+(p.paid_at||"")+"\n\n"+
      "INCOME RECORD\n"+
      "Income ID: "+(p.income_id||"Not posted")+"\n"+
      "Income Reference: "+(p.income_reference||"Not posted")+"\n"+
      "Amount: "+incomeAmount+"\n"+
      "Date: "+(p.income_date||"")+"\n"+
      "Source: "+(p.income_source||"")+"\n\n"+
      "AMOUNT DIFFERENCE: "+difference
    );
  }catch(err){
    alert("Unable to load reconciliation details: "+err.message);
  }
}

document.addEventListener("click",function(e){
  const btn=e.target.closest(".recon-details-btn");
  if(!btn)return;
  e.preventDefault();
  viewReconciliationDetails(btn.dataset.reference||"");
});


async function reconcilePayment(reference){
  if(!reference)return;

  const confirmed=confirm(
    "Reconcile this successful payment into Income?\n\n"+
    "Reference: "+reference+"\n\n"+
    "The system will check for an existing income record first to prevent duplicates."
  );

  if(!confirmed)return;

  try{
    const result=await api(
      "/api/payment-reconciliation/"+encodeURIComponent(reference)+"/reconcile",
      {
        method:"POST",
        body:JSON.stringify({})
      }
    );

    alert(result.message||"Payment reconciliation completed.");
    loadPaymentReconciliation();

  }catch(err){
    alert("Reconciliation failed: "+err.message);
  }
}

document.addEventListener("click",function(e){
  const btn=e.target.closest(".recon-reconcile-btn");
  if(!btn)return;

  e.preventDefault();
  reconcilePayment(btn.dataset.reference||"");
});

function clearPaymentReconciliationFilters(){
  ["reconSearch"].forEach(id=>{
    const el=$("#"+id);
    if(el)el.value="";
  });

  ["reconStatus","reconCircuit"].forEach(id=>{
    const el=$("#"+id);
    if(el)el.value="";
  });

  loadPaymentReconciliation();
}

/* Financial Dashboard */
async function loadFinanceSummary(){
  const fundBox=$("#financeFundBreakdown");
  const expenseBox=$("#financeExpenseBreakdown");
  const circuitBox=$("#financeCircuitBreakdown");
  const monthlyBox=$("#financeMonthlyBreakdown");

  try{
    const year=$("#financeSummaryYear")?.value||"";
    const circuit=$("#financeSummaryCircuit")?.value||"";
    const params=new URLSearchParams();
    if(year)params.set("year",year);
    if(circuit)params.set("circuit",circuit);

    const result=await api("/api/finance-summary?"+params.toString());
    const summary=result.summary||{};

    if($("#financeIncomeTotal"))
      $("#financeIncomeTotal").textContent=money(summary.income_total||0);

    if($("#financeExpenseTotal"))
      $("#financeExpenseTotal").textContent=money(summary.expense_total||0);

    if($("#financeNetBalance"))
      $("#financeNetBalance").textContent=money(summary.net_balance||0);

    if($("#financePaidOnline"))
      $("#financePaidOnline").textContent=money(summary.paid_online_total||0);

    if($("#financeMatchedOnline"))
      $("#financeMatchedOnline").textContent=money(summary.matched_online_total||0);

    if($("#financeUnmatchedOnline"))
      $("#financeUnmatchedOnline").textContent=money(summary.unmatched_online_total||0);

    const funds=result.income_by_fund||[];
    if(fundBox){
      fundBox.innerHTML=funds.length
        ? funds.map(x=>`
            <div class="finance-summary-row">
              <span>${esc(x.fund||"Unspecified")}</span>
              <strong>${money(x.total||0)}</strong>
            </div>
          `).join("")
        : "<p>No income records found.</p>";
    }

    const expenses=result.expenses_by_category||[];
    if(expenseBox){
      expenseBox.innerHTML=expenses.length
        ? expenses.map(x=>`
            <div class="finance-summary-row">
              <span>${esc(x.category||"Uncategorized")}</span>
              <strong>${money(x.total||0)}</strong>
            </div>
          `).join("")
        : "<p>No expense records found.</p>";
    }

    const drillSummary=await api("/api/finance-drilldown?"+params.toString());
    const drillCircuits=drillSummary.circuits||[];
    const circuitCount=$("#financeCircuitCount");
    const churchCount=$("#financeChurchCount");

    if(circuitCount)
      circuitCount.textContent=drillCircuits.length;

    if(churchCount)
      churchCount.textContent=drillCircuits.reduce((n,c)=>n+(c.churches||[]).length,0);

    const circuits=result.income_by_circuit||[];
    if(circuitBox){
      const drill=await api("/api/finance-drilldown?"+params.toString());
      const groups=drill.circuits||[];

      circuitBox.innerHTML=groups.length
        ? groups.map(x=>`
            <div class="finance-drill-group">
              <div class="finance-summary-row">
                <span><strong>${esc(x.circuit||"Diocesan")}</strong></span>
                <strong>${money(x.net_balance||0)}</strong>
              </div>
              <div class="finance-drill-metrics">
                <span>Income <strong>${money(x.total_income||0)}</strong></span>
                <span>Expenses <strong>${money(x.total_expenses||0)}</strong></span>
                <span>Net <strong>${money(x.net_balance||0)}</strong></span>
              </div>
              ${(x.churches||[]).map(ch=>`
                <div class="finance-drill-church">
                  <span>${esc(ch.church_name||"Unspecified Local Church")}</span>
                  <strong>${money(ch.income_total||0)}</strong>
                </div>
              `).join("")}
            </div>
          `).join("")
        : "<p>No circuit/local church income records found.</p>";
    }

    const months=result.monthly_income||[];
    if(monthlyBox){
      monthlyBox.innerHTML=months.length
        ? months.map(x=>`
            <div class="finance-summary-row">
              <span>${esc(x.month||"")}</span>
              <strong>${money(x.total||0)}</strong>
            </div>
          `).join("")
        : "<p>No monthly income records found.</p>";
    }

    const circuitSelect=$("#financeSummaryCircuit");
    if(circuitSelect){
      const drill=await api("/api/finance-drilldown?"+params.toString());
      const available=(drill.circuits||[]).map(x=>x.circuit).filter(Boolean);
      const current=circuitSelect.value;
      circuitSelect.innerHTML='<option value="">All Circuits</option>'+available.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
      if(available.includes(current))circuitSelect.value=current;
    }

    const yearSelect=$("#financeSummaryYear");
    if(yearSelect && yearSelect.options.length<=1){
      const current=new Date().getFullYear();
      for(let y=current;y>=current-5;y--){
        const option=document.createElement("option");
        option.value=String(y);
        option.textContent=String(y);
        yearSelect.appendChild(option);
      }
    }

  }catch(err){
    [fundBox,expenseBox,circuitBox,monthlyBox].forEach(box=>{
      if(box)box.innerHTML=`<p>Error: ${esc(err.message)}</p>`;
    });
  }
}

/* Financial Dashboard circuit filter */
document.addEventListener("change",e=>{
  if(e.target && e.target.id==="financeSummaryCircuit"){
    loadFinanceSummary();
  }
});

/* Financial Dashboard year filter */
document.addEventListener("change",e=>{
  if(e.target && e.target.id==="financeSummaryYear"){
    loadFinanceSummary();
  }
});


function escapeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, function(ch){
    return ({
      "&":"&amp;",
      "<":"&lt;",
      ">":"&gt;",
      '"':"&quot;",
      "'":"&#39;"
    })[ch];
  });
}

async function loadFinancialAccountabilityReport(){
  const year=document.getElementById("financialReportYear")?.value || "";
  const circuit=document.getElementById("financialReportCircuit")?.value || "";

  const params=new URLSearchParams();
  if(year) params.set("year",year);
  if(circuit) params.set("circuit",circuit);

  try{
    const data=await api("/api/financial-accountability-report?"+params.toString());

    const money=v=>"₦"+Number(v||0).toLocaleString("en-NG",{
      minimumFractionDigits:2,
      maximumFractionDigits:2
    });

    document.getElementById("financialReportIncome").textContent=
      money(data.summary.income_total);

    document.getElementById("financialReportExpenses").textContent=
      money(data.summary.expense_total);

    document.getElementById("financialReportNet").textContent=
      money(data.summary.net_balance);

    document.getElementById("financialReportIncomeCount").textContent=
      data.summary.income_count || 0;

    document.getElementById("financialReportExpenseCount").textContent=
      data.summary.expense_count || 0;

    const funds=document.getElementById("financialReportFunds");

    if(data.income_by_fund && data.income_by_fund.length){
      funds.innerHTML=data.income_by_fund.map(x=>`
        <div class="finance-summary-row">
          <span>${escapeHtml(x.fund || "Unspecified")}</span>
          <strong>${money(x.total)}</strong>
        </div>
      `).join("");
    }else{
      funds.innerHTML='<p class="muted">No income records.</p>';
    }

    const categories=document.getElementById("financialReportCategories");

    if(data.expenses_by_category && data.expenses_by_category.length){
      categories.innerHTML=data.expenses_by_category.map(x=>`
        <div class="finance-summary-row">
          <span>${escapeHtml(x.category || "Uncategorized")}</span>
          <strong>${money(x.total)}</strong>
        </div>
      `).join("");
    }else{
      categories.innerHTML='<p class="muted">No expense records.</p>';
    }

    document.getElementById("financialReportInfo").textContent=
      "Generated: "+(data.generated_at || "—")+
      " | Year: "+(data.year || "All")+
      " | Circuit: "+(data.circuit || "All");

  }catch(err){
    console.error("Financial accountability report error:",err);
    const info=document.getElementById("financialReportInfo");
    if(info) info.textContent="Unable to load financial accountability report.";
  }
}



document.addEventListener("change",e=>{
  if(e.target && e.target.id==="financialReportYear"){
    loadFinancialAccountabilityReport();
  }
});

document.addEventListener("change",e=>{
  if(e.target && e.target.id==="financialReportCircuit"){
    loadFinancialAccountabilityReport();
  }
});

document.addEventListener("DOMContentLoaded",()=>{
  const page=document.getElementById("financial_accountability");
  if(page && !page.classList.contains("hidden")){
    loadFinancialAccountabilityReport();
  }
});


async function exportFinancialAccountabilityReport(){
  const year=document.getElementById("financialReportYear")?.value || "";
  const circuit=document.getElementById("financialReportCircuit")?.value || "";

  const params=new URLSearchParams();
  if(year) params.set("year",year);
  if(circuit) params.set("circuit",circuit);

  try{
    const data=await api("/api/financial-accountability-report?"+params.toString());
    const rows=[
      ["FINANCIAL ACCOUNTABILITY REPORT",""],
      ["Generated At",data.generated_at || ""],
      ["Year",data.year || "All"],
      ["Circuit",data.circuit || "All"],
      ["" ,""],
      ["SUMMARY",""],
      ["Total Income",data.summary.income_total || 0],
      ["Total Expenses",data.summary.expense_total || 0],
      ["Net Balance",data.summary.net_balance || 0],
      ["Income Records",data.summary.income_count || 0],
      ["Expense Records",data.summary.expense_count || 0],
      ["" ,""],
      ["INCOME BY FUND",""]
    ];

    (data.income_by_fund || []).forEach(x=>{
      rows.push([x.fund || "Unspecified",x.total || 0]);
    });

    rows.push(["",""],["EXPENSES BY CATEGORY",""]);

    (data.expenses_by_category || []).forEach(x=>{
      rows.push([x.category || "Uncategorized",x.total || 0]);
    });

    const csv=rows.map(row=>row.map(v=>{
      const value=String(v ?? "");
      return '"' + value.replace(/"/g,'""') + '"';
    }).join(",")).join("\n");

    const blob=new Blob([csv],{type:"text/csv;charset=utf-8;"});
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;
    a.download="Financial_Accountability_Report.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

  }catch(err){
    console.error("Export report error:",err);
    alert("Unable to export financial accountability report.");
  }
}

function printFinancialAccountabilityReport(){
  const report=document.getElementById("financial_accountability");
  if(!report){
    alert("Financial Accountability Report page not found.");
    return;
  }

  const printWindow=window.open("","_blank");

  if(!printWindow){
    alert("Please allow pop-ups to print the report.");
    return;
  }

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Financial Accountability Report</title>
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        body{font-family:Arial,sans-serif;padding:30px;color:#111}
        h1,h2,h3{margin-bottom:8px}
        .card{border:1px solid #ddd;border-radius:8px;padding:18px;margin:15px 0}
        .stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
        .stat-card{border:1px solid #ddd;padding:15px;border-radius:8px}
        .stat-card span{display:block;color:#666;margin-bottom:6px}
        .stat-card strong{font-size:20px}
        .actions-row{display:none}
        .page-header p{color:#666}
        .finance-summary-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee}
        @media print{
          body{padding:10px}
          .stats-grid{grid-template-columns:repeat(3,1fr)}
        }
      </style>
    </head>
    <body>
      ${report.innerHTML}
    </body>
    </html>
  `);

  printWindow.document.close();
  printWindow.focus();

  setTimeout(()=>{
    printWindow.print();
  },500);
}

async function loadFinancialReportCircuitBreakdown(){
  const year=document.getElementById("financialReportYear")?.value || "";
  const circuit=document.getElementById("financialReportCircuit")?.value || "";
  const box=document.getElementById("financialReportCircuitBreakdown");

  if(!box) return;

  const params=new URLSearchParams();
  if(year) params.set("year",year);
  if(circuit) params.set("circuit",circuit);

  try{
    const data=await api("/api/financial-accountability-report?"+params.toString()+"&_cb="+Date.now());
    const churches=data.church_accountability || [];

    if(!churches.length){
      box.innerHTML='<p class="muted">No church financial records.</p>';
      return;
    }

    const money=v=>"₦"+Number(v||0).toLocaleString("en-NG",{
      minimumFractionDigits:2,
      maximumFractionDigits:2
    });

    const groups={};

    churches.forEach(ch=>{
      const key=ch.circuit || "Diocesan";
      if(!groups[key]){
        groups[key]={
          circuit:key,
          churches:[],
          income:0,
          expense:0,
          net:0
        };
      }

      groups[key].churches.push(ch);
      groups[key].income += Number(ch.income_total||0);
    });

    const drill=await api("/api/finance-drilldown?"+params.toString());

    (drill.circuits || []).forEach(c=>{
      const key=c.circuit || "Diocesan";
      if(!groups[key]) return;

      groups[key].expense=Number(c.total_expenses||0);
      groups[key].net=Number(c.net_balance||0);
    });

    box.innerHTML=Object.values(groups).map(g=>`
      <div class="finance-drill-group">
        <div class="finance-summary-row">
          <strong>${escapeHtml(g.circuit)}</strong>
          <strong>${money(g.net)}</strong>
        </div>

        <div class="finance-drill-metrics">
          <span>Church Income <strong>${money(g.income)}</strong></span>
          <span>Circuit Expenses <strong>${money(g.expense)}</strong></span>
          <span>Net Balance <strong>${money(g.net)}</strong></span>
        </div>

        <div>
          ${g.churches.map(ch=>`
            <div class="finance-drill-church">
              <span>${escapeHtml(ch.church_name || "Local Church")}</span>
              <span>Income <strong>${money(ch.income_total)}</strong></span>
              <span>Expenses <strong>${money(ch.expense_total)}</strong></span>
              <span>Net <strong>${money(ch.net_balance)}</strong></span>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("");

  }catch(err){
    console.error("Church accountability error:",err);
    box.innerHTML='<p class="muted">Unable to load church accountability data.</p>';
  }
}

const originalLoadFinancialAccountabilityReport=loadFinancialAccountabilityReport;

loadFinancialAccountabilityReport=async function(){
  await originalLoadFinancialAccountabilityReport();
  await loadFinancialReportCircuitBreakdown();
};

/* Financial Accountability filters */
async function populateFinancialAccountabilityFilters(){
  const yearSelect=document.getElementById("financialReportYear");
  const circuitSelect=document.getElementById("financialReportCircuit");

  if(yearSelect && yearSelect.options.length<=1){
    const current=new Date().getFullYear();

    for(let y=current;y>=current-5;y--){
      const option=document.createElement("option");
      option.value=String(y);
      option.textContent=String(y);
      yearSelect.appendChild(option);
    }
  }

  if(circuitSelect){
    try{
      const current=circuitSelect.value;
      const drill=await api("/api/finance-drilldown");

      const systemCircuits=["Diocesan","Effurun","Warri","Sapele","Steel Town"];
      const available=[...new Set(
        systemCircuits.concat(
          (drill.circuits||[]).map(x=>x.circuit).filter(Boolean)
        )
      )];

      circuitSelect.innerHTML=
        '<option value="">All Circuits</option>'+
        available.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");

      if(available.includes(current)){
        circuitSelect.value=current;
      }
    }catch(err){
      console.error("Financial accountability filter error:",err);
    }
  }
}

document.addEventListener("DOMContentLoaded",()=>{
  populateFinancialAccountabilityFilters();
});

/* =========================================================
   DELTA SOUTH CONFERENCE — CLEAN MULTI-PARTICIPANT WEBRTC
   ========================================================= */

window.DSConferenceCall = {
  roomId: null,
  localStream: null,
  participantId: null,
  active: false,
  audioOnly: false,
  pollTimer: null,
  presenceTimer: null,
  lastSignalId: 0,
  peers: new Map(),
  remoteStreams: new Map(),
  pendingIce: new Map(),
  recorder: null,
  recordedChunks: [],
  recording: false,

  async start(roomId, audioOnly = false) {
    if (this.active) {
      console.warn("Conference is already active.");
      return;
    }

    this.roomId = roomId;
    this.audioOnly = !!audioOnly;
    this.participantId =
      "p-" + Date.now() + "-" + Math.random().toString(36).slice(2, 9);

    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: !this.audioOnly
      });
    } catch (error) {
      console.error("Conference media error:", error);
      this.setCallStatus(
        "Microphone/camera permission failed: " +
        (error.message || "permission denied")
      );
      return;
    }

    this.active = true;

    const local = document.querySelector("#conferenceLocalVideo");
    if (local) {
      local.srcObject = this.localStream;
      local.muted = true;
      local.autoplay = true;
      local.playsInline = true;
      local.play().catch(() => {});
    }

    this.setCallStatus(
      this.audioOnly
        ? "Audio conference connected. Waiting for participants..."
        : "Video conference connected. Waiting for participants..."
    );

    this.ensureConferenceUI();
    this.startPolling();
    this.startPresence();

    await this.updatePresence();
    await this.syncPresence();
  },

  async sendSignal(signalType, recipientId, payload) {
    if (!this.roomId || !this.participantId) return null;

    try {
      const response = await fetch(
        "/api/conference/" + this.roomId + "/signals",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            sender_id: this.participantId,
            recipient_id: recipientId || "",
            signal_type: signalType,
            payload: payload || {}
          })
        }
      );

      if (!response.ok) {
        throw new Error(await response.text());
      }

      return await response.json();
    } catch (error) {
      console.error("Conference signal error:", error);
      return null;
    }
  },

  startPolling() {
    this.stopPolling();

    this.pollTimer = setInterval(() => {
      this.pollSignals().catch(error => {
        console.error("Conference polling error:", error);
      });
    }, 600);

    this.pollSignals().catch(() => {});
  },

  startPresence() {
    this.stopPresence();

    this.presenceTimer = setInterval(() => {
      this.updatePresence().catch(error => {
        console.warn("Conference presence update failed:", error);
      });

      this.syncPresence().catch(error => {
        console.warn("Conference presence sync failed:", error);
      });
    }, 2500);

    this.updatePresence().catch(() => {});
    this.syncPresence().catch(() => {});
  },

  stopPresence() {
    if (this.presenceTimer) {
      clearInterval(this.presenceTimer);
      this.presenceTimer = null;
    }
  },

  async updatePresence() {
    if (!this.active || !this.roomId || !this.participantId) {
      return;
    }

    const response = await fetch(
      "/api/conference/" +
      this.roomId +
      "/presence",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          participant_id: this.participantId,
          participant_name: "Participant",
          audio_only: this.audioOnly
        })
      }
    );

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return response.json();
  },

  async syncPresence() {
    if (!this.active || !this.roomId || !this.participantId) {
      return;
    }

    const response = await fetch(
      "/api/conference/" +
      this.roomId +
      "/presence"
    );

    if (!response.ok) return;

    const participants = await response.json();
    const activeIds = new Set();

    for (const participant of participants) {
      const remoteId = String(
        participant.participant_id || ""
      );

      if (!remoteId || remoteId === this.participantId) {
        continue;
      }

      activeIds.add(remoteId);

      /*
       * Only the participant with the smaller ID
       * creates the initial WebRTC offer.
       */
      if (
        this.participantId < remoteId &&
        !this.peers.has(remoteId)
      ) {
        try {
          const pc = await this.createPeer(remoteId, true);

          if (
            pc &&
            pc.signalingState === "stable"
          ) {
            const offer = await pc.createOffer();

            await pc.setLocalDescription(offer);

            await this.sendSignal(
              "offer",
              remoteId,
              {
                kind: "sdp-offer",
                participant_id: this.participantId,
                description: pc.localDescription
              }
            );
          }
        } catch (error) {
          console.error(
            "Conference offer creation failed:",
            remoteId,
            error
          );

          this.removePeer(remoteId);
        }
      }
    }

    for (const peerId of Array.from(this.peers.keys())) {
      if (!activeIds.has(peerId)) {
        this.removePeer(peerId);
      }
    }

    this.updateParticipantCount();
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  },

  async pollSignals() {
    if (!this.active || !this.roomId) return;

    const response = await fetch(
      "/api/conference/" +
      this.roomId +
      "/signals?since_id=" +
      encodeURIComponent(this.lastSignalId)
    );

    if (!response.ok) return;

    const signals = await response.json();

    for (const signal of signals) {
      this.lastSignalId = Math.max(
        this.lastSignalId,
        Number(signal.id) || 0
      );

      if (
        signal.recipient_id &&
        signal.recipient_id !== this.participantId
      ) {
        continue;
      }

      if (signal.sender_id === this.participantId) {
        continue;
      }

      let payload = signal.payload;

      if (typeof payload === "string") {
        try {
          payload = JSON.parse(payload);
        } catch {
          payload = {};
        }
      }

      await this.handleSignal({
        ...signal,
        payload
      });
    }
  },

  async handleSignal(signal) {
    const sender = String(signal.sender_id || "");
    const payload = signal.payload || {};

    if (!sender || sender === this.participantId) return;

    if (signal.signal_type === "offer") {
      if (payload.kind !== "sdp-offer") return;

      const remoteId = String(
        payload.participant_id || sender
      );

      const pc = await this.createPeer(remoteId, false);

      if (!pc) return;

      await pc.setRemoteDescription(
        new RTCSessionDescription(payload.description)
      );

      await this.flushPendingIce(remoteId);

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      await this.sendSignal(
        "answer",
        remoteId,
        {
          kind: "sdp-answer",
          participant_id: this.participantId,
          description: pc.localDescription
        }
      );

      this.updateParticipantCount();
      return;
    }

    if (signal.signal_type === "answer") {
      if (payload.kind !== "sdp-answer") return;

      const remoteId = String(
        payload.participant_id || sender
      );

      const pc = this.peers.get(remoteId);
      if (!pc) return;

      await pc.setRemoteDescription(
        new RTCSessionDescription(payload.description)
      );

      await this.flushPendingIce(remoteId);
      return;
    }

    if (signal.signal_type === "ice") {
      const remoteId = String(
        payload.participant_id || sender
      );

      const candidate = payload.candidate;
      if (!candidate) return;

      const pc = this.peers.get(remoteId);

      if (!pc || !pc.remoteDescription) {
        if (!this.pendingIce.has(remoteId)) {
          this.pendingIce.set(remoteId, []);
        }

        this.pendingIce.get(remoteId).push(candidate);
        return;
      }

      try {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (error) {
        console.warn("ICE candidate rejected:", error);
      }

      return;
    }

    if (signal.signal_type === "leave") {
      this.removePeer(sender);
      this.updateParticipantCount();
    }
  },

  async createPeer(peerId, initiator = false) {
    if (this.peers.has(peerId)) {
      return this.peers.get(peerId);
    }

    const pc = new RTCPeerConnection({
      iceServers: [
        {
          urls: [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302"
          ]
        }
      ]
    });

    this.peers.set(peerId, pc);

    if (this.localStream) {
      for (const track of this.localStream.getTracks()) {
        pc.addTrack(track, this.localStream);
      }
    }

    pc.onicecandidate = event => {
      if (!event.candidate) return;

      this.sendSignal(
        "ice",
        peerId,
        {
          participant_id: this.participantId,
          candidate: event.candidate.toJSON
            ? event.candidate.toJSON()
            : event.candidate
        }
      );
    };

    pc.ontrack = event => {
      let stream = this.remoteStreams.get(peerId);

      if (!stream) {
        stream = new MediaStream();
        this.remoteStreams.set(peerId, stream);
      }

      const track = event.track;

      if (!stream.getTracks().some(t => t.id === track.id)) {
        stream.addTrack(track);
      }

      this.renderRemoteParticipant(peerId, stream);
      this.updateParticipantCount();
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;

      if (
        state === "failed" ||
        state === "closed" ||
        state === "disconnected"
      ) {
        this.removePeer(peerId);
        this.updateParticipantCount();
      }
    };

    pc.oniceconnectionstatechange = () => {
      if (
        pc.iceConnectionState === "failed" ||
        pc.iceConnectionState === "closed"
      ) {
        this.removePeer(peerId);
        this.updateParticipantCount();
      }
    };

    if (initiator) {
      console.log("Creating conference offer for:", peerId);
    }

    return pc;
  },

  async flushPendingIce(peerId) {
    const pc = this.peers.get(peerId);
    const queue = this.pendingIce.get(peerId);

    if (!pc || !queue || !pc.remoteDescription) return;

    for (const candidate of queue) {
      try {
        await pc.addIceCandidate(
          new RTCIceCandidate(candidate)
        );
      } catch (error) {
        console.warn("Queued ICE candidate rejected:", error);
      }
    }

    this.pendingIce.delete(peerId);
  },

  renderRemoteParticipant(peerId, stream) {
    let grid = document.querySelector(".conference-video-grid");

    if (!grid) {
      grid = document.querySelector(
        "#conferenceRemoteVideo"
      )?.parentElement;
    }

    if (!grid) return;

    let card = document.querySelector(
      '[data-conference-peer="' + CSS.escape(peerId) + '"]'
    );

    if (!card) {
      card = document.createElement("div");
      card.className = "conference-video-card";
      card.dataset.conferencePeer = peerId;

      const title = document.createElement("div");
      title.className = "conference-peer-name";
      title.textContent = "Remote Participant";

      const video = document.createElement("video");
      video.autoplay = true;
      video.playsInline = true;
      video.controls = false;
      video.muted = false;
      video.volume = 1;
      video.className = "conference-remote-peer-video";

      card.appendChild(title);
      card.appendChild(video);
      grid.appendChild(card);
    }

    const video = card.querySelector("video");

    if (video && video.srcObject !== stream) {
      video.srcObject = stream;
      video.muted = false;
      video.volume = 1;

      video.play().catch(error => {
        console.warn(
          "Remote autoplay blocked. User interaction may be required.",
          error
        );
      });
    }
  },

  removePeer(peerId) {
    const pc = this.peers.get(peerId);

    if (pc) {
      try {
        pc.close();
      } catch {}
    }

    this.peers.delete(peerId);
    this.remoteStreams.delete(peerId);
    this.pendingIce.delete(peerId);

    const card = document.querySelector(
      '[data-conference-peer="' +
      CSS.escape(peerId) +
      '"]'
    );

    if (card) {
      card.remove();
    }

    this.updateParticipantCount();
  },

  toggleMute() {
    if (!this.localStream) return;

    const tracks = this.localStream.getAudioTracks();

    if (!tracks.length) return;

    const enabled = !tracks[0].enabled;

    tracks.forEach(track => {
      track.enabled = enabled;
    });

    const button = document.querySelector("#conferenceMuteBtn");

    if (button) {
      button.textContent = enabled ? "Mute" : "Unmute";
    }

    this.setCallStatus(
      enabled ? "Microphone on" : "Microphone muted"
    );
  },

  toggleCamera() {
    if (!this.localStream) return;

    const tracks = this.localStream.getVideoTracks();

    if (!tracks.length) return;

    const enabled = !tracks[0].enabled;

    tracks.forEach(track => {
      track.enabled = enabled;
    });

    const button = document.querySelector("#conferenceCameraBtn");

    if (button) {
      button.textContent = enabled
        ? "Camera Off"
        : "Camera On";
    }

    this.setCallStatus(
      enabled ? "Camera on" : "Camera off"
    );
  },

  async startRecording() {
    if (!this.active) {
      this.setCallStatus("Start the conference before recording.");
      return;
    }

    if (this.recording) return;

    const tracks = [];

    if (this.localStream) {
      this.localStream
        .getAudioTracks()
        .forEach(track => tracks.push(track));
    }

    for (const stream of this.remoteStreams.values()) {
      stream
        .getAudioTracks()
        .forEach(track => tracks.push(track));
    }

    if (!tracks.length) {
      this.setCallStatus("No audio stream available for recording.");
      return;
    }

    let recordStream;

    const videoElements = [];

    const localVideo = document.querySelector(
      "#conferenceLocalVideo"
    );

    if (localVideo && !this.audioOnly) {
      videoElements.push(localVideo);
    }

    document
      .querySelectorAll(".conference-remote-peer-video")
      .forEach(video => videoElements.push(video));

    if (videoElements.length && !this.audioOnly) {
      const canvas = document.createElement("canvas");
      canvas.width = 1280;
      canvas.height = 720;

      const ctx = canvas.getContext("2d");

      const draw = () => {
        if (!this.recording) return;

        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const count = videoElements.length;
        const cols = count <= 1 ? 1 : count <= 4 ? 2 : 3;
        const rows = Math.ceil(count / cols);

        const cellW = canvas.width / cols;
        const cellH = canvas.height / rows;

        videoElements.forEach((video, index) => {
          const x = (index % cols) * cellW;
          const y = Math.floor(index / cols) * cellH;

          try {
            ctx.drawImage(video, x, y, cellW, cellH);
          } catch {}
        });

        requestAnimationFrame(draw);
      };

      recordStream = canvas.captureStream(20);

      for (const track of tracks) {
        recordStream.addTrack(track);
      }

      this.recording = true;
      draw();
    } else {
      recordStream = new MediaStream(tracks);
      this.recording = true;
    }

    const mimeTypes = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
      "audio/webm;codecs=opus",
      "audio/webm"
    ];

    const mimeType = mimeTypes.find(type =>
      MediaRecorder.isTypeSupported(type)
    );

    try {
      this.recordedChunks = [];

      this.recorder = new MediaRecorder(
        recordStream,
        mimeType ? { mimeType } : undefined
      );

      this.recorder.ondataavailable = event => {
        if (event.data && event.data.size) {
          this.recordedChunks.push(event.data);
        }
      };

      this.recorder.onstop = () => {
        const blob = new Blob(
          this.recordedChunks,
          {
            type: mimeType || "video/webm"
          }
        );

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");

        a.href = url;
        a.download =
          "MCN-Delta-South-Conference-" +
          new Date()
            .toISOString()
            .replace(/[:.]/g, "-") +
          ".webm";

        document.body.appendChild(a);
        a.click();
        a.remove();

        setTimeout(() => URL.revokeObjectURL(url), 10000);

        this.recordedChunks = [];
        this.recording = false;

        this.setCallStatus(
          "Recording saved to this device."
        );

        this.updateRecordingButton();
      };

      this.recorder.onerror = error => {
        console.error("Conference recording error:", error);
        this.recording = false;
        this.setCallStatus("Recording failed.");
        this.updateRecordingButton();
      };

      this.recorder.start(1000);

      this.setCallStatus("Conference recording started.");
      this.updateRecordingButton();

    } catch (error) {
      console.error("Unable to start recording:", error);
      this.recording = false;
      this.recorder = null;
      this.setCallStatus(
        "This browser does not support conference recording."
      );
    }
  },

  stopRecording() {
    if (!this.recorder || this.recorder.state === "inactive") {
      this.recording = false;
      this.updateRecordingButton();
      return;
    }

    this.setCallStatus("Finishing conference recording...");
    this.recorder.stop();
  },

  ensureConferenceUI() {
    const controls = document.querySelector(
      ".conference-call-controls"
    );

    if (!controls) return;

    if (!document.querySelector("#conferenceParticipantCount")) {
      const count = document.createElement("span");
      count.id = "conferenceParticipantCount";
      count.className = "conference-participant-count";
      count.textContent = "Participants: 1";
      controls.appendChild(count);
    }

    if (!document.querySelector("#conferenceRecordBtn")) {
      const button = document.createElement("button");

      button.id = "conferenceRecordBtn";
      button.type = "button";
      button.className = "btn btn-secondary";
      button.textContent = "Start Recording";

      button.addEventListener("click", () => {
        if (this.recording) {
          this.stopRecording();
        } else {
          this.startRecording();
        }
      });

      controls.appendChild(button);
    }

    this.updateRecordingButton();
    this.updateParticipantCount();
  },

  updateRecordingButton() {
    const button = document.querySelector(
      "#conferenceRecordBtn"
    );

    if (!button) return;

    button.textContent = this.recording
      ? "Stop Recording"
      : "Start Recording";
  },

  updateParticipantCount() {
    const count = document.querySelector(
      "#conferenceParticipantCount"
    );

    if (!count) return;

    count.textContent =
      "Participants: " +
      (this.active ? 1 + this.peers.size : 0);
  },

  setCallStatus(message) {
    const status = document.querySelector(
      "#conferenceCallStatus"
    );

    if (status) {
      status.textContent = message;
    }

    console.log("Conference:", message);
  },

  async stop() {
    if (!this.active && !this.localStream) return;

    try {
      await this.sendSignal(
        "leave",
        "",
        {
          participant_id: this.participantId
        }
      );
    } catch {}

    this.stopRecording();
    this.stopPolling();

    for (const [peerId, pc] of this.peers) {
      try {
        pc.close();
      } catch {}

      const card = document.querySelector(
        '[data-conference-peer="' +
        CSS.escape(peerId) +
        '"]'
      );

      if (card) card.remove();
    }

    this.peers.clear();
    this.remoteStreams.clear();
    this.pendingIce.clear();

    if (this.localStream) {
      this.localStream.getTracks().forEach(track => {
        try {
          track.stop();
        } catch {}
      });
    }

    this.localStream = null;
    this.active = false;

    const local = document.querySelector(
      "#conferenceLocalVideo"
    );

    if (local) {
      local.srcObject = null;
    }

    this.updateParticipantCount();
    this.setCallStatus("Conference call ended.");
  }
};

console.log(
  "Delta South NEW multi-participant WebRTC conference engine loaded."
);

document.addEventListener("DOMContentLoaded", function () {
  const memberRefreshBtn = document.getElementById("memberRegistrationsRefreshBtn");
  if (memberRefreshBtn && typeof loadMemberRegistrations === "function") {
    memberRefreshBtn.addEventListener("click", function () {
      loadMemberRegistrations();
    });
  }

  const refreshBtn = document.getElementById("accountRequestsRefreshBtn");
  if (refreshBtn && typeof loadAccountRequests === "function") {
    refreshBtn.addEventListener("click", function () {
      loadAccountRequests();
    });
  }
});

/* =========================================================
   FINAL MOBILE NAV CLEANUP
   Keep the new working mobile toggle.
   Hide only the old duplicate toggle.
   Reuse the existing menu panel for navigation.
   ========================================================= */
(function(){
  function fixDuplicateMobileNav(){
    const nav = document.getElementById("nav");
    const newToggle = document.getElementById("mobileNavToggle");
    const oldToggle = document.getElementById("menuToggle");
    const wrapper = oldToggle ? oldToggle.closest(".nav-dropdown") : null;
    const panel = document.getElementById("menuPanel");

    if(!nav || !newToggle || !oldToggle || !wrapper || !panel) return;

    /* Hide ONLY the old duplicate toggle. */
    oldToggle.style.display = "none";

    /* Keep the existing menu panel as the navigation list. */
    wrapper.style.display = "block";
    wrapper.style.width = "100%";
    wrapper.style.position = "static";

    panel.style.position = "static";
    panel.style.width = "100%";
    panel.style.maxHeight = "min(58vh,520px)";
    panel.style.overflowY = "auto";
    panel.style.marginTop = "8px";

    /* The new working toggle controls the old menu panel. */
    if(newToggle.dataset.panelConnected !== "1"){
      newToggle.dataset.panelConnected = "1";

      newToggle.addEventListener("click", function(){
        setTimeout(function(){
          const isOpen = nav.classList.contains("mobile-nav-open");
          panel.classList.toggle("open", isOpen);
        }, 0);
      });
    }

    /* Keep the two states synchronized. */
    const observer = new MutationObserver(function(){
      const isOpen = nav.classList.contains("mobile-nav-open");
      panel.classList.toggle("open", isOpen);
    });

    observer.observe(nav, {
      attributes:true,
      attributeFilter:["class"]
    });

    /* Hide the old toggle again if another script tries to show it. */
    setInterval(function(){
      if(oldToggle.style.display !== "none"){
        oldToggle.style.display = "none";
      }
    }, 500);
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded",fixDuplicateMobileNav);
  }else{
    fixDuplicateMobileNav();
  }
})();

/* Final mobile navigation styling */
(function(){
  const style = document.createElement("style");
  style.textContent = `
    @media(max-width:700px){

      #nav .nav-dropdown{
        display:block !important;
        width:100% !important;
        position:static !important;
      }

      #nav #menuToggle{
        display:none !important;
      }

      #nav #menuPanel{
        position:static !important;
        width:100% !important;
        max-height:min(58vh,520px) !important;
        margin-top:8px !important;
        overflow-y:auto !important;
        border-radius:12px !important;
        box-shadow:0 8px 22px rgba(15,23,42,.10) !important;
      }

      #nav:not(.mobile-nav-open) #menuPanel{
        display:none !important;
      }

      #nav.mobile-nav-open #menuPanel{
        display:flex !important;
        flex-direction:column !important;
      }

      #nav.mobile-nav-open #menuPanel button[data-page]{
        display:flex !important;
        width:100% !important;
        min-height:44px !important;
        align-items:center !important;
        justify-content:flex-start !important;
        margin:3px 0 !important;
        padding:10px 14px !important;
        text-align:left !important;
      }

      #nav.mobile-nav-open > .mobile-nav-toggle{
        display:flex !important;
      }
    }
  `;
  document.head.appendChild(style);
})();

/* =========================================================
   DEFINITIVE MOBILE DASHBOARD MENU
   One visible toggle + existing navigation panel
   ========================================================= */
(function(){
  function installDefinitiveMobileNav(){
    const nav = document.getElementById("nav");
    const panel = document.getElementById("menuPanel");
    const oldToggle = document.getElementById("menuToggle");

    if(!nav || !panel) return;

    let toggle = document.getElementById("mobileNavToggle");

    if(!toggle){
      toggle = document.createElement("button");
      toggle.type = "button";
      toggle.id = "mobileNavToggle";
      toggle.className = "mobile-nav-toggle-final";
      toggle.setAttribute("aria-expanded","false");
      toggle.innerHTML =
        '<span class="mobile-nav-left-final">' +
          '<span class="mobile-nav-icon-final">☰</span>' +
          '<span id="mobileNavTitleFinal">Dashboard</span>' +
        '</span>' +
        '<span id="mobileNavArrowFinal">▼</span>';

      nav.insertBefore(toggle, nav.firstChild);
    }

    /* Hide the old duplicate button only. */
    if(oldToggle){
      oldToggle.style.setProperty("display","none","important");
    }

    function updateTitle(){
      const active = panel.querySelector("button[data-page].active");
      const title = document.getElementById("mobileNavTitleFinal");

      if(active && title){
        title.textContent = active.textContent.trim();
      }
    }

    function closeMenu(){
      nav.classList.remove("mobile-nav-open");
      panel.classList.remove("open");
      toggle.setAttribute("aria-expanded","false");

      const arrow = document.getElementById("mobileNavArrowFinal");
      if(arrow) arrow.textContent = "▼";
    }

    function openMenu(){
      nav.classList.add("mobile-nav-open");
      panel.classList.add("open");
      toggle.setAttribute("aria-expanded","true");

      const arrow = document.getElementById("mobileNavArrowFinal");
      if(arrow) arrow.textContent = "▲";
    }

    if(toggle.dataset.ready !== "1"){
      toggle.dataset.ready = "1";

      toggle.addEventListener("click",function(e){
        e.preventDefault();
        e.stopPropagation();

        if(nav.classList.contains("mobile-nav-open")){
          closeMenu();
        }else{
          openMenu();
        }
      });

      panel.querySelectorAll("button[data-page]").forEach(button=>{
        button.addEventListener("click",function(){
          setTimeout(function(){
            updateTitle();
            closeMenu();
          },50);
        });
      });

      document.addEventListener("click",function(e){
        if(
          window.innerWidth <= 700 &&
          nav.classList.contains("mobile-nav-open") &&
          !nav.contains(e.target)
        ){
          closeMenu();
        }
      });
    }

    updateTitle();
  }

  if(document.readyState === "loading"){
    document.addEventListener(
      "DOMContentLoaded",
      installDefinitiveMobileNav
    );
  }else{
    installDefinitiveMobileNav();
  }
})();

/* Definitive mobile menu appearance */
(function(){
  const style=document.createElement("style");

  style.textContent=`
    @media(max-width:700px){

      #nav{
        display:block !important;
        padding:8px 12px !important;
        background:#fff !important;
        position:sticky !important;
        top:0 !important;
        z-index:1000 !important;
        overflow:visible !important;
      }

      #nav .mobile-nav-toggle-final{
        display:flex !important;
        width:100% !important;
        min-height:58px !important;
        align-items:center !important;
        justify-content:space-between !important;
        padding:0 18px !important;
        margin:0 !important;
        border:1px solid #e2e8e4 !important;
        border-radius:16px !important;
        background:#fff !important;
        color:#14532d !important;
        font-size:20px !important;
        font-weight:800 !important;
        box-shadow:0 4px 18px rgba(15,23,42,.08) !important;
      }

      #nav .mobile-nav-left-final{
        display:flex !important;
        align-items:center !important;
        gap:14px !important;
      }

      #nav .mobile-nav-icon-final{
        font-size:28px !important;
        line-height:1 !important;
      }

      #nav #menuToggle{
        display:none !important;
      }

      #nav .nav-dropdown{
        display:block !important;
        width:100% !important;
        position:static !important;
      }

      #nav #menuPanel{
        display:none !important;
        position:static !important;
        width:100% !important;
        max-height:58vh !important;
        overflow-y:auto !important;
        margin-top:8px !important;
        padding:7px !important;
        background:#fff !important;
        border:1px solid #e2e8e4 !important;
        border-radius:14px !important;
        box-shadow:0 10px 28px rgba(15,23,42,.12) !important;
      }

      #nav.mobile-nav-open #menuPanel{
        display:flex !important;
        flex-direction:column !important;
      }

      #nav.mobile-nav-open #menuPanel button[data-page]{
        display:flex !important;
        width:100% !important;
        min-height:44px !important;
        align-items:center !important;
        justify-content:flex-start !important;
        margin:3px 0 !important;
        padding:10px 13px !important;
        border-radius:10px !important;
        white-space:normal !important;
        text-align:left !important;
      }

      #nav.mobile-nav-open #menuPanel button[data-page].active{
        background:#ecfdf3 !important;
        color:#14532d !important;
        font-weight:800 !important;
      }
    }

    @media(min-width:701px){
      #nav .mobile-nav-toggle-final{
        display:none !important;
      }
    }
  `;

  document.head.appendChild(style);
})();

/* =========================================================
   FINAL MOBILE MENU SIZE — COMPACT LEFT DROPDOWN
   ========================================================= */
(function(){
  const style=document.createElement("style");

  style.textContent=`
    @media(max-width:700px){

      #nav{
        display:block !important;
        padding:8px 12px !important;
        position:sticky !important;
        top:0 !important;
        z-index:1000 !important;
      }

      #nav .mobile-nav-toggle-final{
        width:300px !important;
        max-width:calc(100vw - 24px) !important;
        min-height:54px !important;
        justify-content:space-between !important;
        margin:0 !important;
      }

      #nav .nav-dropdown{
        width:300px !important;
        max-width:calc(100vw - 24px) !important;
        position:relative !important;
        display:block !important;
      }

      #nav #menuPanel{
        position:absolute !important;
        top:calc(100% + 8px) !important;
        left:0 !important;
        width:300px !important;
        max-width:calc(100vw - 24px) !important;
        max-height:60vh !important;
        overflow-y:auto !important;
        margin:0 !important;
        padding:7px !important;
        border-radius:14px !important;
        background:#fff !important;
        box-shadow:0 12px 30px rgba(15,23,42,.18) !important;
        z-index:2000 !important;
      }

      #nav:not(.mobile-nav-open) #menuPanel{
        display:none !important;
      }

      #nav.mobile-nav-open #menuPanel{
        display:flex !important;
        flex-direction:column !important;
      }

      #nav.mobile-nav-open #menuPanel button[data-page]{
        min-height:42px !important;
        padding:9px 12px !important;
        margin:2px 0 !important;
        border-radius:9px !important;
        width:100% !important;
        font-size:14px !important;
      }
    }
  `;

  document.head.appendChild(style);
})();

/* FINAL COMPACT MOBILE MENU */
(function(){
  const s=document.createElement("style");
  s.textContent=`
    @media(max-width:700px){
      #nav .mobile-nav-toggle-final{
        width:190px !important;
        max-width:190px !important;
        min-height:42px !important;
        padding:0 11px !important;
        border-radius:10px !important;
        font-size:14px !important;
        box-shadow:0 2px 8px rgba(15,23,42,.08) !important;
      }

      #nav .mobile-nav-left-final{
        gap:8px !important;
      }

      #nav .mobile-nav-icon-final{
        font-size:19px !important;
      }

      #nav .nav-dropdown{
        width:190px !important;
        max-width:190px !important;
      }

      #nav #menuPanel{
        width:190px !important;
        max-width:190px !important;
        max-height:45vh !important;
        padding:5px !important;
        top:calc(100% + 5px) !important;
        border-radius:10px !important;
      }

      #nav.mobile-nav-open #menuPanel button[data-page]{
        min-height:34px !important;
        padding:6px 9px !important;
        margin:1px 0 !important;
        border-radius:7px !important;
        font-size:12px !important;
      }
    }
  `;
  document.head.appendChild(s);
})();
