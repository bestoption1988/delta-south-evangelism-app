package ng.mcn.deltasouth.evangelism

/**
 * Source of truth for the standalone Android client's downloadable modules.
 *
 * Downloadable modules are read-only snapshots. Registration, payments, live
 * broadcasts and all server-side writes remain online and server-authoritative.
 */
data class OfflineModuleDefinition(
    val id: String,
    val title: String,
    val description: String,
    val category: String,
    val requiresSignIn: Boolean = false,
    val containsPersonalData: Boolean = false,
    val supportsBackgroundRefresh: Boolean = true,
    val onlineOnly: Boolean = false
)

object OfflineModuleCatalog {
    val modules = listOf(
        OfflineModuleDefinition("public_home", "Diocesan Home", "Homepage welcome content, vision, mission and public notices.", "Church"),
        OfflineModuleDefinition("church_directory", "Church & Circuit Directory", "Published circuits, local churches, addresses and contact information.", "Church"),
        OfflineModuleDefinition("leadership", "Leadership", "Published diocesan and circuit leadership profiles.", "Church"),
        OfflineModuleDefinition("fellowships", "Fellowships & Ministries", "Men, women, youth, campus fellowship and ministry information.", "Church"),
        OfflineModuleDefinition("scripture", "Scripture & Bible", "Bible books, chapters, daily Scripture and reading resources.", "Worship"),
        OfflineModuleDefinition("hymns", "Methodist Hymns", "Hymn numbers, titles, lyrics and tune information.", "Worship"),
        OfflineModuleDefinition("hymn_audio", "Hymn Tunes & Audio", "Downloadable hymn recordings and tune audio.", "Worship"),
        OfflineModuleDefinition("devotionals", "Devotional Centre", "Devotional readings and worship resources.", "Worship"),
        OfflineModuleDefinition("lectionary", "Lectionary", "Published lectionary and daily readings.", "Worship"),
        OfflineModuleDefinition("communion", "Communion & Worship Books", "Communion liturgy, canticles and worship books.", "Worship"),
        OfflineModuleDefinition("media", "Church Media Library", "Published documents, images, audio and video.", "Media"),
        OfflineModuleDefinition("gallery", "Photo Gallery", "Published diocesan photographs and gallery captions.", "Media"),
        OfflineModuleDefinition("sermons", "Sermons & Teachings", "Published sermon descriptions and downloadable media where permitted.", "Media"),
        OfflineModuleDefinition("news_events", "News & Events", "Published announcements, church news and event details.", "Church"),
        OfflineModuleDefinition("resources", "Church Resources", "Public documents, notices and downloadable resources.", "Media"),
        OfflineModuleDefinition("member_profile", "My Membership", "Your authorized membership profile and ID card.", "Member", true, true),
        OfflineModuleDefinition("attendance", "Attendance", "Authorized attendance history and permitted register data.", "Member", true, true),
        OfflineModuleDefinition("giving", "Giving History", "Your authorized giving history; no payment processing offline.", "Member", true, true),
        OfflineModuleDefinition("member_updates", "Member Updates", "Authorized notices, notifications and member-care records.", "Member", true, true),
        OfflineModuleDefinition("admin_reports", "Administration & Reports", "Role-authorized reports and records for permitted officers.", "Administration", true, true),
        OfflineModuleDefinition("registration", "Membership Registration", "Submit or update registration through the secure diocesan server.", "Online Services", onlineOnly = true, supportsBackgroundRefresh = false),
        OfflineModuleDefinition("online_giving", "Online Giving & Payments", "Secure online payment and server-confirmed payment status.", "Online Services", onlineOnly = true, supportsBackgroundRefresh = false),
        OfflineModuleDefinition("live_services", "Live Services & Conference", "Live broadcasts, video meetings and real-time interaction.", "Online Services", onlineOnly = true, supportsBackgroundRefresh = false),
        OfflineModuleDefinition("prayer_requests", "Prayer Requests", "Submit prayer requests securely when connected.", "Online Services", onlineOnly = true, supportsBackgroundRefresh = false)
    )

    fun find(id: String): OfflineModuleDefinition? = modules.firstOrNull { it.id == id }

    fun downloadable(signedIn: Boolean): List<OfflineModuleDefinition> =
        modules.filter { !it.onlineOnly && (signedIn || !it.requiresSignIn) }

    fun visibleToSignedInUser(signedIn: Boolean): List<OfflineModuleDefinition> =
        modules.filter { signedIn || !it.requiresSignIn }
}
