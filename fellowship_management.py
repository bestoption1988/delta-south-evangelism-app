"""
MCN Delta South Fellowship Management blueprint.
Integration: from fellowship_management import register_fellowship_routes
             register_fellowship_routes(app, db_getter=db, user_getter=current_user)

This module expects db_getter() to return the application's database connection and
user_getter() to return the logged-in user mapping (or None). It uses the existing
fellowship_* schema created by migrate_fellowship_management.py.
"""
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, abort, session

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

    @app.get("/fellowship/<slug>")
    def fellowship_public_home(slug):
        if slug not in FELLOWSHIP_SLUGS:
            abort(404)
        row = query("SELECT * FROM fellowships WHERE slug=? AND active=1", (slug,)).fetchone()
        if not row:
            abort(404)
        f = row_dict(row)
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
            leaders=[row_dict(x) for x in leaders],
            announcements=[row_dict(x) for x in announcements],
            events=[row_dict(x) for x in events],
            studies=[row_dict(x) for x in studies],
            gallery=[row_dict(x) for x in gallery],
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
        if slug not in FELLOWSHIP_SLUGS:
            abort(404)
        row = query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone()
        if not row:
            abort(404)
        fellowship = row_dict(row)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        if request.method == "POST":
            fields = ("name", "short_name", "introduction", "history", "vision", "mission",
                      "objectives", "logo_path", "cover_path")
            values = {key: request.form.get(key, "").strip() for key in fields}
            if not values["name"]:
                flash("Fellowship name is required.", "error")
                return redirect(url_for("fellowship_admin_edit", slug=slug))
            conn = db_getter()
            conn.execute("""UPDATE fellowships SET name=?, short_name=?, introduction=?, history=?,
                vision=?, mission=?, objectives=?, logo_path=?, cover_path=?, updated_at=CURRENT_TIMESTAMP,
                updated_by=? WHERE id=?""",
                (values["name"], values["short_name"], values["introduction"], values["history"],
                 values["vision"], values["mission"], values["objectives"], values["logo_path"],
                 values["cover_path"], user.get("id"), fellowship["id"]))
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
        return render_template("fellowship_admin_edit.html", fellowship=fellowship, user=user,
            leaders=[row_dict(x) for x in leaders],
            announcements=[row_dict(x) for x in announcements],
            events=[row_dict(x) for x in events],
            studies=[row_dict(x) for x in studies])

    @app.post("/admin/fellowships/<slug>/leaders")
    @login_required
    @admin_required
    def fellowship_admin_add_leader(slug):
        if slug not in FELLOWSHIP_SLUGS:
            abort(404)
        fellowship = row_dict(query("SELECT * FROM fellowships WHERE slug=?", (slug,)).fetchone())
        if not fellowship:
            abort(404)
        user = logged_user()
        if not can_manage(user, fellowship):
            abort(403)
        name = request.form.get("full_name", "").strip()
        title = request.form.get("position_title", "").strip()
        if not name or not title:
            flash("Leader name and position are required.", "error")
        else:
            conn = db_getter()
            conn.execute("""INSERT INTO fellowship_leaders
                (fellowship_id, full_name, position_title, biography, photo_path, term_start, term_end,
                 display_order, active, scope_type, scope_value, circuit, church_name, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                (fellowship["id"], name, title, request.form.get("biography", "").strip(),
                 request.form.get("photo_path", "").strip(), request.form.get("term_start", "").strip(),
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
        if slug not in FELLOWSHIP_SLUGS:
            abort(404)
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
                 request.form.get("media_path", "").strip(), status, request.form.get("scope_type", "diocese"),
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
                 request.form.get("body", "").strip(), request.form.get("media_path", "").strip(),
                 request.form.get("event_date", "").strip(), status, request.form.get("scope_type", "diocese"),
                 request.form.get("scope_value", "").strip(), request.form.get("circuit", "").strip(),
                 request.form.get("church_name", "").strip(),
                 datetime.utcnow().isoformat(timespec="seconds") if status == "published" else None, user.get("id")))
        else:
            conn.execute("""INSERT INTO fellowship_announcements
                (fellowship_id,title,body,image_path,status,scope_type,scope_value,circuit,church_name,published_at,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (fellowship["id"], title, request.form.get("body", "").strip(),
                 request.form.get("media_path", "").strip(), status, request.form.get("scope_type", "diocese"),
                 request.form.get("scope_value", "").strip(), request.form.get("circuit", "").strip(),
                 request.form.get("church_name", "").strip(),
                 datetime.utcnow().isoformat(timespec="seconds") if status == "published" else None, user.get("id")))
        if hasattr(conn, "commit"):
            conn.commit()
        flash("Content saved as " + status + ".", "success")
        return redirect(url_for("fellowship_admin_edit", slug=slug))
