from pathlib import Path
from datetime import datetime
import shutil
import sys

app_path = Path("app.py")
js_path = Path("static/app.js")

app = app_path.read_text()
js = js_path.read_text()

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one matching section, found {count}"
        )
    return source.replace(old, new, 1)

# Confirm all insertion points before editing.
required = [
    (app, '@app.get("/api/users")'),
    (app, '@app.post("/api/users")'),
    (app, '@app.put("/api/users/<int:uid>")'),
    (js, 'users:[["username","Username","text"]'),
    (js, 'async function openForm()'),
    (js, 'document.querySelectorAll("[data-toggle-user]")'),
]

for source, fragment in required:
    if fragment not in source:
        sys.exit(f"STOP: Expected source code not found: {fragment}")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(app_path, f"app.py.before-member-linking-{stamp}.bak")
shutil.copy2(js_path, f"static/app.js.before-member-linking-{stamp}.bak")

try:
    # Admin-only endpoint. Returns official membership records and current links.
    route = '''@app.get("/api/user-linkable-members")
@login_required
def user_linkable_members():
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    return jsonify(rows("""
        SELECT m.id, m.member_id, m.full_name, m.circuit, m.church_name,
               u.id AS linked_user_id, u.username AS linked_username
        FROM members m
        LEFT JOIN users u ON u.member_id = m.id
        ORDER BY m.full_name
    """))


'''

    app = replace_once(
        app,
        '@app.get("/api/users")',
        route + '@app.get("/api/users")',
        "membership selector endpoint",
    )

    # Include linked membership information in the Admin's user list.
    old = 'return jsonify(rows("SELECT id,username,role,circuit,church_name,active,must_change_password,created_at FROM users ORDER BY username"))'
    new = '''return jsonify(rows("""
        SELECT u.id, u.username, u.role, u.circuit, u.church_name,
               u.active, u.must_change_password, u.created_at,
               u.member_id, m.full_name AS member_name,
               m.member_id AS official_member_code
        FROM users u
        LEFT JOIN members m ON m.id = u.member_id
        ORDER BY u.username
    """))'''
    app = replace_once(app, old, new, "user listing")

    # Replace account creation with validated membership linking.
    start = app.index('@app.post("/api/users")')
    end = app.index('@app.put("/api/users/<int:uid>")', start)

    create_route = '''@app.post("/api/users")
@login_required
def create_user():
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "Member"

    if len(username) < 3 or len(password) < 8:
        return jsonify({
            "error": "Username must be at least 3 characters and password at least 8 characters."
        }), 400

    if role not in ROLES:
        return jsonify({"error": "Invalid role."}), 400

    try:
        member_id = int(data.get("member_id") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Select a valid official member record."}), 400

    if member_id <= 0:
        return jsonify({"error": "Select an official member record for this account."}), 400

    conn = db()
    linked = conn.execute(
        "SELECT id, circuit, church_name FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not linked:
        return jsonify({"error": "The selected member record was not found."}), 400

    existing = conn.execute(
        "SELECT id, username FROM users WHERE member_id=?",
        (member_id,)
    ).fetchone()

    if existing:
        return jsonify({
            "error": f"This member is already linked to account: {existing['username']}."
        }), 400

    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()

    # Preserve the established role-assignment rules.
    if role in DIOSAN_ROLES:
        circuit = ""
        church_name = ""
    elif role == "Circuit Coordinator":
        circuit = linked["circuit"] or circuit
        church_name = ""
    elif role in {"Member", "Local Church Evangelism Officer"}:
        circuit = linked["circuit"] or circuit
        church_name = linked["church_name"] or church_name

    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error:
        return jsonify({"error": assignment_error}), 400

    try:
        cur = conn.execute("""
            INSERT INTO users(
                username, password, role, circuit, church_name,
                active, must_change_password, created_at, member_id
            ) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
        """, (
            username,
            generate_password_hash(password),
            role,
            circuit,
            church_name,
            datetime.now().isoformat(timespec="seconds"),
            member_id
        ))
        conn.commit()
        audit("CREATE", "users", cur.lastrowid, json.dumps({
            "username": username,
            "role": role,
            "member_id": member_id
        }))
        return jsonify({"id": cur.lastrowid, "ok": True}), 201

    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "That username or membership link already exists."}), 400


'''
    app = app[:start] + create_route + app[end:]

    # Allow an Admin to attach or change a link on an existing account.
    start = app.index('@app.put("/api/users/<int:uid>")')
    end = app.index('@app.delete("/api/users/<int:uid>")', start)

    update_route = '''@app.put("/api/users/<int:uid>")
@login_required
def update_user(uid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    conn = db()
    target = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not target:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(force=True) or {}
    role = data.get("role", target["role"]) or "Member"
    circuit = (data.get("circuit", target["circuit"]) or "").strip()
    church_name = (data.get("church_name", target["church_name"]) or "").strip()

    if role not in ROLES:
        return jsonify({"error": "Invalid role."}), 400

    member_id = target["member_id"]
    if "member_id" in data:
        try:
            member_id = int(data.get("member_id") or 0)
        except (ValueError, TypeError):
            return jsonify({"error": "Select a valid official member record."}), 400

        if member_id <= 0:
            return jsonify({"error": "An account must remain linked to an official member record."}), 400

    linked = conn.execute(
        "SELECT id, circuit, church_name FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not linked:
        return jsonify({"error": "The selected member record was not found."}), 400

    existing = conn.execute(
        "SELECT id, username FROM users WHERE member_id=? AND id<>?",
        (member_id, uid)
    ).fetchone()

    if existing:
        return jsonify({
            "error": f"This member is already linked to account: {existing['username']}."
        }), 400

    if role in DIOSAN_ROLES:
        circuit = ""
        church_name = ""
    elif role == "Circuit Coordinator":
        circuit = linked["circuit"] or circuit
        church_name = ""
    elif role in {"Member", "Local Church Evangelism Officer"}:
        circuit = linked["circuit"] or circuit
        church_name = linked["church_name"] or church_name

    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error:
        return jsonify({"error": assignment_error}), 400

    conn.execute("""
        UPDATE users
        SET role=?, circuit=?, church_name=?, member_id=?
        WHERE id=?
    """, (role, circuit, church_name, member_id, uid))
    conn.commit()

    audit("USER_ASSIGNMENT_UPDATED", "users", uid, json.dumps({
        "role": role,
        "circuit": circuit,
        "church_name": church_name,
        "member_id": member_id
    }))
    return jsonify({"ok": True})


'''
    app = app[:start] + update_route + app[end:]

    # Add Member and the official-member selector to the account form.
    old = 'users:[["username","Username","text"],["password","Temporary password (min 8 characters)","password"],["role","Role","select",["Admin","Bishop / Diocesan Executive","Evangelism Minister","Planting Officer","Diocesan Secretary","Circuit Coordinator","Local Church Evangelism Officer","Finance Officer","Auditor"]],["circuit","Assigned circuit","select",["","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Assigned church (optional)","text"]]'
    new = 'users:[["username","Username","text"],["password","Temporary password (min 8 characters)","password"],["role","Role","select",["Member","Admin","Bishop / Diocesan Executive","Evangelism Minister","Planting Officer","Diocesan Secretary","Circuit Coordinator","Local Church Evangelism Officer","Finance Officer","Auditor"]],["member_id","Link official church member","select",[]],["circuit","Assigned circuit","select",["","Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]],["church_name","Assigned church (optional)","text"]]'
    js = replace_once(js, old, new, "user form schema")

    # Populate the membership selector dynamically for account creation.
    marker = 'let churchOptions=[];'
    insertion = '''let userMemberOptions=[];
if(current==="users"){
  try{
    userMemberOptions=await api("/api/user-linkable-members");
  }catch(e){
    alert("Unable to load official membership records: "+e.message);
    return;
  }
}
'''
    js = replace_once(js, marker, insertion + marker, "user membership options")

    # Render membership names as readable options rather than numeric IDs.
    old = 'if(type==="select"){let choices=key==="circuit"?circuitOptions:opts;'
    new = 'if(type==="select"){let choices=key==="circuit"?circuitOptions:opts;'
    # Insert a special case immediately after the generic select choices are initialized.
    js = replace_once(
        js,
        'let choices=key==="circuit"?circuitOptions:opts;',
        '''let choices=key==="circuit"?circuitOptions:opts;
if(current==="users"&&key==="member_id"){
  control=`<select name="member_id" required><option value="">Select official member</option>${userMemberOptions.filter(m=>!m.linked_user_id).map(m=>`<option value="${m.id}">${esc(m.full_name)} — ${esc(m.member_id||"No member code")} · ${esc(m.church_name||"No church")}</option>`).join("")}</select>`;
  return `<div class="field"><label>${label}</label>${control}</div>`;
}''',
        "membership selector rendering",
    )

    # Add a Link Member action beside Edit Access for existing accounts.
    js = replace_once(
        js,
        '${current==="users"&&me.role==="Admin"?`<button class="secondary" data-edit-user="${r.id}">Edit access</button>',
        '${current==="users"&&me.role==="Admin"?`<button class="secondary" data-link-user="${r.id}">Link member</button><button class="secondary" data-edit-user="${r.id}">Edit access</button>',
        "existing account link button",
    )

    # Existing-account linking workflow. Admin selects a member by number in a numbered list.
    marker = 'document.querySelectorAll("[data-toggle-user]")'
    handler = '''document.querySelectorAll("[data-link-user]").forEach(b=>b.onclick=async()=>{
  const row=records.find(r=>String(r.id)===String(b.dataset.linkUser));
  if(!row)return;
  try{
    const members=await api("/api/user-linkable-members");
    const choices=members.filter(m=>!m.linked_user_id||Number(m.linked_user_id)===Number(row.id));
    if(!choices.length)return alert("No available membership records were found.");
    const listing=choices.map((m,i)=>`${i+1}. ${m.full_name} | ${m.member_id||"No code"} | ${m.church_name||"No church"}${Number(m.linked_user_id)===Number(row.id)?" (currently linked)":""}`).join("\\n");
    const answer=prompt("Choose the official member number for "+row.username+":\\n\\n"+listing+"\\n\\nEnter the number from the list:");
    if(answer===null)return;
    const index=Number(answer)-1;
    if(!Number.isInteger(index)||index<0||index>=choices.length)return alert("Invalid selection.");
    const selected=choices[index];
    await api(`/api/users/${row.id}`,{method:"PUT",body:JSON.stringify({member_id:selected.id})});
    alert("Membership linked successfully. The account role has not been changed.");
    await loadTable();
  }catch(e){alert(e.message)}
});
'''
    js = replace_once(js, marker, handler + marker, "existing-account linking handler")

    # Commit edits only after all replacements succeeded.
    app_path.write_text(app)
    js_path.write_text(js)

    print("Patch applied.")
    print("Backups:")
    print(f"  app.py.before-member-linking-{stamp}.bak")
    print(f"  static/app.js.before-member-linking-{stamp}.bak")

except Exception as exc:
    print(f"PATCH STOPPED: {exc}")
    print("No partial patch was intentionally written.")
    sys.exit(1)
