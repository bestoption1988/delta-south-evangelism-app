from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

path = Path("templates/member_dashboard.html")

if not path.exists():
    sys.exit("ERROR: Member dashboard template not found.")

original = path.read_text()
updated = original

# Back up the original template without overwriting previous backups.
backup = path.with_name(
    path.name + ".before-loading-fix-" +
    datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak"
)
shutil.copy2(path, backup)

# Replace the summary-card loader with one that always resolves
# the Loading state, including when the account is not linked.
pattern = re.compile(
    r'async function loadMemberChurch\(\)\s*\{.*?'
    r'\n\}\s*\n\s*loadMemberChurch\(\);',
    re.S
)

replacement = r'''async function loadMemberChurch(){
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value || "—";
  };

  const setSummary = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value || "—";
  };

  try {
    const r = await fetch("/api/member/me");
    const data = await r.json();

    if (!r.ok) {
      const message = data.error ||
        "Unable to load membership information.";

      setSummary("portal-member-id", "Not linked");
      setSummary("portal-church", "Not linked");
      setSummary("portal-circuit", "Not linked");
      setSummary("portal-fellowship", "Not linked");

      console.warn("Member summary:", message);
      return;
    }

    const m = data.member || data;

    setSummary("portal-member-id", m.member_id);
    setSummary("portal-church", m.church_name);
    setSummary("portal-circuit", m.circuit);
    setSummary("portal-fellowship", m.fellowship);

    set("church-page-name", m.church_name);
    set("church-page-circuit", m.circuit);
    set("church-page-fellowship", m.fellowship);
    set("church-page-position", m.role_position || "Member");
    set("church-page-member-id", m.member_id);

  } catch (e) {
    ["portal-member-id", "portal-church",
     "portal-circuit", "portal-fellowship"].forEach(id => {
      setSummary(id, "Unavailable");
    });
    console.error("Member summary:", e);
  }
}

loadMemberChurch();'''

updated, count = pattern.subn(lambda _: replacement, updated, count=1)

if count != 1:
    print("ERROR: Could not safely locate the summary-card loader.")
    print("Original template has NOT been changed.")
    sys.exit(1)

# Make ID-card errors visible instead of leaving a blank card.
old = '''  } catch(e) {
    console.error("ID card:",e);
  }
}

loadMemberIDCard();'''

new = '''  } catch(e) {
    console.error("ID card:",e);
    const fields = [
      "id-full-name", "id-member-id", "id-position",
      "id-church", "id-circuit", "id-fellowship"
    ];
    fields.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = "Unavailable";
    });
    const placeholder = document.getElementById("id-photo-placeholder");
    if (placeholder) {
      placeholder.style.display = "block";
      placeholder.textContent = "Membership record unavailable";
    }
  }
}

loadMemberIDCard();'''

if old not in updated:
    print("ERROR: Could not safely locate the ID-card error handler.")
    print("Original template has NOT been changed.")
    sys.exit(1)

updated = updated.replace(old, new, 1)

# Preserve the original file if any unexpected write error occurs.
try:
    path.write_text(updated)
except Exception:
    shutil.copy2(backup, path)
    raise

print("Member Portal loading fix applied.")
print("Backup preserved:", backup)
