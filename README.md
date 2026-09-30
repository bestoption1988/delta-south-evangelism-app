# Delta South Diocese Evangelism App — first working build

This is a database-backed, installable Progressive Web App (PWA) built around the existing workbook:
`data/Delta_South_Diocese_Evangelism_Fundraising_System.xlsx`

## Included in this build
- Mobile-first dashboard
- SQLite database stored on the host device
- 4 circuits and 17 numbered church placeholders (replace with official church names)
- Imports the workbook's equipment budget lines into the equipment inventory on first database creation
- Pledges/commitments, income, expenses, equipment, church planting, outreach, sponsors
- Automatic dashboard totals
- Excel export and SQLite backup endpoint
- Audit log for create/delete actions
- PWA manifest and service worker for Add to Home Screen

## Important deployment note
This is the **first working source build**, not yet a signed Android APK. A phone can install it from Chrome as a PWA once the server is running. For other phones to connect, they must be on the same Wi-Fi/hotspot and open the host phone's local IP address and port 8080. Android may restrict background hosting; keep the host app/session running. For reliable multi-phone use beyond the local network, deploy the same backend to a secure server with HTTPS.

## Run on an Android host phone (Termux)
1. Install Termux from its official F-Droid/GitHub source.
2. Copy/extract this folder to the phone, for example `~/Delta_South_Evangelism_App`.
3. In Termux run:
   ```sh
   pkg update
   pkg install python
   pip install flask openpyxl
   cd ~/Delta_South_Evangelism_App
   python app.py
   ```
4. Find the phone's local Wi-Fi/hotspot IP address. Other devices on the same network open `http://HOST-IP:8080`.
5. On the host phone, open `http://127.0.0.1:8080` in Chrome. Menu ⋮ → **Add to Home screen** / **Install app**.

## First-run security and operations
- This starter build is intended for controlled testing on a trusted local network.
- It does not yet include login/authentication, HTTPS, role-based access, or encrypted backups. Do not expose port 8080 to the public internet or enter sensitive donor information until those controls are implemented.
- Back up the database regularly. Use `/api/backup` from a browser while the server is running.
- The official church names are not in the workbook; the initial records are clearly numbered placeholders.

## Database
SQLite file: `data/evangelism.db` (created automatically at first run).
