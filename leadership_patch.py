from pathlib import Path

p = Path("app.py")
s = p.read_text()

titles = [
    "Prelate", "Archbishop", "Bishop, Delta South Diocese",
    "Evangelism Minister", "Lay President",
    "Men Fellowship President", "Women Fellowship President",
    "Youth Fellowship President"
]

if "LEADERSHIP_TITLES =" not in s:
    marker = "APP_VERSION = "
    i = s.find(marker)
    if i < 0:
        raise SystemExit("Cannot find APP_VERSION")
    block = "LEADERSHIP_TITLES = " + repr(titles) + "\n\n"
    s = s[:i] + block + s[i:]

if "def admin_leadership():" not in s:
    marker = '@app.get("/")\ndef public_home():'
    i = s.find(marker)
    if i < 0:
        raise SystemExit("Cannot find public homepage route")

    route = '''
@app.route("/admin/leadership", methods=["GET", "POST"])
@page_login_required
def admin_leadership():
    user = current_user()
    if not user or user["role"] != "Admin":
        return "Administrator access required.", 403

    message = ""
    error = ""
    if request.method == "POST":
        try:
            action = request.form.get("action", "save")
            if action == "delete":
                db().execute(
                    "UPDATE leadership_profiles SET active=0 WHERE id=?",
                    (request.form.get("id", type=int),)
                )
                db().commit()
                message = "Profile hidden."
            elif action == "logo":
                f = request.files.get("logo")
                if not f or not f.filename:
                    raise ValueError("Choose the church logo.")
                ext = f.filename.rsplit(".", 1)[-1].lower()
                if ext not in {"png", "jpg", "jpeg", "webp"}:
                    raise ValueError("Use PNG, JPG, JPEG or WEBP.")
                folder = os.path.join(ROOT, "static", "uploads", "leadership")
                os.makedirs(folder, exist_ok=True)
                f.save(os.path.join(folder, "mcn-logo.png"))
                message = "Logo uploaded."
            else:
                title = request.form.get("title", "").strip()
                name = request.form.get("full_name", "").strip()
                bio = request.form.get("biography", "").strip()
                order = request.form.get("display_order", type=int) or 1
                active = int(request.form.get("active") == "1")
                if title not in LEADERSHIP_TITLES:
                    raise ValueError("Choose a valid leadership position.")
                if len(name) > 160 or len(bio) > 2500:
                    raise ValueError("Name or biography is too long.")

                photo_path = None
                f = request.files.get("photo")
                if f and f.filename:
                    ext = f.filename.rsplit(".", 1)[-1].lower()
                    if ext not in {"png", "jpg", "jpeg", "webp"}:
                        raise ValueError("Use PNG, JPG, JPEG or WEBP.")
                    folder = os.path.join(ROOT, "static", "uploads", "leadership")
                    os.makedirs(folder, exist_ok=True)
                    filename = secrets.token_hex(8) + "." + ext
                    f.save(os.path.join(folder, filename))
                    photo_path = "uploads/leadership/" + filename

                pid = request.form.get("id", type=int)
                if pid:
                    db().execute(
                        """UPDATE leadership_profiles SET title=?,full_name=?,
                           biography=?,display_order=?,active=?,updated_at=CURRENT_TIMESTAMP,
                           updated_by=? WHERE id=?""",
                        (title,name,bio,order,active,user["id"],pid)
                    )
                    if photo_path:
                        db().execute(
                            "UPDATE leadership_profiles SET photo_path=? WHERE id=?",
                            (photo_path,pid)
                        )
                    message = "Profile updated."
                else:
                    db().execute(
                        """INSERT INTO leadership_profiles
                           (title,full_name,biography,photo_path,display_order,active,updated_by)
                           VALUES (?,?,?,?,?,?,?)""",
                        (title,name,bio,photo_path or "",order,active,user["id"])
                    )
                    message = "Profile added."
                db().commit()
        except ValueError as e:
            error = str(e)
        except Exception:
            db().rollback()
            app.logger.exception("Leadership update failed")
            error = "Unable to save changes."

    profiles = db().execute(
        "SELECT * FROM leadership_profiles ORDER BY display_order,title"
    ).fetchall()
    return render_template(
        "leadership_admin.html", profiles=profiles,
        titles=LEADERSHIP_TITLES, message=message, error=error
    )


'''
    s = s[:i] + route + s[i:]

old = '''@app.get("/")
def public_home():
    """Public diocesan homepage; no login required."""
    return render_template("public_home.html")'''
new = '''@app.get("/")
def public_home():
    """Public diocesan homepage; no login required."""
    profiles = db().execute(
        "SELECT * FROM leadership_profiles WHERE active=1 ORDER BY display_order,title"
    ).fetchall()
    return render_template(
        "public_home.html", leadership_profiles=profiles,
        leadership_titles=LEADERSHIP_TITLES
    )'''
if old in s:
    s = s.replace(old, new, 1)
elif "leadership_profiles=profiles" not in s:
    raise SystemExit("Homepage route differs; refusing to guess.")

marker = "    # Account registration requests:"
if "for position, title in enumerate(LEADERSHIP_TITLES" not in s:
    i = s.find(marker)
    if i < 0:
        raise SystemExit("Cannot find database initialization marker")
    seed = '''    for position, title in enumerate(LEADERSHIP_TITLES, 1):
        db().execute(
            """INSERT INTO leadership_profiles
               (title,full_name,biography,photo_path,display_order,active)
               SELECT ?, '', '', '', ?, 1
               WHERE NOT EXISTS (
                   SELECT 1 FROM leadership_profiles WHERE title=?
               )""",
            (title, position, title)
        )
    db().commit()

'''
    s = s[:i] + seed + s[i:]

p.write_text(s)
print("Leadership patch applied.")
