package ng.mcn.deltasouth.evangelism

/**
 * Source of truth for downloadable content modules in the standalone Android client.
 *
 * Each module is downloaded independently. Authentication and online-only actions
 * remain server-authoritative; downloadable content is read-only while offline.
 */
data class OfflineModuleDefinition(
    val id: String,
    val title: String,
    val description: String,
    val category: String,
    val requiresSignIn: Boolean = false,
    val containsPersonalData: Boolean = false,
    val supportsBackgroundRefresh: Boolean = true
)

object OfflineModuleCatalog {
    val modules = listOf(
        OfflineModuleDefinition("public_home", "Diocesan Home", "Homepage content, notices and public church information.", "Church"),
        OfflineModuleDefinition("church_directory", "Church & Circuit Directory", "Published circuits, local churches and contact information.", "Church"),
        OfflineModuleDefinition("leadership", "Leadership", "Published diocesan and circuit leadership profiles.", "Church"),
        OfflineModuleDefinition("scripture", "Scripture & Bible", "Bible books, chapters, daily Scripture and reading resources.", "Worship"),
        OfflineModuleDefinition("hymns", "Methodist Hymns", "Hymn numbers, titles, lyrics and tune information.", "Worship"),
        OfflineModuleDefinition("hymn_audio", "Hymn Tunes & Audio", "Downloadable hymn recordings and tune audio.", "Worship"),
        OfflineModuleDefinition("devotionals", "Devotional Centre", "Devotional readings and worship resources.", "Worship"),
        OfflineModuleDefinition("lectionary", "Lectionary", "Published lectionary and daily readings.", "Worship"),
        OfflineModuleDefinition("communion", "Communion & Worship Books", "Communion liturgy, canticles and worship books.", "Worship"),
        OfflineModuleDefinition("media", "Church Media Library", "Published documents, images, audio and video.", "Media"),
        OfflineModuleDefinition("news_events", "News & Events", "Published announcements, church news and event details.", "Church"),
        OfflineModuleDefinition("member_profile", "My Membership", "Your authorized membership profile and ID card.", "Member", true, true),
        OfflineModuleDefinition("attendance", "Attendance", "Authorized attendance history and permitted register data.", "Member", true, true),
        OfflineModuleDefinition("giving", "Giving History", "Your authorized giving history; no payment processing offline.", "Member", true, true),
        OfflineModuleDefinition("member_updates", "Member Updates", "Authorized notices, notifications and member-care records.", "Member", true, true),
        OfflineModuleDefinition("admin_reports", "Administration & Reports", "Role-authorized reports and records for permitted officers.", "Administration", true, true)
    )

    fun find(id: String): OfflineModuleDefinition? = modules.firstOrNull { it.id == id }

    fun visibleToSignedInUser(signedIn: Boolean): List<OfflineModuleDefinition> =
        modules.filter { signedIn || !it.requiresSignIn }
}
