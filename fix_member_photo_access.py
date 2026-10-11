from pathlib import Path

path = Path("app.py")
source = path.read_text(encoding="utf-8")

start_marker = '@app.get("/api/member-registration-photo/<path:filename>")'
end_marker = '@app.get("/api/membership-statistics")'

start = source.find(start_marker)
end = source.find(end_marker, start + len(start_marker))

if start < 0 or end < 0:
    raise SystemExit("ERROR: Could not locate the expected photo route. No changes made.")

new_route = '''@app.get("/api/member-registration-photo/<path:filename>")
@login_required
def view_member_registration_photo(filename):
    u = current_user()

    safe_name = os.path.basename(filename)
    if safe_name != filename or not safe_name:
        return jsonify({"error": "Invalid photo filename."}), 400

    allowed_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Auditor"
    }

    if u["role"] == "Member":
        if not u["member_id"]:
            return jsonify({
                "error": "Member account is not linked to a membership record."
            }), 403

        member = db().execute(
            "SELECT passport_photo FROM members WHERE id=?",
            (u["member_id"],)
        ).fetchone()

        if not member:
            return jsonify({"error": "Member record not found."}), 404

        own_photo = os.path.basename(member["passport_photo"] or "")
        if not own_photo or own_photo != safe_name:
            return jsonify({
                "error": "You are not authorized to view this photo."
            }), 403

    elif u["role"] not in allowed_roles:
        return jsonify({
            "error": "You are not authorized to view member photos."
        }), 403

    photo_path = os.path.join(MEMBER_PHOTO_DIR, safe_name)

    if not os.path.isfile(photo_path):
        return jsonify({"error": "Photo not found."}), 404

    return send_file(
        photo_path,
        conditional=True,
        max_age=0
    )


'''

path.write_text(
    source[:start] + new_route + source[end:],
    encoding="utf-8"
)

print("Secure member photo access patch applied.")
