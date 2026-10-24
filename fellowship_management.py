"""
MCN Delta South Fellowship Management blueprint.
Integration: from fellowship_management import register_fellowship_routes
             register_fellowship_routes(app, db_getter=db, user_getter=current_user)

This module expects db_getter() to return the application's database connection and
user_getter() to return the logged-in user mapping (or None). It uses the existing
fellowship_* schema created by migrate_fellowship_management.py.
"""
from datetime import datetime
import re
from functools import wraps
import os
import uuid
from flask import render_template, request, redirect, url_for, flash, abort, session, jsonify

FELLOWSHIP_SLUGS = {
    "methodist-mens-fellowship": "Methodist Men’s Fellowship",
    "methodist-womens-fellowship": "Methodist Women’s Fellowship",
    "methodist-youth-fellowship": "Methodist Youth Fellowship",
    "methodist-campus-fellowship": "Methodist Campus Fellowship (MCF)",
}
ADMIN_ROLES = {
    "Admin", "Bishop / Diocesan Executive", "Evangelism Minister",
    "Planting Officer", "Diocesan Secretary", "Circuit Coordinator",
    "Local Church Evangelism Officer", "Campus Fellowship Officer",
}
DIOCESAN_ROLES = {
    "Admin", "Bishop / Diocesan Executive", "Evangelism Minister",
    "Planting Officer", "Diocesan Secretary",
}

def register_fellowship_routes(app, db_getter, user_getter):
    def logged_user():
        user = user_getter()
        if not user:
            return None
        if hasattr(user, "keys"):
            return dict(user)
        return user

    def role_of(user):
        return str((user or {}).get("role", ""))

    def can_manage(user, fellowship, chapter=None):
        """
        Global fellowship administration is restricted to diocesan roles.
        Scoped circuit, church and campus administration must be explicitly
        implemented and validated before those roles receive write access.
        """
        if not user:
            return False

        role = role_of(user)

        if role in DIOCESAN_ROLES:
            return True

        # Do not authorize scoped roles without verified chapter boundaries.
        if not chapter:
            return False

        scope = chapter if hasattr(chapter, "get") else {}
        user_circuit = str(user.get("circuit") or "").strip().casefold()
        user_church = str(user.get("church_name") or "").strip().casefold()
        target_circuit = str(scope.get("circuit") or "").strip().casefold()
        target_church = str(scope.get("church_name") or "").strip().casefold()
        target_campus = str(scope.get("campus_name") or "").strip().casefold()
        user_campus = str(user.get("campus_name") or "").strip().casefold()

        if role == "Circuit Coordinator":
            return bool(user_circuit and target_circuit
                        and user_circuit == target_circuit)

        if role == "Local Church Evangelism Officer":
            return bool(
                user_circuit and user_church
                and target_circuit and target_church
                and user_circuit == target_circuit
                and user_church == target_church
            )

        if role == "Campus Fellowship Officer":
            return bool(user_campus and target_campus
                        and user_campus == target_campus)

        return False

    def query(sql, params=()):
        conn = db_getter()
        cur = conn.execute(sql, params)
        return cur

    def row_dict(row):
        if row is None:
            return None
        if hasattr(row, "keys"):
            return dict(row)
        return row

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not logged_user():
                # Follow the app's existing login page when available.
                return redirect("/login?next=" + request.path)
            return fn(*args, **kwargs)
        return wrapped

    def admin_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = logged_user()
            if not user:
                return redirect("/login?next=" + request.path)
            if role_of(user) not in ADMIN_ROLES:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped

    @app.get("/fellowships")
    def fellowship_directory():
        rows = query("SELECT * FROM fellowships WHERE active=1 ORDER BY name").fetchall()
        return render_template("fellowship_directory.html", fellowships=[row_dict(x) for x in rows])


    @app.get("/api/public/fellowships")
    def public_fellowships_api():
        rows = query(
            "SELECT slug, name, short_name FROM fellowships "
            "WHERE active=1 ORDER BY name"
        ).fetchall()
        return jsonify([row_dict(row) for row in rows])

    @app.post("/admin/fellowships/new")
    @login_required
    @admin_required
    def fellowship_admin_create():
        user = logged_user()
        if role_of(user) not in DIOCESAN_ROLES:
            abort(403)

        name = request.form.get("name", "").strip()
        short_name = request.form.get("short_name", "").strip()
        if not name or not short_name:
            flash("Fellowship name and short name are required.", "error")
            return redirect(url_for("fellowship_admin_directory"))

        if len(name) > 160 or len(short_name) > 40:
            flash("Fellowship name or short name is too long.", "error")
            return redirect(url_for("fellowship_admin_directory"))

        base_slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
        if not base_slug:
            flash("Enter a valid fellowship name.", "error")
            return redirect(url_for("fellowship_admin_directory"))

        slug = "fellowship-" + base_slug[:100]
        suffix = 2
        while query("SELECT 1 FROM fellowships WHERE slug=?", (slug,)).fetchone():
            slug = "fellowship-" + base_slug[:90] + "-" + str(suffix)
            suffix += 1

        conn = db_getter()
        conn.execute(
            """INSERT INTO fellowships
               (slug, name, short_name, introduction, history, vision,
                mission, objectives, active, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (
                slug, name, short_name,
                request.form.get("introduction", "").strip(),
                request.form.get("history", "").strip(),
                request.form.get("vision", "").strip(),
                request.form.get("mission", "").strip(),
                request.form.get("objectives", "").strip(),
                user.get("id"),
            ),
        )
        if hasattr(conn, "commit"):
            conn.commit()

        flash("Fellowship created as pending approval.", "success")
        return redirect(url_for("fellowship_admin_directory"))

    @app.post("/admin/fellowships/<slug>/approve")
    @login_required
    @admin_required
    def fellowship_admin_approve(slug):
        user = logged_user()
        if role_of(user) not in DIOCESAN_ROLES:
            abort(403)

        row = query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone()
        fellowship = row_dict(row)
        if not fellowship:
            abort(404)

        conn = db_getter()
        conn.execute(
            """UPDATE fellowships
               SET active=1, updated_at=CURRENT_TIMESTAMP, updated_by=?
               WHERE slug=?""",
            (user.get("id"), slug),
        )
        if hasattr(conn, "commit"):
            conn.commit()

        flash("Fellowship approved and published.", "success")
        return redirect(url_for("fellowship_admin_directory"))

    @app.get("/fellowship/<slug>")
    def fellowship_public_home(slug):
        row = query("SELECT * FROM fellowships WHERE slug=? AND active=1", (slug,)).fetchone()
        if not row:
            abort(404)
        f = row_dict(row)
        # Create short-lived signed URLs for images stored in the private bucket.
        def fellowship_image_url(path):
            if not path:
                return ""
            if str(path).startswith(("https://", "http://", "data:")):
                return path
            base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
            key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
            if not base or not key:
                return ""
            import requests
            from urllib.parse import quote
            from urllib.parse import quote
            # Existing records may reference either storage bucket.
            for bucket in ("church-media", "leadership-photos"):
                response = requests.post(
                    f"{base}/storage/v1/object/sign/{bucket}/{quote(str(path), safe='/')}",
                    headers={"Authorization": f"Bearer {key}", "apikey": key,
                             "Content-Type": "application/json"},
                    json={"expiresIn": 3600},
                    timeout=20,
                )
                if response.ok:
                    signed = response.json().get("signedURL") or response.json().get("signedUrl") or ""
                    if signed:
                        if signed.startswith(("https://", "http://")):
                            return signed
                        storage_base = base + "/storage/v1"
                        return storage_base + (signed if signed.startswith("/") else "/" + signed)
            app.logger.warning("Could not sign fellowship image from either storage bucket")
            return ""

        f["logo_display_url"] = fellowship_image_url(f.get("logo_path"))
        f["cover_display_url"] = fellowship_image_url(f.get("cover_path"))
        fid = f["id"]
        leaders = query("""SELECT * FROM fellowship_leaders
            WHERE fellowship_id=? AND active=1 ORDER BY display_order, full_name""", (fid,)).fetchall()
        announcements = query("""SELECT * FROM fellowship_announcements
            WHERE fellowship_id=? AND status='published'
            ORDER BY COALESCE(published_at, created_at) DESC LIMIT 12""", (fid,)).fetchall()
        events = query("""SELECT * FROM fellowship_events
            WHERE fellowship_id=? AND status='published'
            ORDER BY starts_at DESC LIMIT 12""", (fid,)).fetchall()
        studies = query("""SELECT * FROM fellowship_studies
            WHERE fellowship_id=? AND status='published'
            ORDER BY event_date DESC LIMIT 12""", (fid,)).fetchall()
        gallery = query("""SELECT * FROM fellowship_gallery
            WHERE fellowship_id=? AND status='published'
            ORDER BY created_at DESC LIMIT 18""", (fid,)).fetchall()
        return render_template(
            "fellowship_public.html", fellowship=f,
            leaders=[dict(row_dict(x), photo_display_url=fellowship_image_url(row_dict(x).get("photo_path"))) for x in leaders],
            announcements=[dict(row_dict(x), image_display_url=fellowship_image_url(
                row_dict(x).get("image_path")
            )) for x in announcements],
            events=[dict(row_dict(x), poster_display_url=fellowship_image_url(
                row_dict(x).get("poster_path")
            )) for x in events],
            studies=[dict(row_dict(x), media_display_url=fellowship_image_url(
                row_dict(x).get("media_path")
            )) for x in studies],
            gallery=[dict(row_dict(x), media_display_url=fellowship_image_url(row_dict(x).get("media_path"))) for x in gallery],
        )

    @app.get("/admin/fellowships")
    @login_required
    @admin_required
    def fellowship_admin_directory():
        rows = query("SELECT * FROM fellowships ORDER BY name").fetchall()
        return render_template("fellowship_admin.html", fellowships=[row_dict(x) for x in rows],
                               user=logged_user())

    @app.route("/admin/fellowships/<slug>", methods=["GET", "POST"])
    @login_required
    @admin_required
    def fellowship_admin_edit(slug):
        row = query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone()
        if not row:
            abort(404)
        fellowship = row_dict(row)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        if request.method == "POST":
            fields = ("name", "short_name", "introduction", "history", "vision", "mission",
                      "objectives")
            values = {key: request.form.get(key, "").strip() for key in fields}
            if not values["name"]:
                flash("Fellowship name is required.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

            # FELLOWSHIP_IMAGE_UPLOAD_V2: persistent image uploads to Supabase Storage.
            logo_path = fellowship.get("logo_path") or ""
            cover_path = fellowship.get("cover_path") or ""
            if request.form.get("remove_logo") == "1":
                logo_path = ""
            if request.form.get("remove_cover") == "1":
                cover_path = ""

            def upload_fellowship_image(field_name, current_path, label):
                uploaded = request.files.get(field_name)
                if not uploaded or not uploaded.filename:
                    return current_path

                filename = uploaded.filename.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
                ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                allowed = {
                    ".jpg": ("image/jpeg", lambda b: b.startswith(bytes.fromhex("FFD8FF"))),
                    ".jpeg": ("image/jpeg", lambda b: b.startswith(bytes.fromhex("FFD8FF"))),
                    ".png": ("image/png", lambda b: b.startswith(bytes.fromhex("89504E470D0A1A0A"))),
                    ".webp": ("image/webp", lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
                }
                if ext not in allowed:
                    raise ValueError(label + ": use JPG, PNG, or WebP.")
                data = uploaded.stream.read(5 * 1024 * 1024 + 1)
                if not data:
                    raise ValueError(label + ": the selected file is empty.")
                if len(data) > 5 * 1024 * 1024:
                    raise ValueError(label + ": maximum image size is 5 MB.")
                mime, signature_check = allowed[ext]
                if not signature_check(data):
                    raise ValueError(label + ": file contents do not match the image type.")

                base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
                key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
                if not base or not key:
                    raise RuntimeError("Supabase Storage credentials are not configured.")

                import requests
                path = f"fellowships/{slug}/{field_name}-{uuid.uuid4().hex}{ext}"
                response = requests.post(
                    f"{base}/storage/v1/object/leadership-photos/{path}",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "apikey": key,
                        "Content-Type": mime,
                        "x-upsert": "false",
                    },
                    data=data,
                    timeout=120,
                )
                if not response.ok:
                    try:
                        payload = response.json()
                        detail = payload.get('message') or payload.get('error') or str(payload)
                    except Exception:
                        detail = response.text
                    detail = str(detail)[:500]
                    app.logger.error('Fellowship image upload failed: HTTP %s; %s', response.status_code, detail)
                    raise RuntimeError('Image upload failed (HTTP ' + str(response.status_code) + '): ' + detail)
                return f"{base}/storage/v1/object/public/leadership-photos/{path}"
            try:
                if request.form.get("remove_logo") != "1":
                    logo_path = upload_fellowship_image("logo_file", logo_path, "Fellowship logo")
                if request.form.get("remove_cover") != "1":
                    cover_path = upload_fellowship_image("cover_file", cover_path, "Cover image")
            except Exception as exc:
                flash(str(exc), "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

            conn = db_getter()
            conn.execute("""UPDATE fellowships SET name=?, short_name=?, introduction=?, history=?,
                vision=?, mission=?, objectives=?, logo_path=?, cover_path=?, updated_at=CURRENT_TIMESTAMP,
                updated_by=? WHERE id=?""",
                (values["name"], values["short_name"], values["introduction"], values["history"],
                 values["vision"], values["mission"], values["objectives"], logo_path,
                 cover_path, user.get("id"), fellowship["id"]))
            if hasattr(conn, "commit"):
                conn.commit()
            flash("Fellowship profile saved.", "success")
            return redirect(url_for("fellowship_admin_edit", slug=slug))
        fellowship = row_dict(query("SELECT * FROM fellowships WHERE id=?", (fellowship["id"],)).fetchone())
        leaders = query("SELECT * FROM fellowship_leaders WHERE fellowship_id=? ORDER BY display_order, full_name",
                        (fellowship["id"],)).fetchall()
        announcements = query("SELECT * FROM fellowship_announcements WHERE fellowship_id=? ORDER BY created_at DESC",
                              (fellowship["id"],)).fetchall()
        events = query("SELECT * FROM fellowship_events WHERE fellowship_id=? ORDER BY starts_at DESC",
                       (fellowship["id"],)).fetchall()
        studies = query("SELECT * FROM fellowship_studies WHERE fellowship_id=? ORDER BY event_date DESC",
                        (fellowship["id"],)).fetchall()
        gallery_rows = query(
            "SELECT * FROM fellowship_gallery WHERE fellowship_id=? "
            "ORDER BY created_at DESC",
            (fellowship["id"],),
        ).fetchall()
        def admin_image_url(path):
            if not path:
                return ""
            if str(path).startswith(("https://", "http://", "data:")):
                return path
            base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
            key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
            if not base or not key:
                return ""
            import requests
            from urllib.parse import quote
            for bucket in ("church-media", "leadership-photos"):
                response = requests.post(
                    f"{base}/storage/v1/object/sign/{bucket}/{quote(str(path), safe='/')}",
                    headers={"Authorization": f"Bearer {key}", "apikey": key,
                             "Content-Type": "application/json"},
                    json={"expiresIn": 3600}, timeout=20,
                )
                if response.ok:
                    signed = response.json().get("signedURL") or response.json().get("signedUrl") or ""
                    if signed:
                        if signed.startswith(("https://", "http://")):
                            return signed
                        storage_base = base + "/storage/v1"
                        return storage_base + (signed if signed.startswith("/") else "/" + signed)
            app.logger.warning("Could not sign fellowship image from either storage bucket")
            return ""

        fellowship["logo_display_url"] = admin_image_url(fellowship.get("logo_path"))
        fellowship["cover_display_url"] = admin_image_url(fellowship.get("cover_path"))
        return render_template("fellowship_admin_edit.html", fellowship=fellowship, user=user,
            leaders=[dict(row_dict(x), photo_display_url=admin_image_url(row_dict(x).get(chr(112)+chr(104)+chr(111)+chr(116)+chr(111)+chr(95)+chr(112)+chr(97)+chr(116)+chr(104)))) for x in leaders],
            announcements=[row_dict(x) for x in announcements],
            events=[row_dict(x) for x in events],
            studies=[row_dict(x) for x in studies],
            gallery=[dict(row_dict(x), media_display_url=admin_image_url(
                row_dict(x).get("media_path")
            )) for x in gallery_rows])

    @app.post("/admin/fellowships/<slug>/leaders")
    @login_required
    @admin_required
    def fellowship_admin_add_leader(slug):
        fellowship = row_dict(query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone())
        if not fellowship:
            abort(404)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        name = request.form.get("full_name", "").strip()
        title = request.form.get("position_title", "").strip()
        photo_path = request.form.get("photo_path", "").strip()
        photo_file = request.files.get("photo_file")

        if photo_file and photo_file.filename:
            filename = photo_file.filename.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            types = {
                ".jpg": ("image/jpeg", bytes.fromhex("FFD8FF")),
                ".jpeg": ("image/jpeg", bytes.fromhex("FFD8FF")),
                ".png": ("image/png", bytes.fromhex("89504E470D0A1A0A")),
                ".webp": ("image/webp", b"RIFF"),
            }
            if ext not in types:
                flash("Leader photo must be JPG, PNG or WebP.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

            data = photo_file.stream.read(5 * 1024 * 1024 + 1)
            mime, signature = types[ext]
            if (not data or len(data) > 5 * 1024 * 1024
                    or not data.startswith(signature)
                    or (ext == ".webp" and data[8:12] != b"WEBP")):
                flash("Invalid leader photo or file exceeds 5 MB.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

            import requests
            from uuid import uuid4
            base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
            key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
            if not base or not key:
                flash("Supabase Storage credentials are missing.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

            photo_path = f"fellowships/{slug}/leader-{uuid4().hex}{ext}"
            upload = requests.post(
                f"{base}/storage/v1/object/leadership-photos/{photo_path}",
                headers={
                    "Authorization": f"Bearer {key}",
                    "apikey": key,
                    "Content-Type": mime,
                    "x-upsert": "false",
                },
                data=data,
                timeout=120,
            )
            if not upload.ok:
                flash("Leader photo upload failed (HTTP "
                      + str(upload.status_code) + ").", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

        if photo_file and photo_file.filename:
            photo_path = f"{base}/storage/v1/object/public/leadership-photos/{photo_path}"

        if not name or not title:
            flash("Leader name and position are required.", "error")
        else:
            conn = db_getter()
            conn.execute("""INSERT INTO fellowship_leaders
                (fellowship_id, full_name, position_title, biography, photo_path, term_start, term_end,
                 display_order, active, scope_type, scope_value, circuit, church_name, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                (fellowship["id"], name, title, request.form.get("biography", "").strip(),
                 photo_path, request.form.get("term_start", "").strip(),
                 request.form.get("term_end", "").strip(), int(request.form.get("display_order") or 0),
                 request.form.get("scope_type", "diocese"), request.form.get("scope_value", "").strip(),
                 request.form.get("circuit", "").strip(), request.form.get("church_name", "").strip(),
                 user.get("id")))
            if hasattr(conn, "commit"):
                conn.commit()
            flash("Fellowship leader added.", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))

    @app.post("/admin/fellowships/<slug>/content")
    @login_required
    @admin_required
    def fellowship_admin_add_content(slug):
        fellowship = row_dict(query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone())
        if not fellowship:
            abort(404)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        kind = request.form.get("kind", "announcement")
        status = request.form.get("status", "draft")
        if status not in ("draft", "published"):
            status = "draft"
        title = request.form.get("title", "").strip()
        if not title:
            flash("A title is required.", "error")
            return redirect(url_for("fellowship_admin_edit", slug=slug))

        # Direct image upload from phone to private Supabase Storage.
        media_path = request.form.get("media_path", "").strip()
        media_file = request.files.get("media_file")
        if media_file and media_file.filename:
            filename = media_file.filename.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            types = {
                ".jpg": ("image/jpeg", bytes.fromhex("FFD8FF")),
                ".jpeg": ("image/jpeg", bytes.fromhex("FFD8FF")),
                ".png": ("image/png", bytes.fromhex("89504E470D0A1A0A")),
                ".webp": ("image/webp", b"RIFF"),
            }
            if ext not in types:
                flash("Upload a JPG, PNG or WebP image.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))
            data = media_file.stream.read(5 * 1024 * 1024 + 1)
            mime, signature = types[ext]
            if (not data or len(data) > 5 * 1024 * 1024
                    or not data.startswith(signature)
                    or (ext == ".webp" and data[8:12] != b"WEBP")):
                flash("Invalid image or image exceeds 5 MB.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))
            import requests
            from uuid import uuid4
            base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
            key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
            if not base or not key:
                flash("Supabase Storage credentials are missing.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))
            media_path = f"fellowships/{slug}/media-{uuid4().hex}{ext}"
            upload = requests.post(
                f"{base}/storage/v1/object/church-media/{media_path}",
                headers={
                    "Authorization": f"Bearer {key}",
                    "apikey": key,
                    "Content-Type": mime,
                    "x-upsert": "false",
                },
                data=data,
                timeout=120,
            )
            if not upload.ok:
                flash("Image upload failed (HTTP " + str(upload.status_code) + ").", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

        common = (fellowship["id"], title)
        conn = db_getter()
        if kind == "event":
            conn.execute("""INSERT INTO fellowship_events
                (fellowship_id,title,description,event_type,venue,starts_at,ends_at,poster_path,status,
                 scope_type,scope_value,circuit,church_name,published_at,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fellowship["id"], title, request.form.get("body", "").strip(),
                 request.form.get("event_type", "programme"), request.form.get("venue", "").strip(),
                 request.form.get("starts_at", "").strip(), request.form.get("ends_at", "").strip(),
                 media_path, status, request.form.get("scope_type", "diocese"),
                 request.form.get("scope_value", "").strip(), request.form.get("circuit", "").strip(),
                 request.form.get("church_name", "").strip(),
                 datetime.utcnow().isoformat(timespec="seconds") if status == "published" else None, user.get("id")))
        elif kind in ("sermon", "bible_study"):
            conn.execute("""INSERT INTO fellowship_studies
                (fellowship_id,content_type,title,scripture_reference,preacher_or_teacher,summary,content,
                 media_path,event_date,status,scope_type,scope_value,circuit,church_name,published_at,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fellowship["id"], kind, title, request.form.get("scripture_reference", "").strip(),
                 request.form.get("teacher", "").strip(), request.form.get("summary", "").strip(),
                 request.form.get("body", "").strip(), media_path,
                 request.form.get("event_date", "").strip(), status, request.form.get("scope_type", "diocese"),
                 request.form.get("scope_value", "").strip(), request.form.get("circuit", "").strip(),
                 request.form.get("church_name", "").strip(),
                 datetime.utcnow().isoformat(timespec="seconds") if status == "published" else None, user.get("id")))
        else:
            conn.execute("""INSERT INTO fellowship_announcements
                (fellowship_id,title,body,image_path,status,scope_type,scope_value,circuit,church_name,published_at,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (fellowship["id"], title, request.form.get("body", "").strip(),
                 media_path, status, request.form.get("scope_type", "diocese"),
                 request.form.get("scope_value", "").strip(), request.form.get("circuit", "").strip(),
                 request.form.get("church_name", "").strip(),
                 datetime.utcnow().isoformat(timespec="seconds") if status == "published" else None, user.get("id")))
        if hasattr(conn, "commit"):
            conn.commit()
        flash("Content saved as " + status + ".", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))


    @app.post("/admin/fellowships/<slug>/gallery")
    @login_required
    @admin_required
    def fellowship_admin_add_gallery(slug):
        fellowship, user = management_fellowship(slug)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "draft")
        if status not in ("draft", "published"):
            status = "draft"
        if not title:
            flash("A gallery title is required.", "error")
            return redirect(url_for("fellowship_admin_edit", slug=slug))
        uploads = [
            item for item in request.files.getlist("media_files")
            if item and item.filename
        ]
        # Backward compatibility with the old single-image form.
        if not uploads:
            single = request.files.get("media_file")
            if single and single.filename:
                uploads = [single]

        if not uploads:
            flash("Choose one or more gallery images.", "error")
            return redirect(url_for("fellowship_admin_edit", slug=slug))

        conn = db_getter()
        saved = 0
        try:
            for index, uploaded in enumerate(uploads, start=1):
                media_path = management_upload_image(
                    slug, uploaded, bucket="church-media", prefix="gallery"
                )
                if not media_path:
                    continue
                photo_title = title if len(uploads) == 1 else f"{title} ({index})"
                conn.execute(
                    """INSERT INTO fellowship_gallery
                       (fellowship_id, title, description, media_path, media_type,
                        event_date, status, scope_type, scope_value, circuit,
                        church_name, created_by)
                       VALUES (?, ?, ?, ?, 'image', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fellowship["id"], photo_title, description, media_path,
                        request.form.get("event_date", "").strip(), status,
                        request.form.get("scope_type", "diocese"),
                        request.form.get("scope_value", "").strip(),
                        request.form.get("circuit", "").strip(),
                        request.form.get("church_name", "").strip(),
                        user.get("id"),
                    ),
                )
                saved += 1
            if saved == 0:
                raise RuntimeError("No gallery images were saved.")
            if hasattr(conn, "commit"):
                conn.commit()
        except Exception as exc:
            if hasattr(conn, "rollback"):
                conn.rollback()
            app.logger.exception("Fellowship multi-image gallery upload failed")
            flash("Gallery upload failed: " + str(exc), "error")
            return redirect(url_for("fellowship_admin_edit", slug=slug))

        flash(f"{saved} gallery image(s) saved as {status}.", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))

    # FELLOWSHIP_MANAGEMENT_V2
    # Every mutation checks login, admin role, fellowship scope, and row ownership.
    def management_row(table, row_id, fellowship_id):
        allowed = {
            "fellowship_leaders",
            "fellowship_gallery",
            "fellowship_announcements",
            "fellowship_events",
            "fellowship_studies",
        }
        if table not in allowed:
            abort(400)
        return query(
            f"SELECT * FROM {table} WHERE id=? AND fellowship_id=?",
            (row_id, fellowship_id),
        ).fetchone()

    def management_fellowship(slug):
        row = query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone()
        if not row:
            abort(404)
        fellowship = row_dict(row)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        return fellowship, user


    # FELLOWSHIP_COMPLETION_V3
    def management_upload_image(slug, uploaded, bucket="church-media",
                                prefix="media"):
        if not uploaded or not uploaded.filename:
            return None
        filename = uploaded.filename.rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = {
            ".jpg": ("image/jpeg", lambda b: b.startswith(bytes.fromhex("FFD8FF"))),
            ".jpeg": ("image/jpeg", lambda b: b.startswith(bytes.fromhex("FFD8FF"))),
            ".png": ("image/png", lambda b: b.startswith(bytes.fromhex("89504E470D0A1A0A"))),
            ".webp": ("image/webp", lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
        }
        if ext not in allowed:
            raise ValueError("Use a JPG, PNG, or WebP image.")
        data = uploaded.stream.read(5 * 1024 * 1024 + 1)
        mime, signature_check = allowed[ext]
        if not data or len(data) > 5 * 1024 * 1024 or not signature_check(data):
            raise ValueError("Invalid image or image exceeds 5 MB.")
        base = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
        key = (os.environ.get("SUPABASE_SECRET_KEY") or "").strip()
        if not base or not key:
            raise RuntimeError("Supabase Storage credentials are missing.")
        import requests
        path = f"fellowships/{slug}/{prefix}-{uuid.uuid4().hex}{ext}"
        response = requests.post(
            f"{base}/storage/v1/object/{bucket}/{path}",
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": mime,
                "x-upsert": "false",
            },
            data=data,
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(
                f"Supabase upload failed (HTTP {response.status_code})."
            )
        if bucket == "leadership-photos":
            return f"{base}/storage/v1/object/public/{bucket}/{path}"
        return path

    def management_update(table, row_id, slug):
        fellowship, user = management_fellowship(slug)
        allowed_columns = {
            "fellowship_leaders": {
                "full_name", "position_title", "biography", "term_start",
                "term_end", "display_order", "active", "scope_type",
                "scope_value", "circuit", "church_name", "photo_path",
            },
            "fellowship_gallery": {
                "title", "description", "event_date", "status",
                "scope_type", "scope_value", "circuit", "church_name",
                "media_path",
            },
            "fellowship_announcements": {
                "title", "body", "status", "scope_type", "scope_value",
                "circuit", "church_name", "image_path",
            },
            "fellowship_events": {
                "title", "description", "event_type", "venue", "starts_at",
                "ends_at", "status", "scope_type", "scope_value", "circuit",
                "church_name", "poster_path",
            },
            "fellowship_studies": {
                "content_type", "title", "scripture_reference",
                "preacher_or_teacher", "summary", "content", "event_date",
                "status", "scope_type", "scope_value", "circuit",
                "church_name", "media_path",
            },
        }
        row = management_row(table, row_id, fellowship["id"])
        if not row:
            abort(404)

        columns = allowed_columns[table]
        values = {}
        for column in columns:
            if column not in request.form:
                continue
            value = request.form.get(column, "").strip()
            if column == "status" and value not in ("draft", "published"):
                value = "draft"
            if column == "active":
                value = 1 if value in ("1", "true", "on", "yes") else 0
            if column == "display_order":
                try:
                    value = int(value or 0)
                except ValueError:
                    value = 0
            values[column] = value

        upload_fields = {
            "fellowship_leaders": ("photo_file", "photo_path", "leadership-photos", "leader"),
            "fellowship_gallery": ("media_file", "media_path", "church-media", "gallery"),
            "fellowship_announcements": ("image_file", "image_path", "church-media", "announcement"),
            "fellowship_events": ("poster_file", "poster_path", "church-media", "event-poster"),
            "fellowship_studies": ("media_file", "media_path", "church-media", "study"),
        }
        file_field, db_field, bucket, prefix = upload_fields[table]
        uploaded = request.files.get(file_field)
        if uploaded and uploaded.filename:
            try:
                new_path = management_upload_image(
                    slug, uploaded, bucket=bucket, prefix=prefix
                )
            except Exception as exc:
                flash(str(exc), "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))
            values[db_field] = new_path

        if table == "fellowship_gallery":
            values["media_type"] = "image"

        if table == "fellowship_leaders":
            if not values.get("full_name", row["full_name"]) or not values.get(
                "position_title", row["position_title"]
            ):
                flash("Leader name and position are required.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))

        if not values:
            flash("No editable fields were submitted.", "error")
            return redirect(url_for("fellowship_admin_edit", slug=slug))

        values["updated_by"] = (user or {}).get("id")
        assignments = ", ".join(f"{column}=?" for column in values)
        params = list(values.values())
        params.extend([row_id, fellowship["id"]])

        conn = db_getter()
        # updated_by is already included in values and assignments.
        # Do not assign the same column twice in PostgreSQL.
        assignments += ", updated_at=CURRENT_TIMESTAMP"
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE id=? AND fellowship_id=?",
            tuple(params),
        )
        if hasattr(conn, "commit"):
            conn.commit()

        flash("Fellowship record updated.", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))

    def management_delete(table, row_id, slug):
        fellowship, user = management_fellowship(slug)
        row = management_row(table, row_id, fellowship["id"])
        if not row:
            abort(404)

        conn = db_getter()
        conn.execute(
            f"DELETE FROM {table} WHERE id=? AND fellowship_id=?",
            (row_id, fellowship["id"]),
        )
        if hasattr(conn, "commit"):
            conn.commit()
        flash("Fellowship record deleted.", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))

    @app.post("/admin/fellowships/<slug>/leaders/<int:row_id>/edit")
    @login_required
    @admin_required
    def fellowship_admin_edit_leader(slug, row_id):
        return management_update("fellowship_leaders", row_id, slug)

    @app.post("/admin/fellowships/<slug>/leaders/<int:row_id>/delete")
    @login_required
    @admin_required
    def fellowship_admin_delete_leader(slug, row_id):
        return management_delete("fellowship_leaders", row_id, slug)

    @app.post("/admin/fellowships/<slug>/gallery/<int:row_id>/edit")
    @login_required
    @admin_required
    def fellowship_admin_edit_gallery(slug, row_id):
        return management_update("fellowship_gallery", row_id, slug)

    @app.post("/admin/fellowships/<slug>/gallery/<int:row_id>/delete")
    @login_required
    @admin_required
    def fellowship_admin_delete_gallery(slug, row_id):
        return management_delete("fellowship_gallery", row_id, slug)

    @app.post("/admin/fellowships/<slug>/announcements/<int:row_id>/edit")
    @login_required
    @admin_required
    def fellowship_admin_edit_announcement(slug, row_id):
        return management_update("fellowship_announcements", row_id, slug)

    @app.post("/admin/fellowships/<slug>/announcements/<int:row_id>/delete")
    @login_required
    @admin_required
    def fellowship_admin_delete_announcement(slug, row_id):
        return management_delete("fellowship_announcements", row_id, slug)

    @app.post("/admin/fellowships/<slug>/events/<int:row_id>/edit")
    @login_required
    @admin_required
    def fellowship_admin_edit_event(slug, row_id):
        return management_update("fellowship_events", row_id, slug)

    @app.post("/admin/fellowships/<slug>/events/<int:row_id>/delete")
    @login_required
    @admin_required
    def fellowship_admin_delete_event(slug, row_id):
        return management_delete("fellowship_events", row_id, slug)

    @app.post("/admin/fellowships/<slug>/studies/<int:row_id>/edit")
    @login_required
    @admin_required
    def fellowship_admin_edit_study(slug, row_id):
        return management_update("fellowship_studies", row_id, slug)

    @app.post("/admin/fellowships/<slug>/studies/<int:row_id>/delete")
    @login_required
    @admin_required
    def fellowship_admin_delete_study(slug, row_id):
        return management_delete("fellowship_studies", row_id, slug)
