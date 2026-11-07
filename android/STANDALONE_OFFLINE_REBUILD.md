# Standalone Android rebuild — implementation plan

## Product rule
The live Flask website is the canonical product and remains untouched. The Android app is a native client of the same backend and must not become a second source of truth.

## Architecture
- Native Kotlin + Jetpack Compose screens; no remote homepage WebView dependency.
- Existing Flask APIs remain authoritative for identity, role permissions, registration approvals and all writes.
- Room/SQLite local content store with schema/version metadata; encrypted storage for account-specific data and session tokens.
- Download manager with independent modules, resumable media downloads, checksums, progress, retry and last-updated metadata.
- WorkManager refreshes only when network is validated and user has enabled background updates.
- Offline mode is read-only for server-owned records. Local drafts may be queued only for explicitly idempotent actions with server-issued operation IDs.
- Registration, sign-in, password reset, online giving/payment and all payment confirmation remain online-only.
- Never store payment credentials or treat an offline payment as completed.

## Download modules
The catalog is implemented in `OfflineModuleCatalog.kt`: public home, church directory, leadership, Bible/Scripture, hymns, hymn audio, devotionals, lectionary, Communion/worship books, media, news/events, membership, attendance, giving history, member updates and role-authorized administration reports.

## Existing server endpoints confirmed in current app.py
- `GET /api/public/churches`
- `GET /api/offline/devotional-resources`
- `GET /api/offline/media-catalogue`
- Authenticated member reads include `/api/member/records`, `/api/member/id-card`, `/api/member/attendance-summary`, `/api/member/attendance`, `/api/member/giving-history`, `/api/member/announcements`, `/api/member/events`, `/api/member/notifications`, `/api/member/testimonies` and `/api/member/appreciations`.

## Important implementation gap
The current native app already has native authenticated member/admin screens and a downloader, but its public diocesan homepage is still rendered in a WebView. The current server does not expose a single public-home JSON endpoint for every homepage section. Before replacing that WebView, map each public section to existing read-only endpoints or add narrowly scoped read-only API endpoints to Flask. Do not scrape rendered HTML or duplicate business rules in Android.

## Acceptance tests before replacing the current APK
1. All public website sections represented in native screens and visually checked against the live site.
2. Every download module can be downloaded independently and reopened in airplane mode.
3. App restart preserves downloaded public modules; account data remains encrypted and isolated per account.
4. Logout removes account-specific cached data but preserves public downloads.
5. Registration and payment are explicitly online-only and show clear offline messages.
6. Sync retries safely, uses idempotency keys, and never duplicates attendance or financial records.
7. Role tests cover member, local church officer, circuit coordinator, diocesan roles, finance and auditor.
8. Existing website and production database remain unchanged during Android testing.
