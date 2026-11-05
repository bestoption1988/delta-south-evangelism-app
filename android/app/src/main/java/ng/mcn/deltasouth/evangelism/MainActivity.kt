package ng.mcn.deltasouth.evangelism

import android.os.Bundle
import android.content.Intent
import java.io.File
import org.json.JSONArray
import org.json.JSONObject
import androidx.core.content.FileProvider
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.content.Context
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.ui.viewinterop.AndroidView
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Backend.initialize(applicationContext)
        android.webkit.ServiceWorkerController.getInstance().setServiceWorkerClient(
            object : android.webkit.ServiceWorkerClient() {
                override fun shouldInterceptRequest(request: android.webkit.WebResourceRequest): android.webkit.WebResourceResponse? {
                    if (!networkAvailable(applicationContext)) {
                        val cachedBible = OfflineModuleManager.cachedWebBibleBooks(applicationContext, request.url.toString())
                            ?: OfflineModuleManager.cachedWebBibleChapter(applicationContext, request.url.toString())
                        if (cachedBible != null) {
                            return android.webkit.WebResourceResponse(
                                "application/json", "UTF-8", 200, "OK",
                                mapOf("Access-Control-Allow-Origin" to "*", "Access-Control-Allow-Methods" to "GET, OPTIONS"),
                                cachedBible.inputStream()
                            )
                        }
                    }
                    return null
                }
            }
        )
        OfflineModuleManager.scheduleAutomaticUpdates(applicationContext)
        setContent { MaterialTheme { NativeDioceseApp() } }
    }
}

@Composable
private fun NativeDioceseApp() {
    val appContext = LocalContext.current
    var online by remember { mutableStateOf(networkAvailable(appContext)) }
    var downloadBusy by remember { mutableStateOf(false) }
    var downloadMessage by remember { mutableStateOf("") }
    var downloadedModules by remember { mutableIntStateOf(appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_downloaded_count", 0)) }
    var mediaDownloadedCount by remember { mutableIntStateOf(appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_media_downloaded_count", 0)) }
    var offlineMediaRows by remember { mutableStateOf(emptyList<Map<String, String>>()) }
    var devotionalResourceCount by remember { mutableIntStateOf(appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_devotional_resources_count", 0)) }
    var devotionalAudioCount by remember { mutableIntStateOf(appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_devotional_audio_count", 0)) }
    var offlineDevotionalRows by remember { mutableStateOf(emptyList<Map<String, String>>()) }
    var selectedDevotional by remember { mutableStateOf<Map<String, String>?>(null) }
    var pendingAttendanceCount by remember { mutableIntStateOf(OfflineAttendanceQueue.pendingCount(appContext)) }
    DisposableEffect(appContext) {
        val manager = appContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                val capabilities = manager.getNetworkCapabilities(network)
                online = capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true &&
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            }
            override fun onLost(network: Network) { online = networkAvailable(appContext) }
            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                online = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            }
        }
        runCatching { manager.registerDefaultNetworkCallback(callback) }
        onDispose { runCatching { manager.unregisterNetworkCallback(callback) } }
    }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var signedIn by remember { mutableStateOf(false) }
    var showStaffLogin by remember { mutableStateOf(false) }
    var showOfflineLibrary by remember { mutableStateOf(false) }
    var mustChangePassword by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var profile by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var dashboard by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var memberRecords by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var profilePhone by remember { mutableStateOf("") }
    var profileBirthday by remember { mutableStateOf("") }
    var profileAddress by remember { mutableStateOf("") }
    var profileProfession by remember { mutableStateOf("") }
    var profileFellowship by remember { mutableStateOf("") }
    var currentPassword by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var idCard by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var attendanceSummary by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var attendanceRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var attendanceRegisterMembers by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var attendanceRegisterDate by remember { mutableStateOf(java.time.LocalDate.now().toString()) }
    var attendanceMeetingType by remember { mutableStateOf("Sunday Service") }
    var attendanceMemberSearch by remember { mutableStateOf("") }
    var givingRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var feedRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var eventRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var notificationRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var careThreads by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var careUnreadTotal by remember { mutableStateOf(0) }
    var careDetail by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var careSelectedId by remember { mutableStateOf<Int?>(null) }
    var careSubject by remember { mutableStateOf("") }
    var careMessage by remember { mutableStateOf("") }
    var careCategory by remember { mutableStateOf("General Assistance") }
    var carePriority by remember { mutableStateOf("Normal") }
    var careReply by remember { mutableStateOf("") }
    var financeSummary by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var reportData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var governanceData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var healthData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var securityData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var backupRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var adminUserRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var accountRequestRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var accountRequestRole by remember { mutableStateOf("Local Church Evangelism Officer") }
    var qualityData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var auditRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var reportYear by remember { mutableStateOf(java.time.LocalDate.now().year.toString()) }
    var reportCircuit by remember { mutableStateOf("All") }
    var paymentRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var reconciliationRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var churchAccountRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var accountBank by remember { mutableStateOf("") }
    var accountName by remember { mutableStateOf("") }
    var accountNumber by remember { mutableStateOf("") }
    var accountType by remember { mutableStateOf("Current") }
    var accountBranch by remember { mutableStateOf("") }
    var accountNotes by remember { mutableStateOf("") }
    var conferenceRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var conferenceTitle by remember { mutableStateOf("") }
    var conferenceDate by remember { mutableStateOf("") }
    var conferenceStart by remember { mutableStateOf("") }
    var conferenceEnd by remember { mutableStateOf("") }
    var conferenceCircuit by remember { mutableStateOf("Diocesan") }
    var conferenceAgenda by remember { mutableStateOf("") }
    var conferenceDetail by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var conferenceSelectedId by remember { mutableStateOf<Int?>(null) }
    var conferenceMessage by remember { mutableStateOf("") }
    var conferenceParticipantName by remember { mutableStateOf("") }
    var conferenceParticipantRole by remember { mutableStateOf("") }
    var conferencePresenceRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var registrations by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var directoryChurches by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var directoryCircuits by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var memberDirectory by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var memberSearch by remember { mutableStateOf("") }
    var membershipStats by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var appointmentMember by remember { mutableStateOf<Map<String, Any?>?>(null) }
    var appointmentData by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var appointmentOffice by remember { mutableStateOf("Local Church Evangelism Officer") }
    var appointmentLevel by remember { mutableStateOf("Local Church") }
    var appointmentCircuit by remember { mutableStateOf("") }
    var appointmentChurch by remember { mutableStateOf("") }
    var appointmentStart by remember { mutableStateOf("") }
    var appointmentEnd by remember { mutableStateOf("") }
    var appointmentNotes by remember { mutableStateOf("") }
    var appointmentEditingId by remember { mutableStateOf<Int?>(null) }
    var selected by remember { mutableStateOf("Home") }
    val scope = rememberCoroutineScope()
    // Restore a previously authenticated, encrypted staff session before showing
    // the public screen. The cached /api/me response permits read-only offline access.
    LaunchedEffect(Unit) {
        if (Backend.cookies.hasSession()) {
            val restored = withContext(Dispatchers.IO) { runCatching { Backend.api.me() } }
            restored.onSuccess { account ->
                profile = account
                if (account["must_change_password"] == true || account["must_change_password"].toString() == "1") {
                    mustChangePassword = true
                    showStaffLogin = true
                } else {
                    signedIn = true
                    selected = "Home"
                }
            }.onFailure { error ->
                if (online) message = error.message ?: "Your saved staff session could not be restored."
            }
        }
    }
    // Reuse encrypted, session-scoped API snapshots when offline; only refresh and
    // synchronize server changes when a validated connection is available.
    LaunchedEffect(signedIn, online) {
        if (signedIn) {
            if (online) {
                runCatching { withContext(Dispatchers.IO) { OfflineAttendanceQueue.syncPending(appContext) } }
                    .onSuccess { pendingAttendanceCount = OfflineAttendanceQueue.pendingCount(appContext) }
            }
            runCatching { withContext(Dispatchers.IO) { Backend.api.dashboard() } }
                .onSuccess { dashboard = it }
                .onFailure { message = it.message ?: "Dashboard will load when the connection is available." }
            if (online) {
                val prefs = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
                if (prefs.getBoolean("initial_download_complete", false)) {
                    OfflineModuleManager.scheduleImmediateUpdate(appContext)
                } else {
                    downloadBusy = true
                    downloadMessage = "Preparing your offline modules…"
                    val result = withContext(Dispatchers.IO) { OfflineModuleManager.downloadAll(appContext) }
                    downloadedModules = result.downloaded
                    if (result.downloaded > 0) prefs.edit().putBoolean("initial_download_complete", true).apply()
                    downloadMessage = "Initial download: ${result.downloaded} saved, ${result.unavailable} not available for this account, ${result.failed} failed."
                    downloadBusy = false
                }
            }
        }
    }
    LaunchedEffect(selected, devotionalResourceCount, devotionalAudioCount) {
        if (selected == "Downloads") {
            offlineMediaRows = withContext(Dispatchers.IO) {
                runCatching {
                    val file = File(OfflineModuleManager.offlineMediaDirectory(appContext), "index.json")
                    val array = if (file.exists()) JSONArray(file.readText()) else JSONArray()
                    (0 until array.length()).mapNotNull { index ->
                        val item = array.optJSONObject(index) ?: return@mapNotNull null
                        mapOf(
                            "title" to item.optString("title"),
                            "description" to item.optString("description"),
                            "mime_type" to item.optString("mime_type"),
                            "media_type" to item.optString("media_type"),
                            "file" to item.optString("file")
                        )
                    }
                }.getOrDefault(emptyList())
            }
            offlineDevotionalRows = withContext(Dispatchers.IO) {
                runCatching {
                    val directory = File(appContext.filesDir, "offline_devotional")
                    val collections = listOf("english_hymns", "yoruba_hymns", "akokun", "bible_verses", "canticles", "communion_english", "communion_yoruba", "creeds")
                    val output = mutableListOf<Map<String, String>>()
                    collections.forEach { collection ->
                        val file = File(directory, collection + ".json")
                        if (file.exists()) {
                            val array = JSONArray(file.readText())
                            for (index in 0 until array.length()) {
                                val item = array.optJSONObject(index) ?: continue
                                val payload = item.optJSONObject("payload") ?: runCatching { JSONObject(item.optString("content_json", "{}")) }.getOrDefault(JSONObject())
                                val body = buildString {
                                    listOf("reference", "heading", "verse", "content", "firstline", "lyrics", "chorus").forEach { key ->
                                        val value = payload.optString(key)
                                        if (value.isNotBlank()) append(value).append("\n\n")
                                    }
                                    val stanzas = payload.optJSONArray("stanzas")
                                    if (stanzas != null) for (s in 0 until stanzas.length()) append(stanzas.optString(s)).append("\n\n")
                                }.trim()
                                output.add(mapOf(
                                    "title" to item.optString("title", "Church resource"),
                                    "collection" to collection.replace('_', ' '),
                                    "content" to body,
                                    "audio_file" to item.optString("audio_file")
                                ))
                            }
                        }
                    }
                    output
                }.getOrDefault(emptyList())
            }
        }
    }
    BackHandler(enabled = signedIn && selected != "Home") { selected = "Home"; message = "" }
    val role = (profile["role"] ?: "").toString()
    val financeRoles = setOf("Admin", "Finance Officer", "Auditor", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary")
    val canReview = role == "Admin" || role == "Evangelism Minister"

    if (!signedIn && !showStaffLogin && !showOfflineLibrary) {
        PublicDiocesanHomepage(
            online = online,
            offlineDownloadBusy = downloadBusy,
            onStaffLogin = { showStaffLogin = true },
            onOfflineDownload = {
                if (online && !downloadBusy) {
                    downloadBusy = true
                    downloadMessage = "Saving the diocesan homepage, devotional resources, media and permitted records for offline use…"
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            runCatching { OfflineModuleManager.downloadAll(appContext) }
                        }
                        result.onSuccess { summary ->
                            downloadedModules = summary.downloaded
                            mediaDownloadedCount = summary.mediaDownloaded
                            devotionalResourceCount = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_devotional_resources_count", 0)
                            devotionalAudioCount = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_devotional_audio_count", 0)
                            val offlinePrefs = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
                            val webChapters = offlinePrefs.getInt("last_web_bible_chapter_count", 0)
                            val missingWebChapters = offlinePrefs.getInt("last_web_bible_missing_count", 0)
                            downloadMessage = "Offline package updated: ${summary.downloaded} data sets, ${summary.mediaDownloaded} media files, ${webChapters} WEB Bible chapters, ${summary.unavailable} account-restricted items and ${summary.failed} failed modules."
                            if (missingWebChapters > 0) downloadMessage += " ${missingWebChapters} WEB Bible chapters need another download."
                            android.widget.Toast.makeText(appContext, downloadMessage, android.widget.Toast.LENGTH_LONG).show()
                        }.onFailure { error ->
                            downloadMessage = error.message ?: "The offline package could not be completed."
                            android.widget.Toast.makeText(appContext, downloadMessage, android.widget.Toast.LENGTH_LONG).show()
                        }
                        downloadBusy = false
                    }
                }
            },
            onBackPressed = { }
        )
    } else if (!signedIn && showOfflineLibrary) {
        PublicOfflineLibrary(online = online, onBack = { showOfflineLibrary = false })
    } else if (!signedIn && mustChangePassword) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.Center) {
            Text("Password update required", style = MaterialTheme.typography.headlineSmall)
            Text("Your account must have a new password before you can open staff records.")
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(currentPassword, { currentPassword = it }, label = { Text("Current / temporary password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
            OutlinedTextField(newPassword, { newPassword = it }, label = { Text("New password (at least 8 characters)") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
            OutlinedTextField(confirmPassword, { confirmPassword = it }, label = { Text("Confirm new password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            Button(enabled = !busy, onClick = {
                busy = true
                message = "Updating password…"
                scope.launch {
                    val result = withContext(Dispatchers.IO) {
                        Backend.api.forceChangePassword(mapOf(
                            "current_password" to currentPassword,
                            "new_password" to newPassword,
                            "confirm_password" to confirmPassword
                        ))
                    }
                    if (result["success"] == true) {
                        mustChangePassword = false
                        signedIn = true
                        profile = profile + ("must_change_password" to false)
                        selected = "Home"
                        password = ""
                        currentPassword = ""
                        newPassword = ""
                        confirmPassword = ""
                        message = result["message"]?.toString() ?: "Password changed successfully."
                    } else {
                        message = result["message"]?.toString() ?: "Password could not be changed."
                    }
                    busy = false
                }
            }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Please wait…" else "Save new password") }
            if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.error)
        }
    } else if (!signedIn) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.Center) {
            TextButton(onClick = { showStaffLogin = false; message = "" }) { Text("← Back to public homepage") }
            Text("METHODIST CHURCH NIGERIA", style = MaterialTheme.typography.titleLarge)
            Text("DELTA SOUTH DIOCESE", style = MaterialTheme.typography.titleMedium)
            Text("Staff and authorised officers", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(username, { username = it }, label = { Text("Username") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(password, { password = it }, label = { Text("Password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            Button(enabled = !busy, onClick = {
                busy = true
                message = "Signing in…"
                scope.launch {
                    val result = withContext(Dispatchers.IO) { Backend.login(username.trim(), password) }
                    result.onSuccess {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.me() } }
                            .onSuccess {
                                profile = it
                                if (it["must_change_password"] == true || it["must_change_password"].toString() == "1") {
                                    currentPassword = password
                                    mustChangePassword = true
                                    message = "Please set a new password to continue."
                                } else {
                                    signedIn = true
                                    selected = "Home"
                                    message = ""
                                }
                            }
                            .onFailure { message = it.message ?: "Could not load account profile." }
                    }.onFailure { message = it.message ?: "Sign in failed." }
                    busy = false
                }
            }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Please wait…" else "Sign in") }
            if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.error)
        }
    } else {        val tabs = buildList {
            addAll(listOf("Home", "Profile", "Attendance", "Giving", "Feed", "Updates", "Member Care", "Directory", "Downloads"))
            if (role == "Member") add("ID Card")
            if (role in setOf("Admin", "Evangelism Minister", "Planting Officer", "Circuit Coordinator", "Local Church Evangelism Officer")) add("Attendance Register")
            if (role in setOf("Admin", "Bishop / Diocesan Executive", "Evangelism Minister", "Planting Officer", "Diocesan Secretary", "Circuit Coordinator", "Local Church Evangelism Officer", "Auditor")) add("Members")
            if (financeRoles.contains(role)) add("Finance")
            if (role in setOf("Admin", "Auditor", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary", "Circuit Coordinator")) add("Reports")
            if (role in setOf("Admin", "Auditor")) add("System")
            if (role == "Admin") add("User Administration")
            if (role == "Admin") add("Account Requests")
            if (role in setOf("Admin", "Auditor", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary", "Circuit Coordinator")) add("Governance")
            add("Conferences")
            if (canReview) add("Approvals")
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp)) {
            Text("MCN Delta South Diocese", style = MaterialTheme.typography.headlineSmall)
            Text(if (online) "ONLINE • Live diocesan data" else "OFFLINE • Showing saved data where available; changes require internet", color = if (online) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error, style = MaterialTheme.typography.labelMedium)
            Text("Welcome, ${profile["full_name"] ?: profile["username"] ?: "Member"}")
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
                tabs.forEach { label -> FilterChip(selected == label, { selected = label }, label = { Text(label) }) }
            }
            Spacer(Modifier.height(10.dp))
            when (selected) {
                "Home" -> {
                    ActionButton("Refresh dashboard", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.dashboard() } }
                            .onSuccess { dashboard = it }.onFailure { message = it.message ?: "Dashboard could not load." }
                    }
                    DashboardCards(dashboard)
                }
                "Downloads" -> {
                    Text("Offline Download Centre", style = MaterialTheme.typography.titleLarge)
                    Text("Download the information your account is permitted to access. Saved API data is encrypted on this phone and remains available when you are offline.")
                    Spacer(Modifier.height(8.dp))
                    Text("Downloaded data sets: $downloadedModules")
                    Text("Offline media files: $mediaDownloadedCount")
                    Text("Attendance records waiting to sync: $pendingAttendanceCount")
                    Text(if (online) "Internet connection available" else "Offline — saved information remains available")
                    Button(
                        enabled = online && !downloadBusy,
                        onClick = {
                            downloadBusy = true
                            downloadMessage = "Downloading available modules…"
                            scope.launch {
                                val result = withContext(Dispatchers.IO) { OfflineModuleManager.downloadAll(appContext) }
                                downloadedModules = result.downloaded
                                mediaDownloadedCount = result.mediaDownloaded
                                devotionalResourceCount = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).getInt("last_devotional_resources_count", 0)
                                offlineMediaRows = withContext(Dispatchers.IO) {
                                    runCatching {
                                        val file = File(OfflineModuleManager.offlineMediaDirectory(appContext), "index.json")
                                        val array = if (file.exists()) JSONArray(file.readText()) else JSONArray()
                                        (0 until array.length()).mapNotNull { index ->
                                            val item = array.optJSONObject(index) ?: return@mapNotNull null
                                            mapOf("title" to item.optString("title"), "description" to item.optString("description"), "mime_type" to item.optString("mime_type"), "media_type" to item.optString("media_type"), "file" to item.optString("file"))
                                        }
                                    }.getOrDefault(emptyList())
                                }
                                downloadMessage = "Completed: ${result.downloaded} data sets, ${result.mediaDownloaded} media files downloaded, ${result.unavailable} unavailable to this account, ${result.failed} failed."
                                downloadBusy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text(if (downloadBusy) "Downloading…" else "Download All Modules") }
                    Text("Devotional & Worship Centre", style = MaterialTheme.typography.titleMedium)
                    Text("Saved devotional readings: $devotionalResourceCount")
                    Text("Hymn audio records checked: $devotionalAudioCount")
                    Button(
                        enabled = online && !downloadBusy,
                        onClick = {
                            downloadBusy = true
                            downloadMessage = "Downloading hymns, Scripture, canticles, Communion and creeds…"
                            scope.launch {
                                val count = withContext(Dispatchers.IO) {
                                    val saved = OfflineModuleManager.downloadAllDevotionalResources(appContext)
                                    OfflineModuleManager.downloadDailyDevotion(appContext)
                                    OfflineModuleManager.downloadLectionary(appContext)
                                    saved
                                }
                                devotionalResourceCount = count
                                downloadMessage = "$count devotional resources, today's Scripture and hymn, and the 2027 lectionary saved for offline use."
                                downloadBusy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Download Hymns, Scripture & Worship Books") }
                    Button(
                        enabled = online && !downloadBusy,
                        onClick = {
                            downloadBusy = true
                            downloadMessage = "Downloading hymn recordings…"
                            scope.launch {
                                val count = withContext(Dispatchers.IO) { OfflineModuleManager.downloadHymnAudio(appContext) }
                                devotionalAudioCount = count
                                downloadMessage = "Hymn audio download finished. $count hymn records checked."
                                downloadBusy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Download Hymn Audio") }
                    Button(
                        enabled = online && !downloadBusy,
                        onClick = {
                            runCatching {
                                val bibleUrl = BuildConfig.API_BASE_URL + "devotional-centre/holy-bible"
                                appContext.startActivity(
                                    Intent(Intent.ACTION_VIEW, android.net.Uri.parse(bibleUrl))
                                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                )
                                downloadMessage = "Opening the World English Bible (WEB) reader."
                            }.onFailure { downloadMessage = it.message ?: "Could not open the WEB Bible reader." }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Open World English Bible (WEB)") }
                    Text("Download published media by module", style = MaterialTheme.typography.titleMedium)
                    val downloadMediaModule: (String, String) -> Unit = { mediaType, label ->
                        downloadBusy = true
                        downloadMessage = "Downloading $label for offline use…"
                        scope.launch {
                            val saved = withContext(Dispatchers.IO) {
                                OfflineModuleManager.downloadMediaCategory(appContext, mediaType)
                            }
                            offlineMediaRows = withContext(Dispatchers.IO) {
                                runCatching {
                                    val file = File(OfflineModuleManager.offlineMediaDirectory(appContext), "index.json")
                                    val array = if (file.exists()) JSONArray(file.readText()) else JSONArray()
                                    (0 until array.length()).mapNotNull { index ->
                                        val item = array.optJSONObject(index) ?: return@mapNotNull null
                                        mapOf("title" to item.optString("title"), "description" to item.optString("description"), "mime_type" to item.optString("mime_type"), "media_type" to item.optString("media_type"), "file" to item.optString("file"))
                                    }
                                }.getOrDefault(emptyList())
                            }
                            mediaDownloadedCount = offlineMediaRows.size
                            downloadMessage = if (saved > 0) "$saved $label item(s) saved for offline use." else "No new published $label files could be downloaded. Check that the files are published in the Church Media Library."
                            downloadBusy = false
                        }
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            enabled = online && !downloadBusy,
                            onClick = { downloadMediaModule("audio", "audio") },
                            modifier = Modifier.weight(1f)
                        ) { Text("Audio") }
                        Button(
                            enabled = online && !downloadBusy,
                            onClick = { downloadMediaModule("video", "video") },
                            modifier = Modifier.weight(1f)
                        ) { Text("Video") }
                        Button(
                            enabled = online && !downloadBusy,
                            onClick = { downloadMediaModule("document", "document") },
                            modifier = Modifier.weight(1f)
                        ) { Text("Documents") }
                    }
                    Button(
                        enabled = online && pendingAttendanceCount > 0 && !downloadBusy,
                        onClick = {
                            downloadBusy = true
                            scope.launch {
                                val synced = withContext(Dispatchers.IO) { OfflineAttendanceQueue.syncPending(appContext) }
                                pendingAttendanceCount = OfflineAttendanceQueue.pendingCount(appContext)
                                downloadMessage = "$synced queued attendance records synchronized. $pendingAttendanceCount remain pending."
                                downloadBusy = false
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Synchronize Queued Attendance") }
                    Text("Automatic updates run every 6 hours whenever Wi-Fi or mobile data is available. You can also download updates now.")
                    if (downloadMessage.isNotBlank()) Text(downloadMessage, style = MaterialTheme.typography.bodySmall)
                    Text("Saved media — available without internet", style = MaterialTheme.typography.titleMedium)
                    if (offlineMediaRows.isEmpty()) Text("No published media has been downloaded yet.")
                    offlineMediaRows.forEach { item ->
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                Column(Modifier.weight(1f)) {
                                    Text(item["title"] ?: "Church media", style = MaterialTheme.typography.bodyLarge)
                                    Text(item["media_type"] ?: "Media", style = MaterialTheme.typography.bodySmall)
                                }
                                Button(onClick = {
                                    runCatching {
                                        val file = File(OfflineModuleManager.offlineMediaDirectory(appContext), item["file"] ?: "")
                                        require(file.exists()) { "This media file is not saved on this phone." }
                                        val uri = FileProvider.getUriForFile(appContext, appContext.packageName + ".fileprovider", file)
                                        val intent = Intent(Intent.ACTION_VIEW).setDataAndType(uri, item["mime_type"] ?: "*/*")
                                            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                                        appContext.startActivity(intent)
                                    }.onFailure { downloadMessage = it.message ?: "No compatible viewer is installed." }
                                }) { Text("Open") }
                            }
                        }
                    }
                    Text("Saved devotional readings — available without internet", style = MaterialTheme.typography.titleMedium)
                    if (offlineDevotionalRows.isEmpty()) Text("Download the devotional collections above to read hymns, Scripture and worship materials offline.")
                    LazyColumn(modifier = Modifier.heightIn(max = 460.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        items(offlineDevotionalRows.take(80)) { item ->
                            ElevatedCard(Modifier.fillMaxWidth()) {
                                Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Column(Modifier.weight(1f)) {
                                        Text(item["title"] ?: "Church resource", style = MaterialTheme.typography.bodyLarge)
                                        Text(item["collection"] ?: "Devotional", style = MaterialTheme.typography.bodySmall)
                                    }
                                    TextButton(onClick = { selectedDevotional = item }) { Text("Read") }
                                }
                            }
                        }
                    }
                    Text("For security, financial actions, approvals, messages and other changes still need a live connection. Offline mode does not invent or replay transactions.")
                }
                "Profile" -> {
                    Text("My Membership Profile", style = MaterialTheme.typography.titleLarge)
                    ActionButton("Load membership record", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.memberRecords() } }
                            .onSuccess { memberRecords = it; message = "Membership record loaded." }.onFailure { message = it.message ?: "Membership record unavailable." }
                    }
                    KeyValueList(if (memberRecords.isEmpty()) profile else memberRecords)
                    if (role == "Member") {
                        Text("Update contact details", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(profilePhone, { profilePhone = it }, label = { Text("Phone") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(profileBirthday, { profileBirthday = it }, label = { Text("Birthday") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(profileAddress, { profileAddress = it }, label = { Text("Residential address") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(profileProfession, { profileProfession = it }, label = { Text("Profession / business / trade") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(profileFellowship, { profileFellowship = it }, label = { Text("Fellowship") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy, onClick = {
                            scope.launch {
                                busy = true
                                val updates = mapOf("phone" to profilePhone, "birthday" to profileBirthday, "address" to profileAddress, "profession_business_trade" to profileProfession, "fellowship" to profileFellowship).filterValues { it.isNotBlank() }
                                runCatching { withContext(Dispatchers.IO) { Backend.api.updateMemberProfile(updates) } }
                                    .onSuccess { message = it["message"]?.toString() ?: "Profile updated." }
                                    .onFailure { message = it.message ?: "Profile update failed." }
                                busy = false
                            }
                        }) { Text("Save profile details") }
                        Text("Change password", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(currentPassword, { currentPassword = it }, label = { Text("Current password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(newPassword, { newPassword = it }, label = { Text("New password (minimum 8 characters)") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(confirmPassword, { confirmPassword = it }, label = { Text("Confirm new password") }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && currentPassword.isNotBlank() && newPassword.length >= 8 && newPassword == confirmPassword, onClick = {
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) { Backend.api.changeMemberPassword(mapOf("current_password" to currentPassword, "new_password" to newPassword, "confirm_password" to confirmPassword)) } }
                                    .onSuccess { currentPassword = ""; newPassword = ""; confirmPassword = ""; message = it["message"]?.toString() ?: "Password changed." }
                                    .onFailure { message = it.message ?: "Password change failed." }
                                busy = false
                            }
                        }) { Text("Change password") }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                }
                "ID Card" -> {
                    Text("Official Diocesan Membership ID", style = MaterialTheme.typography.titleLarge)
                    ActionButton("Load my membership ID", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.memberIdCard() } }
                            .onSuccess { idCard = it; message = "Membership ID loaded." }
                            .onFailure { message = it.message ?: "Membership ID is unavailable." }
                    }
                    if (idCard.isNotEmpty()) MemberIdCard(idCard)
                    Text(message, style = MaterialTheme.typography.bodySmall)
                }
                "Attendance Register" -> {
                    Text("Church Attendance Register", style = MaterialTheme.typography.titleLarge)
                    Text("Record member attendance for your authorized church or circuit. The server enforces your role and church boundaries.")
                    OutlinedTextField(attendanceRegisterDate, { attendanceRegisterDate = it }, label = { Text("Attendance date (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(attendanceMeetingType, { attendanceMeetingType = it }, label = { Text("Meeting / service") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(attendanceMemberSearch, { attendanceMemberSearch = it }, label = { Text("Search member name or ID") }, modifier = Modifier.fillMaxWidth())
                    ActionButton("Load members for attendance", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.members() } }
                            .onSuccess { attendanceRegisterMembers = it; message = "${it.size} members loaded." }
                            .onFailure { message = it.message ?: "Could not load members." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    val filteredAttendanceMembers = attendanceRegisterMembers.filter { member ->
                        val q = attendanceMemberSearch.trim()
                        q.isBlank() || listOf("full_name", "member_id", "phone", "church_name").any { member[it]?.toString()?.contains(q, true) == true }
                    }
                    filteredAttendanceMembers.forEach { member ->
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(member["full_name"]?.toString() ?: "Member", style = MaterialTheme.typography.titleSmall)
                                Text("ID: ${member["member_id"] ?: member["id"] ?: ""}  •  ${member["church_name"] ?: ""}")
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Button(enabled = !busy, onClick = {
                                        val id = (member["id"] as? Number)?.toInt() ?: member["member_id"]?.toString()?.toIntOrNull()
                                        if (id != null) scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) { Backend.api.recordMemberAttendance(mapOf("member_id" to id.toString(), "attendance_date" to attendanceRegisterDate.trim(), "meeting_type" to attendanceMeetingType.trim(), "status" to "Present")) } }
                                                .onSuccess { message = "Present recorded for ${member["full_name"] ?: "member"}." }
                                                .onFailure {
                                                    if (!online) {
                                                        OfflineAttendanceQueue.enqueueAttendance(appContext, mapOf("member_id" to id.toString(), "attendance_date" to attendanceRegisterDate.trim(), "meeting_type" to attendanceMeetingType.trim(), "status" to "Present"))
                                                        pendingAttendanceCount = OfflineAttendanceQueue.pendingCount(appContext)
                                                        message = "Attendance saved securely on this phone. It will synchronize when internet returns."
                                                    } else message = it.message ?: "Could not record attendance."
                                                }
                                            busy = false
                                        }
                                    }) { Text("Present") }
                                    OutlinedButton(enabled = !busy, onClick = {
                                        val id = (member["id"] as? Number)?.toInt() ?: member["member_id"]?.toString()?.toIntOrNull()
                                        if (id != null) scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) { Backend.api.recordMemberAttendance(mapOf("member_id" to id.toString(), "attendance_date" to attendanceRegisterDate.trim(), "meeting_type" to attendanceMeetingType.trim(), "status" to "Absent")) } }
                                                .onSuccess { message = "Absent recorded for ${member["full_name"] ?: "member"}." }
                                                .onFailure {
                                                    if (!online) {
                                                        OfflineAttendanceQueue.enqueueAttendance(appContext, mapOf("member_id" to id.toString(), "attendance_date" to attendanceRegisterDate.trim(), "meeting_type" to attendanceMeetingType.trim(), "status" to "Absent"))
                                                        pendingAttendanceCount = OfflineAttendanceQueue.pendingCount(appContext)
                                                        message = "Attendance saved securely on this phone. It will synchronize when internet returns."
                                                    } else message = it.message ?: "Could not record attendance."
                                                }
                                            busy = false
                                        }
                                    }) { Text("Absent") }
                                }
                            }
                        }
                    }
                }
                "Attendance" -> {
                    ActionButton("Refresh attendance", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.attendanceSummary() to Backend.api.memberAttendance() } }
                            .onSuccess { attendanceSummary = it.first; attendanceRows = it.second }
                            .onFailure { message = it.message ?: "Attendance history unavailable." }
                    }
                    KeyValueList(attendanceSummary)
                    Text("Attendance history", style = MaterialTheme.typography.titleMedium)
                    RecordList(attendanceRows, listOf("attendance_date", "meeting_type", "status", "circuit", "church_name"))
                }
                "Giving" -> {
                    ActionButton("Refresh giving history", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.givingHistory() } }
                            .onSuccess { givingRows = it }.onFailure { message = it.message ?: "Giving history unavailable." }
                    }
                    Text("Your recorded contributions", style = MaterialTheme.typography.titleMedium)
                    RecordList(givingRows, listOf("date", "source", "fund", "amount", "method", "reference"))
                }
                "Feed" -> {
                    ActionButton("Load announcements", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.announcements() } }
                            .onSuccess { feedRows = it; message = "${it.size} announcements loaded." }
                            .onFailure { message = it.message ?: "Feed unavailable." }
                    }
                    Text(message)
                    RecordList(feedRows, listOf("title", "message", "created_at", "status"))
                }
                "Updates" -> {
                    Text("Diocesan Updates Centre", style = MaterialTheme.typography.titleLarge)
                    Text("Announcements, diocesan events and account notifications.")
                    ActionButton("Refresh all updates", busy) {
                        runCatching {
                            withContext(Dispatchers.IO) {
                                Triple(Backend.api.announcements(), Backend.api.events(), Backend.api.notifications())
                            }
                        }.onSuccess {
                            feedRows = it.first
                            eventRows = it.second
                            notificationRows = it.third
                            message = "Updates refreshed."
                        }.onFailure { message = it.message ?: "Updates could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    Text("Announcements", style = MaterialTheme.typography.titleMedium)
                    RecordList(feedRows, listOf("title", "message", "created_at", "status"))
                    Text("Upcoming events", style = MaterialTheme.typography.titleMedium)
                    RecordList(eventRows, listOf("title", "event_name", "description", "event_date", "start_time", "venue", "status"))
                    Text("My notifications", style = MaterialTheme.typography.titleMedium)
                    notificationRows.forEach { notification ->
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(notification["title"]?.toString() ?: "Notification", style = MaterialTheme.typography.titleSmall)
                                Text(notification["message"]?.toString() ?: "")
                                Text("Type: ${notification["notification_type"] ?: ""}  •  Status: ${notification["status"] ?: ""}")
                                val notificationId = (notification["id"] as? Number)?.toInt()
                                if (notificationId != null && notification["status"]?.toString()?.equals("Read", true) != true) {
                                    OutlinedButton(enabled = !busy, onClick = {
                                        scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) { Backend.api.markNotificationRead(notificationId) } }
                                                .onSuccess { runCatching { withContext(Dispatchers.IO) { Backend.api.notifications() } }.onSuccess { notificationRows = it }; message = "Notification marked as read." }
                                                .onFailure { message = it.message ?: "Could not mark notification as read." }
                                            busy = false
                                        }
                                    }) { Text("Mark as read") }
                                }
                            }
                        }
                    }
                }
                "Member Care" -> {
                    Text("Diocesan Member Care", style = MaterialTheme.typography.titleLarge)
                    Text("Submit a request, follow up your conversations and reply to the diocesan support team.")
                    Text("Unread replies: $careUnreadTotal", style = MaterialTheme.typography.labelLarge)
                    ActionButton("Load my conversations", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.customerCareThreads() } }
                            .onSuccess { careThreads = it; runCatching { withContext(Dispatchers.IO) { Backend.api.customerCareUnreadCount() } }.onSuccess { careUnreadTotal = (it["total"] as? Number)?.toInt() ?: 0 }; message = "${it.size} conversations loaded." }
                            .onFailure { message = it.message ?: "Member Care is unavailable." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    careThreads.forEach { thread ->
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp)) {
                                Text(thread["subject"]?.toString()?.ifBlank { "Support request" } ?: "Support request", style = MaterialTheme.typography.titleSmall)
                                Text("Ticket: ${thread["thread_id"] ?: "—"} • ${thread["status"] ?: "—"}")
                                Text("Category: ${thread["category"] ?: "General Assistance"} • Priority: ${thread["priority"] ?: "Normal"}")
                                TextButton(onClick = {
                                    val id = (thread["id"] as? Number)?.toInt()
                                    if (id != null) {
                                        careSelectedId = id
                                        scope.launch {
                                            runCatching { withContext(Dispatchers.IO) {
                                                Backend.api.markCustomerCareRead(id)
                                                Backend.api.customerCareDetail(id)
                                            } }
                                                .onSuccess {
                                                    careDetail = it
                                                    runCatching { withContext(Dispatchers.IO) { Backend.api.customerCareUnreadCount() } }
                                                        .onSuccess { careUnreadTotal = (it["total"] as? Number)?.toInt() ?: 0 }
                                                }
                                                .onFailure { message = it.message ?: "Conversation could not be opened." }
                                        }
                                    }
                                }) { Text("Open conversation") }
                            }
                        }
                    }
                    Divider()
                    Text("Create a support request", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(careSubject, { careSubject = it }, label = { Text("Subject") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(careCategory, { careCategory = it }, label = { Text("Category (use exact category)") }, modifier = Modifier.fillMaxWidth())
                    Text("Categories: General Assistance, Registration, Church Records, Baptism, Confirmation, Marriage, Transfer / Relocation, Giving / Tithe, Technical Support, Other", style = MaterialTheme.typography.bodySmall)
                    OutlinedTextField(carePriority, { carePriority = it }, label = { Text("Priority: Normal, High, Urgent") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(careMessage, { careMessage = it }, label = { Text("Describe how we can help") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                    Button(enabled = !busy && careMessage.isNotBlank(), onClick = {
                        busy = true
                        scope.launch {
                            runCatching { withContext(Dispatchers.IO) {
                                Backend.api.createCustomerCareThread(mapOf(
                                    "subject" to careSubject.trim(), "category" to careCategory.trim(),
                                    "priority" to carePriority.trim(), "message" to careMessage.trim()
                                ))
                            } }.onSuccess {
                                message = "Support request submitted. Ticket: ${it["thread_id"] ?: "created"}"
                                careSubject = ""; careMessage = ""
                                runCatching { withContext(Dispatchers.IO) { Backend.api.customerCareThreads() } }
                                    .onSuccess { careThreads = it }
                            }.onFailure { message = it.message ?: "Could not submit request." }
                            busy = false
                        }
                    }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Submitting…" else "Submit support request") }
                    careSelectedId?.let { selectedId ->
                        Divider()
                        val thread = careDetail["thread"] as? Map<String, Any?> ?: emptyMap()
                        Text("Conversation: ${thread["thread_id"] ?: selectedId}", style = MaterialTheme.typography.titleMedium)
                        val messages = careDetail["messages"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(messages, listOf("sender_name", "sender_role", "message", "created_at"))
                        OutlinedTextField(careReply, { careReply = it }, label = { Text("Write a reply") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                        Button(enabled = !busy && careReply.isNotBlank(), onClick = {
                            busy = true
                            scope.launch {
                                runCatching { withContext(Dispatchers.IO) { Backend.api.sendCustomerCareMessage(selectedId, mapOf("message" to careReply.trim())) } }
                                    .onSuccess {
                                        careReply = ""
                                        runCatching { withContext(Dispatchers.IO) { Backend.api.customerCareDetail(selectedId) } }
                                            .onSuccess { careDetail = it }
                                        message = "Reply sent."
                                    }.onFailure { message = it.message ?: "Reply could not be sent." }
                                busy = false
                            }
                        }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Sending…" else "Send reply") }
                    }
                }
                "Account Requests" -> {
                    Text("Staff Account Registration Requests", style = MaterialTheme.typography.titleLarge)
                    Text("Review pending requests and assign only an authorized role. The server validates circuit and church assignments.")
                    ActionButton("Load account requests", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.accountRequests() } }
                            .onSuccess { accountRequestRows = it; message = "${it.count { row -> row["status"]?.toString() == "Pending" }} pending requests loaded." }
                            .onFailure { message = it.message ?: "Account requests could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    OutlinedTextField(accountRequestRole, { accountRequestRole = it }, label = { Text("Role to assign (choose an allowed staff role)") }, modifier = Modifier.fillMaxWidth())
                    Text("Allowed: Admin, Bishop / Diocesan Executive, Evangelism Minister, Planting Officer, Diocesan Secretary, Circuit Coordinator, Local Church Evangelism Officer, Finance Officer, Auditor", style = MaterialTheme.typography.bodySmall)
                    accountRequestRows.filter { it["status"]?.toString() == "Pending" }.forEach { req ->
                        val id = (req["id"] as? Number)?.toInt() ?: -1
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                Text(req["full_name"]?.toString() ?: "Applicant", style = MaterialTheme.typography.titleSmall)
                                Text("Username: ${req["username"] ?: "—"}")
                                Text("Phone: ${req["phone"] ?: "—"}")
                                Text("Requested assignment: ${req["circuit"] ?: "—"} • ${req["church_name"] ?: "—"}")
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Button(enabled = !busy && id > 0 && accountRequestRole.isNotBlank(), onClick = {
                                        scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) {
                                                Backend.api.approveAccountRequest(id, mapOf(
                                                    "role" to accountRequestRole.trim(),
                                                    "circuit" to (req["circuit"]?.toString() ?: ""),
                                                    "church_name" to (req["church_name"]?.toString() ?: "")
                                                ))
                                            } }.onSuccess {
                                                message = it["message"]?.toString() ?: "Account approved."
                                                runCatching { withContext(Dispatchers.IO) { Backend.api.accountRequests() } }.onSuccess { accountRequestRows = it }
                                            }.onFailure { message = it.message ?: "Approval failed. Check role and assignment." }
                                            busy = false
                                        }
                                    }) { Text("Approve") }
                                    OutlinedButton(enabled = !busy && id > 0, onClick = {
                                        scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) { Backend.api.rejectAccountRequest(id, mapOf("review_note" to "Rejected by administrator in native app.")) } }
                                                .onSuccess {
                                                    message = it["message"]?.toString() ?: "Request rejected."
                                                    runCatching { withContext(Dispatchers.IO) { Backend.api.accountRequests() } }.onSuccess { accountRequestRows = it }
                                                }.onFailure { message = it.message ?: "Rejection failed." }
                                            busy = false
                                        }
                                    }) { Text("Reject") }
                                }
                            }
                        }
                    }
                    if (accountRequestRows.none { it["status"]?.toString() == "Pending" }) Text("No pending account requests.")
                }
                "Directory" -> {
                    Text("Church & Circuit Directory", style = MaterialTheme.typography.titleLarge)
                    Text("Browse the circuits and local churches available to your account.")
                    ActionButton("Load church directory", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.circuits() to Backend.api.membershipChurches() } }
                            .onSuccess { directoryCircuits = it.first; directoryChurches = it.second; message = "Directory refreshed." }
                            .onFailure { message = it.message ?: "Directory could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    Text("Circuits", style = MaterialTheme.typography.titleMedium)
                    RecordList(directoryCircuits, listOf("name", "status", "notes"))
                    Text("Local Churches", style = MaterialTheme.typography.titleMedium)
                    ChurchDirectoryList(directoryChurches)
                }
                "Members" -> {
                    Text("Church Membership Directory", style = MaterialTheme.typography.titleLarge)
                    Text("Search member records available to your account. Circuit and local-church restrictions are enforced by the diocesan server.")
                    OutlinedTextField(
                        value = memberSearch,
                        onValueChange = { memberSearch = it },
                        label = { Text("Search name, member ID, phone or church") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    ActionButton("Load membership statistics", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.membershipStatistics() } }
                            .onSuccess { membershipStats = it }
                            .onFailure { message = it.message ?: "Membership statistics unavailable." }
                    }
                    if (membershipStats.isNotEmpty()) {
                        val statisticKeys = listOf("total_members", "male", "female", "youth", "children", "baptised", "confirmed", "married", "new_members", "transferred", "relocated")
                        MembershipSummaryCards(membershipStats.filterKeys { it in statisticKeys })
                    }
                    ActionButton("Load members", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.members() } }
                            .onSuccess { memberDirectory = it; message = "${it.size} member records loaded." }
                            .onFailure { message = it.message ?: "Member directory could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    val query = memberSearch.trim().lowercase()
                    val filteredMembers = memberDirectory.filter { row ->
                        query.isBlank() || listOf("full_name", "member_id", "phone", "circuit", "church_name", "fellowship")
                            .any { key -> row[key]?.toString()?.lowercase()?.contains(query) == true }
                    }
                    Text("${filteredMembers.size} matching members", style = MaterialTheme.typography.labelMedium)
                    if (role == "Admin") {
                        Text("Church Office Appointments", style = MaterialTheme.typography.titleMedium)
                        Text("Select a member to view or record diocesan, circuit or local-church appointments.")
                        filteredMembers.forEach { row ->
                            ElevatedCard(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(10.dp)) {
                                    Text(row["full_name"]?.toString() ?: "Member", style = MaterialTheme.typography.titleSmall)
                                    Text("ID: ${row["member_id"] ?: "—"} • ${row["church_name"] ?: row["circuit"] ?: ""}")
                                    TextButton(onClick = {
                                        val id = (row["id"] as? Number)?.toInt()
                                        if (id != null) {
                                            appointmentMember = row
                                            scope.launch {
                                                runCatching { withContext(Dispatchers.IO) { Backend.api.memberAppointments(id) } }
                                                    .onSuccess { appointmentData = it; appointmentCircuit = row["circuit"]?.toString() ?: ""; appointmentChurch = row["church_name"]?.toString() ?: ""; message = "Appointments loaded." }
                                                    .onFailure { message = it.message ?: "Could not load appointments." }
                                            }
                                        } else message = "This member record has no database ID."
                                    }) { Text("Manage appointments") }
                                }
                            }
                        }
                        appointmentMember?.let { selectedMember ->
                            val memberId = (selectedMember["id"] as? Number)?.toInt()
                            Divider()
                            Text("Appointments: ${selectedMember["full_name"] ?: "Member"}", style = MaterialTheme.typography.titleMedium)
                            val appointmentRows = appointmentData["appointments"] as? List<Map<String, Any?>> ?: emptyList()
                            appointmentRows.forEach { appointment ->
                                ElevatedCard(Modifier.fillMaxWidth()) {
                                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Text(appointment["office"]?.toString() ?: "Church office", style = MaterialTheme.typography.titleSmall)
                                        Text("${appointment["level"] ?: ""} • ${appointment["circuit"] ?: "Diocesan"} • ${appointment["church_name"] ?: ""}")
                                        Text("Start: ${appointment["start_date"] ?: "—"}   End: ${appointment["end_date"] ?: "—"}")
                                        Text("Status: ${appointment["status"] ?: "—"}")
                                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                            TextButton(onClick = {
                                                appointmentEditingId = (appointment["id"] as? Number)?.toInt()
                                                appointmentOffice = appointment["office"]?.toString() ?: ""
                                                appointmentLevel = appointment["level"]?.toString() ?: "Local Church"
                                                appointmentCircuit = appointment["circuit"]?.toString() ?: ""
                                                appointmentChurch = appointment["church_name"]?.toString() ?: ""
                                                appointmentStart = appointment["start_date"]?.toString() ?: ""
                                                appointmentEnd = appointment["end_date"]?.toString() ?: ""
                                                appointmentNotes = appointment["notes"]?.toString() ?: ""
                                            }) { Text("Edit") }
                                            if (appointment["status"]?.toString() != "Terminated") {
                                                TextButton(onClick = {
                                                    val id = (appointment["id"] as? Number)?.toInt()
                                                    if (id != null) {
                                                        scope.launch {
                                                            busy = true
                                                            runCatching { withContext(Dispatchers.IO) {
                                                                Backend.api.terminateMemberAppointment(id, mapOf(
                                                                    "end_date" to java.time.LocalDate.now().toString(),
                                                                    "notes" to (appointment["notes"]?.toString() ?: "")
                                                                ))
                                                            } }.onSuccess {
                                                                Backend.api.memberAppointments(memberId!!).let { appointmentData = it }
                                                                message = "Appointment terminated."
                                                            }.onFailure { message = it.message ?: "Could not terminate appointment." }
                                                            busy = false
                                                        }
                                                    }
                                                }, enabled = !busy) { Text("Terminate") }
                                            }
                                        }
                                    }
                                }
                            }
                            Text(if (appointmentEditingId == null) "Add church office appointment" else "Edit selected appointment", style = MaterialTheme.typography.titleSmall)
                            OutlinedTextField(appointmentOffice, { appointmentOffice = it }, label = { Text("Office (use exact official title)") }, modifier = Modifier.fillMaxWidth())
                            Text("Valid offices: Bishop / Diocesan Executive; Lay President; Evangelism Minister; Presbyters; Ministers; Lay Preachers; Planting Officer; Diocesan Secretary; Circuit Coordinator; Local Church Evangelism Officer; Sunday School Teachers; Finance Officer; Conference Awardees; Diocesan Awardees; Friends of the Diocese; Auditor; Men Fellowship President; Women Fellowship President; Youth Fellowship President; Others", style = MaterialTheme.typography.bodySmall)
                            OutlinedTextField(appointmentLevel, { appointmentLevel = it }, label = { Text("Level: Diocesan, Circuit, or Local Church") }, modifier = Modifier.fillMaxWidth())
                            if (appointmentLevel != "Diocesan") OutlinedTextField(appointmentCircuit, { appointmentCircuit = it }, label = { Text("Circuit") }, modifier = Modifier.fillMaxWidth())
                            if (appointmentLevel == "Local Church") OutlinedTextField(appointmentChurch, { appointmentChurch = it }, label = { Text("Local church") }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(appointmentStart, { appointmentStart = it }, label = { Text("Start date (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(appointmentEnd, { appointmentEnd = it }, label = { Text("End date (optional, YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(appointmentNotes, { appointmentNotes = it }, label = { Text("Notes") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                            Button(enabled = !busy && memberId != null && appointmentStart.isNotBlank(), onClick = {
                                busy = true
                                scope.launch {
                                    runCatching { withContext(Dispatchers.IO) {
                                        if (appointmentEditingId != null) Backend.api.updateMemberAppointment(appointmentEditingId!!, mapOf(
                                            "office" to appointmentOffice.trim(), "level" to appointmentLevel.trim(),
                                            "circuit" to appointmentCircuit.trim(), "church_name" to appointmentChurch.trim(),
                                            "start_date" to appointmentStart.trim(), "end_date" to appointmentEnd.trim(),
                                            "status" to "Active", "notes" to appointmentNotes.trim()
                                        )) else Backend.api.createMemberAppointment(memberId!!, mapOf(
                                            "office" to appointmentOffice.trim(), "level" to appointmentLevel.trim(),
                                            "circuit" to appointmentCircuit.trim(), "church_name" to appointmentChurch.trim(),
                                            "start_date" to appointmentStart.trim(), "end_date" to appointmentEnd.trim(),
                                            "status" to "Active", "notes" to appointmentNotes.trim()
                                        ))
                                    } }.onSuccess {
                                        message = it["message"]?.toString() ?: "Appointment saved."
                                        appointmentEditingId = null
                                        runCatching { withContext(Dispatchers.IO) { Backend.api.memberAppointments(memberId!!) } }
                                            .onSuccess { appointmentData = it }
                                    }.onFailure { message = it.message ?: "Appointment could not be saved." }
                                    busy = false
                                }
                            }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Saving…" else "Save appointment") }
                        }
                    } else {
                        RecordList(filteredMembers, listOf("member_id", "full_name", "phone", "circuit", "church_name", "fellowship", "gender", "baptised", "confirmed", "marriage"))
                    }
                }
                "Reports" -> {
                    Text("Diocesan Reports & Performance", style = MaterialTheme.typography.titleLarge)
                    OutlinedTextField(reportYear, { reportYear = it.filter(Char::isDigit).take(4) }, label = { Text("Report year") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(reportCircuit, { reportCircuit = it }, label = { Text("Circuit (All or exact circuit name)") }, modifier = Modifier.fillMaxWidth())
                    ActionButton("Load diocesan report", busy) {
                        val year = reportYear.toIntOrNull() ?: java.time.LocalDate.now().year
                        runCatching { withContext(Dispatchers.IO) { Backend.api.reports(year, reportCircuit.trim().ifBlank { "All" }) } }
                            .onSuccess { reportData = it; message = "Report loaded for $year." }
                            .onFailure { message = it.message ?: "Report could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    val summary = reportData["summary"] as? Map<String, Any?> ?: emptyMap()
                    if (summary.isNotEmpty()) {
                        Text("Performance summary", style = MaterialTheme.typography.titleMedium)
                        KeyValueList(summary)
                    }
                    val finance = reportData["finance"] as? Map<String, Any?> ?: emptyMap()
                    if (finance.isNotEmpty()) {
                        Text("Finance summary", style = MaterialTheme.typography.titleMedium)
                        KeyValueList(finance)
                    }
                    val circuits = reportData["circuits"] as? List<Map<String, Any?>> ?: emptyList()
                    Text("Circuit performance", style = MaterialTheme.typography.titleMedium)
                    RecordList(circuits, listOf("circuit", "members", "plants", "launched", "outreach", "decisions", "joined"))
                    val roadmap = reportData["five_year"] as? List<Map<String, Any?>> ?: emptyList()
                    Text("Five-year church planting roadmap", style = MaterialTheme.typography.titleMedium)
                    RecordList(roadmap, listOf("year", "target", "planned", "launched", "remaining"))
                }
                "Governance" -> {
                    Text("Diocesan Governance & Reporting", style = MaterialTheme.typography.titleLarge)
                    Text("Reporting periods, circuit report submissions and action-point status.")
                    ActionButton("Refresh governance overview", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.reportingSummary() } }
                            .onSuccess { governanceData = it; message = "Governance overview refreshed." }
                            .onFailure { message = it.message ?: "Governance overview unavailable." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    if (governanceData.isNotEmpty()) {
                        Text("Reporting periods", style = MaterialTheme.typography.titleMedium)
                        val periods = governanceData["periods"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(periods, listOf("period_name", "start_date", "end_date", "submission_due", "status"))
                        Text("Circuit report status", style = MaterialTheme.typography.titleMedium)
                        val reportStatus = governanceData["report_status"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(reportStatus, listOf("status", "count"))
                        Text("Action-point status", style = MaterialTheme.typography.titleMedium)
                        val actionStatus = governanceData["action_status"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(actionStatus, listOf("status", "count"))
                        KeyValueList(mapOf("Recorded meetings" to governanceData["meetings"]))
                    }
                }
                "Conferences" -> {
                    Text("Diocesan Conference Centre", style = MaterialTheme.typography.titleLarge)
                    Text("View scheduled and live diocesan meetings and conferences.")
                    ActionButton("Refresh conferences", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.conferences() } }
                            .onSuccess { conferenceRows = it; message = "Conference schedule refreshed." }
                            .onFailure { message = it.message ?: "Conference schedule unavailable." }
                    }
                    if (role in setOf("Admin", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary")) {
                        Text("Schedule a conference", style = MaterialTheme.typography.titleMedium)
                        OutlinedTextField(conferenceTitle, { conferenceTitle = it }, label = { Text("Conference title") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceDate, { conferenceDate = it }, label = { Text("Date (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceStart, { conferenceStart = it }, label = { Text("Start time") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceEnd, { conferenceEnd = it }, label = { Text("End time") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceCircuit, { conferenceCircuit = it }, label = { Text("Circuit or Diocesan") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceAgenda, { conferenceAgenda = it }, label = { Text("Agenda") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                        Button(enabled = !busy && conferenceTitle.isNotBlank() && conferenceDate.isNotBlank(), onClick = {
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) { Backend.api.createConference(mapOf(
                                    "title" to conferenceTitle.trim(),
                                    "meeting_date" to conferenceDate.trim(),
                                    "start_time" to conferenceStart.trim(),
                                    "end_time" to conferenceEnd.trim(),
                                    "circuit" to conferenceCircuit.trim(),
                                    "agenda" to conferenceAgenda.trim()
                                )) } }
                                    .onSuccess {
                                        message = "Conference scheduled. Room code: " + (it["room_code"] ?: "")
                                        conferenceTitle = ""; conferenceAgenda = ""
                                        runCatching { withContext(Dispatchers.IO) { Backend.api.conferences() } }.onSuccess { conferenceRows = it }
                                    }
                                    .onFailure { message = it.message ?: "Conference could not be scheduled." }
                                busy = false
                            }
                        }) { Text("Schedule conference") }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    RecordList(conferenceRows, listOf("title", "meeting_type", "meeting_date", "start_time", "end_time", "circuit", "organizer", "status", "room_code", "agenda"))
                    Text("Open a conference", style = MaterialTheme.typography.titleMedium)
                    conferenceRows.forEach { room ->
                        val id = (room["id"] as? Number)?.toInt()
                        if (id != null) {
                            OutlinedButton(enabled = !busy, onClick = {
                                scope.launch {
                                    busy = true
                                    runCatching { withContext(Dispatchers.IO) { Backend.api.conferenceDetail(id) } }
                                        .onSuccess { conferenceDetail = it; conferenceSelectedId = id; message = "Conference room opened." }
                                        .onFailure { message = it.message ?: "Could not open conference." }
                                    busy = false
                                }
                            }) { Text("Open: " + (room["title"] ?: "Conference")) }
                        }
                    }
                    if (conferenceSelectedId != null && conferenceDetail.isNotEmpty()) {
                        val room = conferenceDetail["room"] as? Map<String, Any?> ?: emptyMap()
                        Text("Room: " + (room["room_code"] ?: ""), style = MaterialTheme.typography.titleMedium)
                        Text("Participants")
                        val participants = conferenceDetail["participants"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(participants, listOf("participant_name", "participant_role", "phone", "status"))
                        OutlinedTextField(conferenceParticipantName, { conferenceParticipantName = it }, label = { Text("Participant name") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(conferenceParticipantRole, { conferenceParticipantRole = it }, label = { Text("Role") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && conferenceParticipantName.isNotBlank(), onClick = {
                            val selectedId = conferenceSelectedId ?: return@Button
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) { Backend.api.addConferenceParticipant(selectedId, mapOf("participant_name" to conferenceParticipantName.trim(), "participant_role" to conferenceParticipantRole.trim())) } }
                                    .onSuccess { conferenceParticipantName = ""; conferenceParticipantRole = ""; runCatching { withContext(Dispatchers.IO) { Backend.api.conferenceDetail(selectedId) } }.onSuccess { conferenceDetail = it }; message = "Participant added." }
                                    .onFailure { message = it.message ?: "Could not add participant." }
                                busy = false
                            }
                        }) { Text("Add participant") }
                        Text("Live attendance / presence", style = MaterialTheme.typography.titleMedium)
                        Text("Check in to show that you are currently in this conference. Presence expires automatically if not refreshed.")
                        val presenceName = (profile["full_name"] ?: profile["name"] ?: profile["username"] ?: username).toString()
                        val presenceId = (profile["username"] ?: profile["id"] ?: username).toString()
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(enabled = !busy, onClick = {
                                val selectedId = conferenceSelectedId ?: return@Button
                                scope.launch {
                                    busy = true
                                    runCatching { withContext(Dispatchers.IO) { Backend.api.updateConferencePresence(selectedId, mapOf("participant_id" to presenceId, "participant_name" to presenceName, "audio_only" to true)) } }
                                        .onSuccess { runCatching { withContext(Dispatchers.IO) { Backend.api.conferencePresence(selectedId) } }.onSuccess { conferencePresenceRows = it }; message = "Conference attendance checked in." }
                                        .onFailure { message = it.message ?: "Could not check in." }
                                    busy = false
                                }
                            }) { Text("Check in") }
                            OutlinedButton(enabled = !busy, onClick = {
                                val selectedId = conferenceSelectedId ?: return@OutlinedButton
                                scope.launch {
                                    busy = true
                                    runCatching { withContext(Dispatchers.IO) { Backend.api.leaveConferencePresence(selectedId, presenceId) } }
                                        .onSuccess { runCatching { withContext(Dispatchers.IO) { Backend.api.conferencePresence(selectedId) } }.onSuccess { conferencePresenceRows = it }; message = "You have left the live attendance list." }
                                        .onFailure { message = it.message ?: "Could not leave attendance." }
                                    busy = false
                                }
                            }) { Text("Leave") }
                        }
                        ActionButton("Refresh live attendance", busy) {
                            val selectedId = conferenceSelectedId ?: return@ActionButton
                            runCatching { withContext(Dispatchers.IO) { Backend.api.conferencePresence(selectedId) } }
                                .onSuccess { conferencePresenceRows = it; message = "Live attendance refreshed." }
                                .onFailure { message = it.message ?: "Attendance list unavailable." }
                        }
                        Text("Currently present: ${conferencePresenceRows.size}")
                        RecordList(conferencePresenceRows, listOf("participant_name", "participant_id", "audio_only", "last_seen"))
                        Text("Conference messages")
                        val messages = conferenceDetail["messages"] as? List<Map<String, Any?>> ?: emptyList()
                        RecordList(messages, listOf("sender_name", "sender_role", "message", "created_at"))
                        OutlinedTextField(conferenceMessage, { conferenceMessage = it }, label = { Text("Write a message") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                        Button(enabled = !busy && conferenceMessage.isNotBlank(), onClick = {
                            val selectedId = conferenceSelectedId ?: return@Button
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) { Backend.api.sendConferenceMessage(selectedId, mapOf("message" to conferenceMessage.trim())) } }
                                    .onSuccess { conferenceMessage = ""; runCatching { withContext(Dispatchers.IO) { Backend.api.conferenceDetail(selectedId) } }.onSuccess { conferenceDetail = it }; message = "Conference message sent." }
                                    .onFailure { message = it.message ?: "Could not send conference message." }
                                busy = false
                            }
                        }) { Text("Send message") }
                    }
                }
                "User Administration" -> {
                    Text("User Account Administration", style = MaterialTheme.typography.titleLarge)
                    Text("Administrator-only account oversight. Changes are recorded by the diocesan server.")
                    ActionButton("Load user accounts", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.adminUsers() } }
                            .onSuccess { adminUserRows = it; message = "${it.size} user accounts loaded." }
                            .onFailure { message = it.message ?: "Could not load user accounts." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    adminUserRows.forEach { account ->
                        ElevatedCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(account["username"]?.toString() ?: "Account", style = MaterialTheme.typography.titleSmall)
                                Text("Role: ${account["role"] ?: ""}")
                                Text("Member: ${account["member_name"] ?: "Not linked"}  •  ID: ${account["official_member_code"] ?: ""}")
                                Text("Circuit: ${account["circuit"] ?: ""}  •  Church: ${account["church_name"] ?: ""}")
                                Text("Status: " + (if (account["active"] == true || account["active"]?.toString() == "1") "Active" else "Inactive"))
                                Text("Password change required: ${account["must_change_password"] ?: false}")
                                val uid = (account["id"] as? Number)?.toInt()
                                if (uid != null && uid != (profile["id"] as? Number)?.toInt()) {
                                    OutlinedButton(enabled = !busy, onClick = {
                                        scope.launch {
                                            busy = true
                                            runCatching { withContext(Dispatchers.IO) { Backend.api.toggleUser(uid) } }
                                                .onSuccess { runCatching { withContext(Dispatchers.IO) { Backend.api.adminUsers() } }.onSuccess { adminUserRows = it }; message = "Account status updated." }
                                                .onFailure { message = it.message ?: "Account status could not be changed." }
                                            busy = false
                                        }
                                    }) { Text(if (account["active"] == true || account["active"]?.toString() == "1") "Deactivate account" else "Activate account") }
                                }
                            }
                        }
                    }
                }
                "System" -> {
                    Text("System Health & Security", style = MaterialTheme.typography.titleLarge)
                    Text("Read-only diagnostics and security overview. Backup restoration and account changes remain protected on the web administration portal.")
                    ActionButton("Run system checks", busy) {
                        runCatching { withContext(Dispatchers.IO) { Triple(Backend.api.systemHealth(), Backend.api.securityStatus(), Backend.api.backupHistory()) } }
                            .onSuccess { healthData = it.first; securityData = it.second; backupRows = it.third; message = "System checks and backup history refreshed." }
                            .onFailure { message = it.message ?: "System checks could not be completed." }
                    }
                    if (role == "Admin") {
                        ActionButton("Create secure database backup", busy) {
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) { Backend.api.createSecurityBackup() } }
                                    .onSuccess { result ->
                                        message = "Backup created: " + (result["filename"] ?: "Completed")
                                        runCatching { withContext(Dispatchers.IO) { Backend.api.backupHistory() } }.onSuccess { backupRows = it }
                                    }
                                    .onFailure { message = it.message ?: "Backup could not be created." }
                                busy = false
                            }
                        }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    if (healthData.isNotEmpty()) {
                        Text("Application health", style = MaterialTheme.typography.titleMedium)
                        KeyValueList(mapOf("Overall status" to healthData["ok"], "Version" to healthData["version"], "Stage" to healthData["stage"], "Database integrity" to healthData["integrity"], "Generated" to healthData["generated_at"]))
                        val checks = healthData["checks"] as? Map<String, Any?> ?: emptyMap()
                        KeyValueList(checks)
                        Text("Missing tables: " + ((healthData["missing_tables"] as? List<*>)?.joinToString().orEmpty().ifBlank { "None" }))
                        Text("Schema issues: " + ((healthData["schema_issues"] as? List<*>)?.joinToString().orEmpty().ifBlank { "None" }))
                        val counts = healthData["counts"] as? Map<String, Any?> ?: emptyMap()
                        Text("Database record counts", style = MaterialTheme.typography.titleMedium)
                        KeyValueList(counts)
                    }
                    if (securityData.isNotEmpty()) {
                        Text("Security overview", style = MaterialTheme.typography.titleMedium)
                        KeyValueList(securityData.filterKeys { it != "latest_backup" })
                        val latest = securityData["latest_backup"] as? Map<String, Any?> ?: emptyMap()
                        if (latest.isNotEmpty()) KeyValueList(latest)
                    }
                    if (role in setOf("Admin", "Auditor")) {
                        Text("Data quality checks", style = MaterialTheme.typography.titleMedium)
                        ActionButton("Run data quality scan", busy) {
                            runCatching { withContext(Dispatchers.IO) { Backend.api.dataQuality() } }
                                .onSuccess { qualityData = it; message = "Data quality scan completed." }
                                .onFailure { message = it.message ?: "Data quality scan unavailable." }
                        }
                        if (qualityData.isNotEmpty()) {
                            KeyValueList(mapOf("Overall data quality" to qualityData["ok"], "Generated" to qualityData["generated_at"]))
                            Text("Checks", style = MaterialTheme.typography.titleSmall)
                            val checks = qualityData["checks"] as? List<Map<String, Any?>> ?: emptyList()
                            RecordList(checks, listOf("name", "count", "severity"))
                            Text("Issues requiring attention", style = MaterialTheme.typography.titleSmall)
                            val issues = qualityData["issues"] as? List<Map<String, Any?>> ?: emptyList()
                            RecordList(issues, listOf("name", "count", "severity"))
                        }
                        Text("Audit trail", style = MaterialTheme.typography.titleMedium)
                        ActionButton("Load recent audit records", busy) {
                            runCatching { withContext(Dispatchers.IO) { Backend.api.auditLog() } }
                                .onSuccess { auditRows = it; message = "${it.size} audit records loaded." }
                                .onFailure { message = it.message ?: "Audit records unavailable." }
                        }
                        RecordList(auditRows, listOf("happened_at", "username", "action", "table_name", "record_id", "details"))
                    }
                    Text("Database backup history", style = MaterialTheme.typography.titleMedium)
                    Text("Recent server backups. Backup restoration is intentionally not available in the mobile app.")
                    RecordList(backupRows, listOf("created_at", "created_by", "filename", "size_bytes", "backup_type", "status"))
                }
                "Finance" -> {
                    Text("Finance & Payments Centre", style = MaterialTheme.typography.titleLarge)
                    Text("Authorized finance access. Reconciliation actions remain protected by the diocesan server.")
                    ActionButton("Refresh finance records", busy) {
                        runCatching { withContext(Dispatchers.IO) { Triple(Backend.api.financeSummary(), Backend.api.paymentHistory(), Backend.api.paymentReconciliation()) } }
                            .onSuccess {
                                financeSummary = it.first
                                paymentRows = (it.second["payments"] as? List<Map<String, Any?>>) ?: emptyList()
                                reconciliationRows = (it.third["payments"] as? List<Map<String, Any?>>) ?: emptyList()
                                runCatching { withContext(Dispatchers.IO) { Backend.api.churchAccounts() } }
                                    .onSuccess { churchAccountRows = it }
                                message = "Finance records refreshed."
                            }.onFailure { message = it.message ?: "Finance records could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    val summary = financeSummary["summary"] as? Map<String, Any?> ?: emptyMap()
                    SummaryCards(summary)
                    Text("Church bank accounts", style = MaterialTheme.typography.titleMedium)
                    Text("Active diocesan, circuit and local church accounts available to your authorized role.")
                    RecordList(churchAccountRows, listOf("account_level", "circuit", "church_name", "bank_name", "account_name", "account_number", "currency", "purpose"))
                    if (role in setOf("Admin", "Finance Officer", "Evangelism Minister", "Circuit Coordinator", "Local Church Evangelism Officer")) {
                        Text("Register a church bank account", style = MaterialTheme.typography.titleMedium)
                        Text("Your role determines whether the account is registered at diocesan, circuit or local-church level.")
                        OutlinedTextField(accountBank, { accountBank = it }, label = { Text("Bank name") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(accountName, { accountName = it }, label = { Text("Account name") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(accountNumber, { accountNumber = it }, label = { Text("Account number") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(accountType, { accountType = it }, label = { Text("Account type (Current / Savings)") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(accountBranch, { accountBranch = it }, label = { Text("Bank branch (optional)") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(accountNotes, { accountNotes = it }, label = { Text("Notes (optional)") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && accountBank.isNotBlank() && accountName.isNotBlank() && accountNumber.isNotBlank(), onClick = {
                            scope.launch {
                                busy = true
                                runCatching { withContext(Dispatchers.IO) {
                                    Backend.api.createChurchAccount(mapOf(
                                        "bank_name" to accountBank.trim(),
                                        "account_name" to accountName.trim(),
                                        "account_number" to accountNumber.trim(),
                                        "account_type" to accountType.trim(),
                                        "branch" to accountBranch.trim(),
                                        "notes" to accountNotes.trim()
                                    ))
                                } }.onSuccess {
                                    accountBank = ""; accountName = ""; accountNumber = ""; accountBranch = ""; accountNotes = ""
                                    runCatching { withContext(Dispatchers.IO) { Backend.api.churchAccounts() } }
                                        .onSuccess { churchAccountRows = it }
                                    message = "Church bank account registered."
                                }.onFailure { message = it.message ?: "Could not register bank account." }
                                busy = false
                            }
                        }, modifier = Modifier.fillMaxWidth()) { Text("Register bank account") }
                    }
                    Text("Payment history", style = MaterialTheme.typography.titleMedium)
                    RecordList(paymentRows, listOf("reference", "status", "amount", "currency", "purpose", "donor_name", "circuit", "church_name", "created_at", "paid_at"))
                    Text("Payment reconciliation", style = MaterialTheme.typography.titleMedium)
                    Text("Only payments already confirmed as paid by the server can be reconciled into church income. Pending payments cannot be marked successful from this screen.")
                    if (reconciliationRows.isEmpty()) {
                        Text("No reconciliation records loaded.")
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            reconciliationRows.forEach { payment ->
                                ElevatedCard(Modifier.fillMaxWidth()) {
                                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                        Text(payment["reference"]?.toString() ?: "Payment", style = MaterialTheme.typography.titleSmall)
                                        Text("Status: " + (payment["payment_status"] ?: "Unknown"))
                                        Text("Amount: " + (payment["payment_amount"] ?: "") + " " + (payment["currency"] ?: ""))
                                        Text("Donor: " + (payment["donor_name"] ?: "Not supplied"))
                                        Text("Reconciliation: " + (payment["reconciliation_status"] ?: "Unknown"))
                                        if (payment["payment_status"]?.toString()?.equals("paid", true) == true && payment["income_id"] == null) {
                                            Button(enabled = !busy, onClick = {
                                                val ref = payment["reference"]?.toString().orEmpty()
                                                if (ref.isNotBlank()) {
                                                    busy = true
                                                    scope.launch {
                                                        runCatching { withContext(Dispatchers.IO) { Backend.api.reconcilePayment(ref) } }
                                                            .onSuccess { message = it["message"]?.toString() ?: "Payment reconciled." }
                                                            .onFailure { message = it.message ?: "Payment reconciliation failed." }
                                                        runCatching { withContext(Dispatchers.IO) { Backend.api.paymentReconciliation() } }
                                                            .onSuccess { reconciliationRows = (it["payments"] as? List<Map<String, Any?>>) ?: emptyList() }
                                                        busy = false
                                                    }
                                                }
                                            }) { Text("Reconcile into church income") }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                "Approvals" -> {
                    Text("Membership Registration Approvals", style = MaterialTheme.typography.titleLarge)
                    Text("Review pending applications. Approval creates the official member record and login using the existing server workflow.")
                    ActionButton("Load registrations", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.memberRegistrations() } }
                            .onSuccess { registrations = it; message = "${it.size} registration records loaded." }
                            .onFailure { message = it.message ?: "Registration list unavailable." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    RegistrationList(registrations, busy) { id, status ->
                        busy = true
                        scope.launch {
                            runCatching {
                                withContext(Dispatchers.IO) {
                                    Backend.api.reviewMemberRegistration(id, mapOf(
                                        "status" to status,
                                        "role" to "Member",
                                        "circuit" to "",
                                        "church_name" to "",
                                        "review_note" to "Reviewed in the native Android app."
                                    ))
                                }
                            }.onSuccess {
                                message = it["message"]?.toString() ?: "Registration updated."
                                runCatching { withContext(Dispatchers.IO) { Backend.api.memberRegistrations() } }
                                    .onSuccess { registrations = it }
                            }.onFailure { message = it.message ?: "Could not update registration." }
                            busy = false
                        }
                    }
                }
            }
            if (message.isNotBlank() && selected !in setOf("Feed", "Finance", "Approvals")) {
                Text(message, color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(12.dp))
            OutlinedButton(onClick = {
                Backend.clearLocalData()
                signedIn = false
                showStaffLogin = false
                username = ""
                password = ""
                currentPassword = ""
                newPassword = ""
                confirmPassword = ""
                busy = false
                message = ""
                selected = "Home"
                profile = emptyMap()
                dashboard = emptyMap()
                memberRecords = emptyMap()
                profilePhone = ""; profileBirthday = ""; profileAddress = ""
                profileProfession = ""; profileFellowship = ""
                idCard = emptyMap()
                attendanceSummary = emptyMap()
                attendanceRows = emptyList()
                attendanceRegisterMembers = emptyList()
                attendanceMemberSearch = ""
                givingRows = emptyList()
                feedRows = emptyList()
                eventRows = emptyList()
                notificationRows = emptyList()
                careThreads = emptyList(); careUnreadTotal = 0; careDetail = emptyMap()
                careSelectedId = null; careSubject = ""; careMessage = ""; careReply = ""
                financeSummary = emptyMap(); reportData = emptyMap(); governanceData = emptyMap()
                healthData = emptyMap(); securityData = emptyMap(); backupRows = emptyList()
                adminUserRows = emptyList(); accountRequestRows = emptyList()
                qualityData = emptyMap(); auditRows = emptyList()
                paymentRows = emptyList(); reconciliationRows = emptyList()
                churchAccountRows = emptyList()
                accountBank = ""; accountName = ""; accountNumber = ""; accountBranch = ""; accountNotes = ""
                conferenceRows = emptyList(); conferenceDetail = emptyMap(); conferenceSelectedId = null
                conferenceMessage = ""; conferenceParticipantName = ""; conferenceParticipantRole = ""
                conferencePresenceRows = emptyList()
                registrations = emptyList(); directoryChurches = emptyList(); directoryCircuits = emptyList()
                memberDirectory = emptyList(); memberSearch = ""; membershipStats = emptyMap()
                appointmentMember = null; appointmentData = emptyMap(); appointmentCircuit = ""
                appointmentChurch = ""; appointmentStart = ""; appointmentEnd = ""; appointmentNotes = ""
                appointmentEditingId = null
            }) { Text("Sign out") }
        }
    }
}


private fun networkAvailable(context: Context): Boolean {
    val manager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    val network = manager.activeNetwork ?: return false
    val capabilities = manager.getNetworkCapabilities(network) ?: return false
    return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
        capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
}

@Composable
private fun ActionButton(label: String, busy: Boolean, action: suspend () -> Unit) {
    val scope = rememberCoroutineScope()
    Button(enabled = !busy, onClick = { scope.launch { action() } }) {
        Text(if (busy) "Please wait…" else label)
    }
}

@Composable
private fun RegistrationList(
    rows: List<Map<String, Any?>>,
    busy: Boolean,
    onReview: (Int, String) -> Unit
) {
    if (rows.isEmpty()) {
        Text("No registration records loaded. Select Load registrations.")
        return
    }
    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.heightIn(max = 480.dp)) {
        items(rows) { row ->
            val id = (row["id"] as? Number)?.toInt() ?: row["id"]?.toString()?.toIntOrNull() ?: -1
            val status = row["status"]?.toString() ?: "Pending"
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(row["full_name"]?.toString() ?: "Applicant", style = MaterialTheme.typography.titleMedium)
                    Text("Registration: ${row["registration_id"] ?: id}")
                    Text("Circuit: ${row["circuit"] ?: "—"}")
                    Text("Local Church: ${row["church_name"] ?: "—"}")
                    Text("Phone: ${row["phone"] ?: "—"}")
                    Text("Status: $status")
                    if (status != "Approved" && status != "Rejected" && id > 0) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(enabled = !busy, onClick = { onReview(id, "Approved") }) { Text("Approve as Member") }
                            OutlinedButton(enabled = !busy, onClick = { onReview(id, "Rejected") }) { Text("Reject") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun KeyValueList(values: Map<String, Any?>) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.heightIn(max = 520.dp)) {
        items(values.entries.toList()) { entry ->
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text(entry.key, style = MaterialTheme.typography.labelMedium)
                    Text(entry.value?.toString() ?: "—")
                }
            }
        }
    }
}



private fun loadOfflineDevotionalRows(context: Context): List<Map<String, String>> {
    val directory = File(context.filesDir, "offline_devotional")
    val collections = listOf("english_hymns", "yoruba_hymns", "akokun", "bible_verses", "canticles", "communion_english", "communion_yoruba", "creeds")
    val output = mutableListOf<Map<String, String>>()
    collections.forEach { collection ->
        val file = File(directory, collection + ".json")
        if (!file.exists()) return@forEach
        runCatching {
            val array = JSONArray(file.readText())
            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue
                val payload = item.optJSONObject("payload") ?: JSONObject()
                val body = buildString {
                    listOf("reference", "heading", "verse", "content", "firstline", "lyrics", "chorus").forEach { key ->
                        val value = payload.optString(key)
                        if (value.isNotBlank()) append(value).append("\n\n")
                    }
                    val stanzas = payload.optJSONArray("stanzas")
                    if (stanzas != null) for (s in 0 until stanzas.length()) append(stanzas.optString(s)).append("\n\n")
                }.trim()
                output.add(mapOf(
                    "title" to item.optString("title", "Church resource"),
                    "collection" to collection.replace('_', ' '),
                    "content" to body,
                    "audio_file" to item.optString("audio_file")
                ))
            }
        }
    }
    val daily = File(directory, "daily_devotion.json")
    if (daily.exists()) runCatching {
        val root = JSONObject(daily.readText())
        val verse = root.optJSONObject("verse") ?: JSONObject()
        val hymn = root.optJSONObject("hymn") ?: JSONObject()
        if (verse.length() > 0) output.add(0, mapOf(
            "title" to ("Scripture of the Day · " + verse.optString("reference")),
            "collection" to "daily scripture",
            "content" to verse.optString("text"),
            "audio_file" to ""
        ))
        if (hymn.length() > 0) output.add(1.coerceAtMost(output.size), mapOf(
            "title" to ("Hymn of the Day · " + hymn.optString("title")),
            "collection" to "daily hymn",
            "content" to hymn.optString("lyrics"),
            "audio_file" to ""
        ))
    }
    return output
}

private fun loadOfflineMediaRows(context: Context): List<Map<String, String>> = runCatching {
    val file = File(OfflineModuleManager.offlineMediaDirectory(context), "index.json")
    val array = if (file.exists()) JSONArray(file.readText()) else JSONArray()
    (0 until array.length()).mapNotNull { index ->
        val item = array.optJSONObject(index) ?: return@mapNotNull null
        mapOf(
            "title" to item.optString("title"),
            "description" to item.optString("description"),
            "mime_type" to item.optString("mime_type"),
            "media_type" to item.optString("media_type"),
            "file" to item.optString("file")
        )
    }
}.getOrDefault(emptyList())

@Composable
private fun PublicOfflineLibrary(online: Boolean, onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var resources by remember { mutableStateOf(loadOfflineDevotionalRows(context)) }
    var media by remember { mutableStateOf(loadOfflineMediaRows(context)) }
    var selected by remember { mutableStateOf<Map<String, String>?>(null) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        TextButton(onClick = onBack) { Text("← Return to diocesan homepage") }
        Text("MCN Delta South Diocese", style = MaterialTheme.typography.headlineSmall)
        Text("Offline Worship & Scripture Library", style = MaterialTheme.typography.titleLarge)
        Text("Download public hymns, Scripture, worship books, recordings and church media while connected. Saved readings remain on this phone.")
        Button(enabled = online && !busy, onClick = {
            busy = true
            message = "Downloading all devotional collections…"
            scope.launch {
                val result = withContext(Dispatchers.IO) {
                    runCatching {
                        val count = OfflineModuleManager.downloadAllDevotionalResources(context)
                        OfflineModuleManager.downloadDailyDevotion(context)
                        OfflineModuleManager.downloadLectionary(context)
                        count
                    }
                }
                resources = withContext(Dispatchers.IO) { loadOfflineDevotionalRows(context) }
                message = result.fold({ "${it} devotional resources and today's Scripture and hymn are saved." }, { it.message ?: "Some resources could not be downloaded." })
                busy = false
            }
        }, modifier = Modifier.fillMaxWidth()) { Text("Download Hymns, Scripture & Worship Books") }
        Button(enabled = online && !busy, onClick = {
            busy = true
            message = "Downloading hymn recordings…"
            scope.launch {
                val result = withContext(Dispatchers.IO) { runCatching { OfflineModuleManager.downloadHymnAudio(context) } }
                resources = withContext(Dispatchers.IO) { loadOfflineDevotionalRows(context) }
                message = result.fold({ "Hymn audio download finished. ${it} hymn records checked." }, { it.message ?: "Hymn audio could not be downloaded." })
                busy = false
            }
        }, modifier = Modifier.fillMaxWidth()) { Text("Download Hymn Audio") }
        Button(enabled = online && !busy, onClick = {
            runCatching {
                val bibleUrl = BuildConfig.API_BASE_URL + "devotional-centre/holy-bible"
                context.startActivity(
                    Intent(Intent.ACTION_VIEW, android.net.Uri.parse(bibleUrl))
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
                message = "Opening the World English Bible (WEB) reader. Scripture text loads from the WEB public-domain Bible service."
            }.onFailure { message = it.message ?: "Could not open the WEB Bible reader." }
        }, modifier = Modifier.fillMaxWidth()) { Text("Open World English Bible (WEB)") }
        Text("Church Media Library", style = MaterialTheme.typography.titleMedium)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            listOf("audio", "video", "document").forEach { type ->
                OutlinedButton(
                    enabled = online && !busy,
                    onClick = {
                        busy = true
                        message = "Downloading published $type files…"
                        scope.launch {
                            val result = withContext(Dispatchers.IO) { runCatching { OfflineModuleManager.downloadMediaCategory(context, type) } }
                            media = withContext(Dispatchers.IO) { loadOfflineMediaRows(context) }
                            message = result.fold({ "${it} $type item(s) saved for offline use." }, { it.message ?: "The $type module could not be downloaded." })
                            busy = false
                        }
                    },
                    modifier = Modifier.weight(1f)
                ) { Text(type.replaceFirstChar { it.uppercase() }) }
            }
        }
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
        if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.primary)
        Text("Saved readings (${resources.size})", style = MaterialTheme.typography.titleMedium)
        if (resources.isEmpty()) Text("No devotional collections have been downloaded yet.")
        LazyColumn(Modifier.heightIn(max = 430.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(resources) { item ->
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f)) {
                            Text(item["title"] ?: "Church resource")
                            Text(item["collection"] ?: "", style = MaterialTheme.typography.bodySmall)
                        }
                        TextButton(onClick = { selected = item }) { Text("Read") }
                    }
                }
            }
        }
        Text("Saved media (${media.size})", style = MaterialTheme.typography.titleMedium)
        media.forEach { item ->
            ElevatedCard(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(Modifier.weight(1f)) {
                        Text(item["title"] ?: "Church media")
                        Text(item["media_type"] ?: "", style = MaterialTheme.typography.bodySmall)
                    }
                    TextButton(onClick = {
                        runCatching {
                            val file = File(OfflineModuleManager.offlineMediaDirectory(context), item["file"].orEmpty())
                            val uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", file)
                            val mime = item["mime_type"].orEmpty().ifBlank { "*/*" }
                            context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
                        }.onFailure { message = it.message ?: "Could not open saved media." }
                    }) { Text("Open") }
                }
            }
        }
    }
    selected?.let { item ->
        AlertDialog(
            onDismissRequest = { selected = null },
            title = { Text(item["title"] ?: "Church resource") },
            text = {
                Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    Text(item["content"].orEmpty().ifBlank { "No reading text was included in this resource." })
                }
            },
            confirmButton = {
                Row {
                    val audio = item["audio_file"].orEmpty()
                    if (audio.isNotBlank()) TextButton(onClick = {
                        runCatching {
                            val file = File(context.filesDir, "offline_devotional/" + audio)
                            val uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", file)
                            context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "audio/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK))
                        }.onFailure { message = it.message ?: "Could not play hymn audio." }
                    }) { Text("Play audio") }
                    TextButton(onClick = { selected = null }) { Text("Close") }
                }
            }
        )
    }
}

@Composable
private fun PublicDiocesanHomepage(online: Boolean, offlineDownloadBusy: Boolean, onStaffLogin: () -> Unit, onOfflineDownload: () -> Unit, onBackPressed: () -> Unit) {
    val context = LocalContext.current
    var pageError by remember { mutableStateOf(false) }
    var pageLoading by remember { mutableStateOf(true) }
    var webView by remember { mutableStateOf<WebView?>(null) }
    BackHandler(enabled = webView?.canGoBack() == true) { webView?.goBack() }
    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                WebView(ctx).apply {
                    settings.javaScriptEnabled = true
                    settings.userAgentString = settings.userAgentString + " MCNDeltaSouthAndroid"
                    settings.domStorageEnabled = true
                    settings.loadsImagesAutomatically = true
                    settings.javaScriptCanOpenWindowsAutomatically = true
                    settings.setSupportMultipleWindows(false)
                    settings.mediaPlaybackRequiresUserGesture = false
                    settings.useWideViewPort = true
                    settings.loadWithOverviewMode = false
                    settings.allowFileAccess = false
                    settings.allowContentAccess = true
                    settings.cacheMode = if (online) android.webkit.WebSettings.LOAD_DEFAULT else android.webkit.WebSettings.LOAD_CACHE_ELSE_NETWORK
                    isFocusable = true
                    isFocusableInTouchMode = true
                    isVerticalScrollBarEnabled = true
                    isHorizontalScrollBarEnabled = false
                    overScrollMode = android.view.View.OVER_SCROLL_IF_CONTENT_SCROLLS
                    setLayerType(android.view.View.LAYER_TYPE_HARDWARE, null)
                    webViewClient = object : WebViewClient() {
                        override fun shouldOverrideUrlLoading(view: WebView, request: android.webkit.WebResourceRequest): Boolean {
                            if (request.url.scheme == "mcn-app" && request.url.host == "offline") {
                                onOfflineDownload()
                                return true
                            }
                            if (request.url.scheme == "mcn-app" && request.url.host == "staff-login") {
                                onStaffLogin()
                                return true
                            }
                            return super.shouldOverrideUrlLoading(view, request)
                        }
                        override fun shouldInterceptRequest(view: WebView, request: android.webkit.WebResourceRequest): android.webkit.WebResourceResponse? {
                            if (!online) {
                                val cachedBible = OfflineModuleManager.cachedWebBibleBooks(ctx, request.url.toString())
                                    ?: OfflineModuleManager.cachedWebBibleChapter(ctx, request.url.toString())
                                if (cachedBible != null) {
                                    return android.webkit.WebResourceResponse(
                                        "application/json", "UTF-8", 200, "OK",
                                        mapOf("Access-Control-Allow-Origin" to "*", "Access-Control-Allow-Methods" to "GET, OPTIONS"),
                                        cachedBible.inputStream()
                                    )
                                }
                            }
                            return super.shouldInterceptRequest(view, request)
                        }
                        override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
                            pageLoading = true
                            pageError = false
                        }
                        override fun onPageFinished(view: WebView, url: String?) {
                            pageLoading = false
                        }
                        override fun onReceivedError(view: WebView, request: android.webkit.WebResourceRequest, error: android.webkit.WebResourceError) {
                            if (request.isForMainFrame) {
                                pageLoading = false
                                pageError = true
                            }
                        }
                    }
                    webChromeClient = WebChromeClient()
                    loadUrl(BuildConfig.API_BASE_URL)
                    webView = this
                }
            },
            update = { view ->
                val cacheMode = if (online) android.webkit.WebSettings.LOAD_DEFAULT else android.webkit.WebSettings.LOAD_CACHE_ELSE_NETWORK
                if (view.settings.cacheMode != cacheMode) {
                    view.settings.cacheMode = cacheMode
                    if (!view.url.isNullOrBlank()) view.reload()
                }
                if (view.url.isNullOrBlank()) view.loadUrl(BuildConfig.API_BASE_URL)
            }
        )
        if (pageLoading || offlineDownloadBusy) {
            LinearProgressIndicator(Modifier.fillMaxWidth().align(androidx.compose.ui.Alignment.TopCenter))
        }
        if (pageError) {
            ElevatedCard(Modifier.align(androidx.compose.ui.Alignment.Center).padding(24.dp)) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("The diocesan homepage could not be reached.", style = MaterialTheme.typography.titleMedium)
                    Text("Check your internet connection and try again.")
                    Button(onClick = { pageError = false; pageLoading = true; webView?.reload() }) { Text("Retry homepage") }
                }
            }
        }

    }

}

@Composable
private fun DashboardCards(values: Map<String, Any?>) {
    val labels = mapOf(
        "active_plants" to "Active Church Plants",
        "appreciations" to "Appreciations",
        "balance" to "Available Balance",
        "calendar" to "Calendar & Events",
        "churches" to "Local Churches",
        "contact_followups" to "Contact Follow-ups",
        "expenses" to "Total Expenses",
        "income" to "Total Income",
        "incomes" to "Total Income",
        "members" to "Registered Members",
        "outreach" to "Outreach Activities",
        "commitments" to "Commitments",
        "testimonies" to "Testimonies",
        "trust_fund" to "Evangelism Trust Fund"
    )
    fun prettyValue(key: String, value: Any?): String {
        if (value == null) return "—"
        if (value is Number) {
            val amountMetric = key.contains("balance", true) || key.contains("income", true) ||
                key.contains("expense", true) || key.contains("fund", true) ||
                key.contains("amount", true) || key.contains("donation", true)
            val number = value.toDouble()
            return if (amountMetric) "₦" + String.format("%,.2f", number)
            else if (number % 1.0 == 0.0) String.format("%,.0f", number)
            else String.format("%,.1f", number)
        }
        return value.toString()
    }
    val entries = values.entries.filter { it.value !is Map<*, *> && it.value !is List<*> }
    if (entries.isEmpty()) {
        Text("Your diocesan dashboard is ready. Pull down or tap Refresh dashboard to load the latest figures.")
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        entries.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                pair.forEach { entry ->
                    ElevatedCard(Modifier.weight(1f), colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                labels[entry.key] ?: entry.key.replace('_', ' ').split(' ').joinToString(" ") { word -> word.replaceFirstChar { it.uppercase() } },
                                style = MaterialTheme.typography.labelLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(prettyValue(entry.key, entry.value), style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }
                if (pair.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}


@Composable
private fun RecordList(rows: List<Map<String, Any?>>, fields: List<String>) {
    if (rows.isEmpty()) {
        Text("No records loaded yet.")
    } else {
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.heightIn(max = 440.dp)) {
            items(rows) { row ->
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        fields.filter { row[it] != null && row[it].toString().isNotBlank() }.forEach { key ->
                            Text(key.replace('_', ' ').replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                            Text(row[key].toString(), style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryCards(summary: Map<String, Any?>) {
    val labels = listOf(
        "income_total" to "Total income",
        "expense_total" to "Total expenses",
        "net_balance" to "Net balance",
        "paid_online_total" to "Online payments",
        "matched_online_total" to "Matched online",
        "unmatched_online_total" to "Unmatched online"
    )
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        labels.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                pair.forEach { (key, label) ->
                    ElevatedCard(Modifier.weight(1f)) {
                        Column(Modifier.padding(12.dp)) {
                            Text(label, style = MaterialTheme.typography.labelSmall)
                            Text("₦" + String.format("%,.2f", (summary[key] as? Number)?.toDouble() ?: 0.0), style = MaterialTheme.typography.titleMedium)
                        }
                    }
                }
            }
        }
    }
}


@Composable
private fun ChurchDirectoryList(rows: List<Map<String, Any?>>) {
    if (rows.isEmpty()) {
        Text("No church records loaded. Select Load church directory.")
        return
    }
    val grouped = rows.groupBy { it["circuit"]?.toString().orEmpty().ifBlank { "Unassigned Circuit" } }.toSortedMap()
    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.heightIn(max = 520.dp)) {
        grouped.forEach { (circuit, churches) ->
            item(key = circuit) {
                Text(circuit + " • " + churches.size + " churches", style = MaterialTheme.typography.titleMedium)
            }
            items(churches) { church ->
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp)) {
                        Text(church["church_name"]?.toString() ?: "Local Church", style = MaterialTheme.typography.bodyLarge)
                        Text(circuit, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }
    }
}

@Composable
private fun MembershipSummaryCards(stats: Map<String, Any?>) {
    val labels = listOf(
        "total_members" to "Total members", "male" to "Male", "female" to "Female",
        "youth" to "Youth", "children" to "Children", "baptised" to "Baptised",
        "confirmed" to "Confirmed", "married" to "Married", "new_members" to "New members",
        "transferred" to "Transferred", "relocated" to "Relocated"
    )
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        labels.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                pair.forEach { (key, label) ->
                    ElevatedCard(Modifier.weight(1f)) {
                        Column(Modifier.padding(12.dp)) {
                            Text(label, style = MaterialTheme.typography.labelSmall)
                            Text((stats[key] ?: 0).toString(), style = MaterialTheme.typography.titleLarge)
                        }
                    }
                }
                if (pair.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun MemberIdCard(data: Map<String, Any?>) {
    ElevatedCard(Modifier.fillMaxWidth(), colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("METHODIST CHURCH NIGERIA", style = MaterialTheme.typography.titleMedium)
            Text("DELTA SOUTH DIOCESE", style = MaterialTheme.typography.titleLarge)
            HorizontalDivider()
            Text(data["full_name"]?.toString() ?: "Member", style = MaterialTheme.typography.headlineSmall)
            Text("MEMBER ID: ${data["member_id"] ?: "—"}", style = MaterialTheme.typography.titleMedium)
            Text("Office / Position: ${data["role_position"] ?: "Member"}")
            Text("Circuit: ${data["circuit"] ?: "—"}")
            Text("Local Church: ${data["church_name"] ?: "—"}")
            Text("Fellowship: ${data["fellowship"] ?: "—"}")
            Text("Present this card as proof of diocesan membership.", style = MaterialTheme.typography.bodySmall)
        }
    }
}
