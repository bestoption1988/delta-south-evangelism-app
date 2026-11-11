// Release build trigger: mobile navigation and offline reader fixes.
package ng.mcn.deltasouth.evangelism

import android.os.Bundle
import android.util.Log
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

private fun offlinePageArchiveFile(context: Context, url: String): File {
    val uri = android.net.Uri.parse(url)
    val key = (uri.encodedPath.orEmpty() + "?" + uri.encodedQuery.orEmpty())
        .hashCode().toString().replace("-", "n")
    return File(File(context.filesDir, "offline_homepage/pages"), "$key.mht")
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Always render the native shell first. Secure storage and WebView service-worker
        // setup are guarded so a device-specific keystore/WebView failure cannot close the app.
        setContent { MaterialTheme { NativeDioceseApp() } }

        Thread {
            try {
                Backend.initialize(applicationContext)
            } catch (error: Throwable) {
                Log.e("DeltaSouthStartup", "Secure session storage initialization failed", error)
            }
            try {
                android.webkit.ServiceWorkerController.getInstance().setServiceWorkerClient(
                    object : android.webkit.ServiceWorkerClient() {
                        override fun shouldInterceptRequest(request: android.webkit.WebResourceRequest): android.webkit.WebResourceResponse? {
                            OfflineDevotionalPage.fileResponse(applicationContext, request.url.toString())?.let { return it }
                            if (!networkAvailable(applicationContext)) {
                                val localBible = OfflineModuleManager.cachedBibleModuleResponse(applicationContext, request.url.toString())
                                if (localBible != null) {
                                    return android.webkit.WebResourceResponse(
                                        "application/json", "UTF-8", 200, "OK",
                                        mapOf("Access-Control-Allow-Origin" to "*", "Access-Control-Allow-Methods" to "GET, OPTIONS"),
                                        java.io.ByteArrayInputStream(localBible)
                                    )
                                }
                            }
                            return null
                        }
                    }
                )
            } catch (error: Throwable) {
                Log.e("DeltaSouthStartup", "WebView offline service-worker setup failed", error)
            }
        }.start()
        // Clean legacy files and migrate existing downloads after first render, on IO.
        Thread {
            runCatching { OfflineModuleManager.removeLegacyBibleFiles(applicationContext) }
            runCatching { OfflineModuleManager.migrateToCardFolders(applicationContext) }
            // Background refresh is disabled: users update only when they deliberately choose Update.
            runCatching {
                androidx.work.WorkManager.getInstance(applicationContext)
                    .cancelUniqueWork("mcn-delta-south-offline-refresh")
                androidx.work.WorkManager.getInstance(applicationContext)
                    .cancelUniqueWork("mcn-delta-south-offline-refresh-now")
            }
        }.start()
    }
}

@Composable
private fun NativeDioceseApp() {
    val appContext = LocalContext.current
    var online by remember { mutableStateOf(networkAvailable(appContext)) }
    var downloadBusy by remember { mutableStateOf(false) }
    var downloadMessage by remember { mutableStateOf("") }
    var downloadProgress by remember { mutableIntStateOf(0) }
    var downloadStage by remember { mutableStateOf("Waiting to download…") }
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
    // First connected launch creates the on-device package once. Later launches never
    // refresh from Naijacloud automatically; refresh is user-initiated from the homepage.
    LaunchedEffect(signedIn, online) {
        if (signedIn) {
            if (online) {
                runCatching { withContext(Dispatchers.IO) { OfflineAttendanceQueue.syncPending(appContext) } }
                    .onSuccess { pendingAttendanceCount = OfflineAttendanceQueue.pendingCount(appContext) }
            }
            runCatching { withContext(Dispatchers.IO) { Backend.api.dashboard() } }
                .onSuccess { dashboard = it }
                .onFailure { message = it.message ?: "Dashboard will load from saved records when offline." }
        }
        // Do not launch the large first-time media package while the public
        // homepage is starting. On some Android devices the simultaneous media,
        // Bible and archive work can exhaust memory and cause Android to kill the app.
        // The user can deliberately start this package from Update Offline Content.

    }
    BackHandler(enabled = signedIn && selected != "Home") { selected = "Home"; message = "" }
    val role = (profile["role"] ?: "").toString()
    val financeRoles = setOf("Admin", "Finance Officer", "Auditor", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary")
    val canReview = role == "Admin" || role == "Evangelism Minister"

    if (!signedIn && !showStaffLogin) {
        PublicDiocesanHomepage(
            online = online,
            offlineDownloadBusy = downloadBusy,
            offlineDownloadProgress = downloadProgress,
            offlineDownloadStage = downloadStage,
            onStaffLogin = { showStaffLogin = true },
            onOfflineDownload = { homepageView ->
                if (online && !downloadBusy) {
                    downloadBusy = true
                    downloadMessage = "Updating the saved homepage and offline content…"
                    downloadProgress = 0
                    downloadStage = "Checking for updated diocesan content…"
                    // Only this deliberate action contacts the live homepage for a fresh copy.
                    homepageView.settings.cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
                    homepageView.loadUrl(BuildConfig.API_BASE_URL)
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            runCatching {
                                OfflineModuleManager.downloadAll(appContext) { stage, percent ->
                                    scope.launch(Dispatchers.Main) { downloadStage = stage; downloadProgress = percent }
                                }
                            }
                        }
                        result.onSuccess { summary ->
                            val offlinePrefs = appContext.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
                            val bibleModules = offlinePrefs.getInt("last_uploaded_bible_module_count", 0)
                            offlinePrefs.edit().putBoolean("initial_download_complete", true).apply()
                            downloadMessage = "Offline update saved: ${summary.downloaded} data sets, ${summary.mediaDownloaded} media files, ${bibleModules} uploaded Bible modules, ${summary.unavailable} restricted items and ${summary.failed} failed."
                            android.widget.Toast.makeText(appContext, downloadMessage, android.widget.Toast.LENGTH_LONG).show()
                        }.onFailure { error ->
                            downloadMessage = error.message ?: "The offline package could not be updated."
                            android.widget.Toast.makeText(appContext, downloadMessage, android.widget.Toast.LENGTH_LONG).show()
                        }
                        // Return to the on-device homepage when the deliberate update is finished.
                        // Return to the same real homepage, preferring the latest archive saved
                        // during this explicit update and otherwise the APK-bundled first-install copy.
                        homepageView.post {
                            homepageView.settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                            val savedHomepage = File(appContext.filesDir, "offline_homepage/diocesan-homepage.mht")
                            if (savedHomepage.isFile && savedHomepage.length() > 0L) {
                                homepageView.loadUrl(android.net.Uri.fromFile(savedHomepage).toString())
                            } else {
                                homepageView.loadUrl("file:///android_asset/offline-home/index.html")
                            }
                        }
                        downloadBusy = false
                    }
                }
            },
            onBackPressed = { }
        )
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
            addAll(listOf("Home", "Profile", "Attendance", "Giving", "Feed", "Updates", "Member Care", "Directory"))
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



@Composable
private fun PublicDiocesanHomepage(online: Boolean, offlineDownloadBusy: Boolean, offlineDownloadProgress: Int, offlineDownloadStage: String, onStaffLogin: () -> Unit, onOfflineDownload: (WebView) -> Unit, onBackPressed: () -> Unit) {
    val context = LocalContext.current
    val onlineState by rememberUpdatedState(online)
    var pageError by remember { mutableStateOf(false) }
    var pageErrorDetails by remember { mutableStateOf("The connection to the diocesan website failed.") }
    var pageLoading by remember { mutableStateOf(true) }
    var webView by remember { mutableStateOf<WebView?>(null) }
    fun openSavedDiocesanHome(target: WebView?) {
        if (target == null) return
        target.post {
            // Always open the homepage shipped inside this APK. Older app installs may
            // contain a stale MHTML snapshot from a previous broken release; preferring
            // that file makes every newer APK appear unchanged even after its assets are fixed.
            target.settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
            val staleArchive = File(context.filesDir, "offline_homepage/diocesan-homepage.mht")
            if (staleArchive.exists()) {
                runCatching { staleArchive.delete() }
            }
            target.loadUrl("file:///android_asset/offline-home/index.html")
        }
    }
    BackHandler(enabled = webView?.canGoBack() == true) { webView?.goBack() }
    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                // Read this flag from WebView request worker threads instead of calling view.url.
                val localArchiveActive = java.util.concurrent.atomic.AtomicBoolean(false)
                WebView(ctx).apply {
                    settings.javaScriptEnabled = true
                    // Identify this WebView to the diocesan homepage so Android-only UI is selected.
                    // Keep the normal Android browser identity and append the app marker used by public_home.html.
                    settings.userAgentString = settings.userAgentString + " MCNDeltaSouthAndroid"
                    settings.domStorageEnabled = true
                    settings.loadsImagesAutomatically = true
                    // Never allow target=_blank or window.open() to create a second browser window.
                    // All diocesan pages and links must remain in this app's single WebView.
                    settings.javaScriptCanOpenWindowsAutomatically = false
                    settings.setSupportMultipleWindows(false)
                    settings.mediaPlaybackRequiresUserGesture = false
                    settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                    settings.useWideViewPort = true
                    settings.loadWithOverviewMode = false
                    settings.allowFileAccess = true
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
                            val uri = request.url
                            // The online server may return 404 for its homepage while the
                            // installed app still has usable local libraries. Keep navigation
                            // inside the app and show the on-device library instead of a raw 404.
                            val rawLocalPath = uri.path.orEmpty()
                            // Daily homepage shortcuts must open their actual saved libraries,
                            // not the Devotional Centre landing page.
                            val localPath = when {
                                rawLocalPath == "/devotional-centre" && uri.fragment == "uploaded-bible-library" -> "/devotional-centre/holy-bible"
                                rawLocalPath == "/devotional-centre" && uri.fragment == "english-methodist-hymns" -> "/devotional-centre/collection/english-hymns"
                                rawLocalPath == "/devotional-centre/english-hymns" -> "/devotional-centre/collection/english-hymns"
                                rawLocalPath == "/bible" || rawLocalPath == "/scripture" -> "/devotional-centre/holy-bible"
                                rawLocalPath == "/hymns" || rawLocalPath == "/hymn-library" -> "/devotional-centre/collection/english-hymns"
                                else -> rawLocalPath
                            }
                            val bundledPagePath = if (uri.scheme == "file" &&
                                localPath.startsWith("/android_asset/offline-home/")) {
                                "/" + localPath.removePrefix("/android_asset/offline-home/").substringBefore('?')
                            } else ""
                            val resolvedOfflinePath = when {
                                localPath.startsWith("/devotional-centre") || localPath == "/media-library" ||
                                    localPath == "/fellowships" || localPath.startsWith("/fellowship/") -> localPath
                                bundledPagePath.startsWith("/devotional-centre") || bundledPagePath == "/media-library" ||
                                    bundledPagePath == "/fellowships" || bundledPagePath.startsWith("/fellowship/") -> bundledPagePath
                                else -> ""
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "home") {
                                openSavedDiocesanHome(view)
                                return true
                            }
                            if (uri.host == "offline.mcn-app" &&
                                (localPath.isBlank() || localPath == "/" ||
                                 localPath == "/fellowships" || localPath.startsWith("/fellowship/") ||
                                 localPath.startsWith("/devotional-centre") || localPath == "/media-library")) {
                                view.settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                                view.loadDataWithBaseURL("https://offline.mcn-app/", OfflineDevotionalPage.render(view.context, localPath.ifBlank { "/" }, uri.getQueryParameter("q").orEmpty(), uri.getQueryParameter("translation").orEmpty()), "text/html", "UTF-8", null)
                                return true
                            }
                            if (resolvedOfflinePath.isNotBlank()) {
                                val html = OfflineDevotionalPage.render(view.context, resolvedOfflinePath, uri.getQueryParameter("q").orEmpty(), uri.getQueryParameter("translation").orEmpty())
                                view.loadDataWithBaseURL("https://offline.mcn-app/", html, "text/html", "UTF-8", null)
                                return true
                            }
                            // Never let ordinary homepage navigation silently contact Naijacloud.
                            // Public pages that have local renderers open from saved phone data;
                            // other pages use a saved MHTML copy or a clear offline notice.
                            val diocesanHost = android.net.Uri.parse(BuildConfig.API_BASE_URL).host
                            if ((uri.scheme == "http" || uri.scheme == "https") && uri.host == diocesanHost) {
                                val route = localPath.ifBlank { "/" }
                                if (route == "/" || route == "/index.html") {
                                    openSavedDiocesanHome(view)
                                    return true
                                }
                                if (route in setOf("/login", "/register", "/registration", "/giving", "/payment", "/prayer-request")) {
                                    if (onlineState) {
                                        // Let WebView perform the original navigation itself.
                                        // Calling loadUrl() here from shouldOverrideUrlLoading can
                                        // re-enter navigation interception and fail on some WebView versions.
                                        return false
                                    } else {
                                        val notice = "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font:16px system-ui;padding:24px'><h2>Internet connection required</h2><p>This service needs an internet connection. Your saved homepage and downloaded church resources remain available offline.</p><p><a href='mcn-app://home'>Return to homepage</a></p></body>"
                                        view.loadDataWithBaseURL("https://offline.mcn-app/", notice, "text/html", "UTF-8", null)
                                        return true
                                    }
                                }
                                val savedPage = offlinePageArchiveFile(view.context, uri.toString())
                                if (savedPage.isFile && savedPage.length() > 0L) {
                                    view.loadUrl(android.net.Uri.fromFile(savedPage).toString())
                                } else {
                                    val notice = "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font:16px system-ui;padding:24px;background:#f3f6fa;color:#17345b'><h2>Page not saved for offline use</h2><p>This page is not part of the downloaded offline package. Use Update Offline Content while connected to save the latest available content.</p><p><a href='mcn-app://home'>Return to saved homepage</a></p></body>"
                                    view.loadDataWithBaseURL("https://offline.mcn-app/", notice, "text/html", "UTF-8", null)
                                }
                                return true
                            }
                            if (uri.scheme == "file" && bundledPagePath.isNotBlank()) {
                                val route = bundledPagePath.removePrefix("/")
                                if (route in setOf("login", "register", "registration", "giving", "payment", "prayer-request")) {
                                    view.loadUrl(BuildConfig.API_BASE_URL.trimEnd('/') + "/" + route)
                                }
                                return true
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "offline") {
                                onOfflineDownload(view)
                                return true
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "offline-library") {
                                val html = OfflineDevotionalPage.render(view.context, "/devotional-centre")
                                view.loadDataWithBaseURL(BuildConfig.API_BASE_URL, html, "text/html", "UTF-8", null)
                                return true
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "staff-login") {
                                // Keep authentication on the original diocesan web pages.
                                // Do not replace registration, login or password-reset screens
                                // with a separate native form.
                                val loginUrl = android.net.Uri.parse(BuildConfig.API_BASE_URL)
                                    .buildUpon().appendPath("login").build()
                                view.loadUrl(loginUrl.toString())
                                return true
                            }
                            // All website navigation stays inside this WebView, including links
                            // to other diocesan pages and pages opened with target=_blank.
                            if (uri.scheme == "http" || uri.scheme == "https") {
                                // External web links are not opened as background navigation from
                                // the bundled homepage. Login/payment actions are handled above.
                                return true
                            }
                            // Let phone/email handlers work without launching a browser.
                            if (uri.scheme == "tel" || uri.scheme == "mailto") {
                                runCatching {
                                    view.context.startActivity(Intent(Intent.ACTION_VIEW, uri))
                                }
                                return true
                            }
                            // Prevent unknown/custom links from handing the user to a browser.
                            return true
                        }

                        @Suppress("DEPRECATION")
                        override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                            val uri = android.net.Uri.parse(url)
                            if (uri.scheme == "mcn-app" && uri.host == "home") {
                                openSavedDiocesanHome(view)
                                return true
                            }
                            val legacyPath = when {
                                uri.path == "/devotional-centre" && uri.fragment == "uploaded-bible-library" -> "/devotional-centre/holy-bible"
                                uri.path == "/devotional-centre" && uri.fragment == "english-methodist-hymns" -> "/devotional-centre/collection/english-hymns"
                                uri.path == "/devotional-centre/english-hymns" -> "/devotional-centre/collection/english-hymns"
                                uri.path == "/bible" || uri.path == "/scripture" -> "/devotional-centre/holy-bible"
                                uri.path == "/hymns" || uri.path == "/hymn-library" -> "/devotional-centre/collection/english-hymns"
                                else -> uri.path.orEmpty()
                            }
                            if (legacyPath.startsWith("/devotional-centre") || legacyPath == "/media-library" ||
                                legacyPath == "/fellowships" || legacyPath.startsWith("/fellowship/")) {
                                val html = OfflineDevotionalPage.render(view.context, legacyPath, uri.getQueryParameter("q").orEmpty(), uri.getQueryParameter("translation").orEmpty())
                                view.loadDataWithBaseURL("https://offline.mcn-app/", html, "text/html", "UTF-8", null)
                                return true
                            }
                            if ((uri.scheme == "http" || uri.scheme == "https") &&
                                uri.host == android.net.Uri.parse(BuildConfig.API_BASE_URL).host) {
                                if (legacyPath.isBlank() || legacyPath == "/" || legacyPath == "/index.html") {
                                    openSavedDiocesanHome(view)
                                } else {
                                    val savedPage = offlinePageArchiveFile(view.context, uri.toString())
                                    if (savedPage.isFile && savedPage.length() > 0L) {
                                        view.loadUrl(android.net.Uri.fromFile(savedPage).toString())
                                    } else {
                                        val notice = "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font:16px system-ui;padding:24px'><h2>Page not saved for offline use</h2><p>Use Update Offline Content while connected to save this page.</p><p><a href='mcn-app://home'>Return to homepage</a></p></body>"
                                        view.loadDataWithBaseURL("https://offline.mcn-app/", notice, "text/html", "UTF-8", null)
                                    }
                                }
                                return true
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "offline") {
                                onOfflineDownload(view)
                                return true
                            }
                            if (uri.scheme == "mcn-app" && uri.host == "staff-login") {
                                val loginUrl = android.net.Uri.parse(BuildConfig.API_BASE_URL)
                                    .buildUpon().appendPath("login").build()
                                view.loadUrl(loginUrl.toString())
                                return true
                            }
                            if ((uri.scheme == "http" || uri.scheme == "https") &&
                                uri.host == android.net.Uri.parse(BuildConfig.API_BASE_URL).host &&
                                view.url?.startsWith("file:") == true) {
                                val savedPage = offlinePageArchiveFile(view.context, uri.toString())
                                if (savedPage.isFile && savedPage.length() > 0L) {
                                    view.loadUrl(android.net.Uri.fromFile(savedPage).toString())
                                } else {
                                    val notice = "<!doctype html><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font:16px system-ui;padding:24px;background:#f3f6fa;color:#17345b'><h2>Offline page not saved yet</h2><p>Connect and deliberately choose <b>Update Offline Content</b> to save this section.</p><p><a href='mcn-app://home'>Return to saved homepage</a></p></body>"
                                    view.loadDataWithBaseURL("https://offline.mcn-app/", notice, "text/html", "UTF-8", null)
                                }
                                return true
                            }
                            // Do not allow a legacy WebView navigation path to load the
                            // diocesan website directly. Only explicit Update/Login/payment flows do.
                            return true
                        }
                        override fun shouldInterceptRequest(view: WebView, request: android.webkit.WebResourceRequest): android.webkit.WebResourceResponse? {
                            OfflineDevotionalPage.fileResponse(ctx, request.url.toString())?.let { return it }
                            // Serve same-origin homepage assets directly from the APK. This is
                            // what prevents absolute /static/... image, CSS and JS URLs from
                            // falling through to Naijacloud when the homepage is opened locally.
                            val requestedUri = request.url
                            val configuredHost = android.net.Uri.parse(BuildConfig.API_BASE_URL).host
                            // Serve APK-bundled same-origin assets on the very first page load.
                            // Do not gate this on onPageStarted: WebView may request CSS/images
                            // before that callback flips localArchiveActive, causing a blank page
                            // when the phone is in Airplane Mode.
                            if (requestedUri.host == configuredHost && !request.isForMainFrame) {
                                val requestPath = android.net.Uri.decode(requestedUri.encodedPath.orEmpty()).trimStart('/')
                                if (requestPath.startsWith("api/") || requestPath.startsWith("socket.io/")) {
                                    return android.webkit.WebResourceResponse(
                                        "application/json", "UTF-8", 503, "Offline snapshot",
                                        mapOf("Cache-Control" to "no-store"),
                                        java.io.ByteArrayInputStream(ByteArray(0))
                                    )
                                }
                                val safePath = requestPath.split('/').filter { it.isNotBlank() && it != "." && it != ".." }.joinToString("/")
                                if (safePath.isNotBlank()) {
                                    val assetPath = "offline-home/$safePath"
                                    val mime = when (safePath.substringAfterLast('.', "").lowercase()) {
                                        "css" -> "text/css"; "js" -> "application/javascript"; "mjs" -> "application/javascript"
                                        "png" -> "image/png"; "jpg", "jpeg" -> "image/jpeg"; "gif" -> "image/gif"
                                        "webp" -> "image/webp"; "svg" -> "image/svg+xml"; "ico" -> "image/x-icon"
                                        "woff" -> "font/woff"; "woff2" -> "font/woff2"; "ttf" -> "font/ttf"
                                        "json" -> "application/json"; "mp4" -> "video/mp4"; "webm" -> "video/webm"
                                        "mp3" -> "audio/mpeg"; "m4a" -> "audio/mp4"; "pdf" -> "application/pdf"
                                        else -> "application/octet-stream"
                                    }
                                    val localAsset = runCatching { ctx.assets.open(assetPath) }.getOrNull()
                                    if (localAsset != null) {
                                        return android.webkit.WebResourceResponse(mime, null, localAsset)
                                    }
                                }
                                // A missing bundled same-origin resource must not trigger a
                                // network request; return a local 404 instead.
                                return android.webkit.WebResourceResponse(
                                    "text/plain", "UTF-8", 404, "Not found",
                                    mapOf("Cache-Control" to "no-store"),
                                    java.io.ByteArrayInputStream("Offline asset not packaged".toByteArray())
                                )
                            }
                            // While the bundled/saved homepage is active and the phone is offline,
                            // fail all remote HTTP requests locally. This prevents CDN, analytics,
                            // API and accidental website requests from delaying the offline screen.
                            if (localArchiveActive.get() && !onlineState &&
                                (requestedUri.scheme == "http" || requestedUri.scheme == "https")) {
                                return android.webkit.WebResourceResponse(
                                    "text/plain", "UTF-8", 503, "Offline",
                                    mapOf("Cache-Control" to "no-store"),
                                    java.io.ByteArrayInputStream(ByteArray(0))
                                )
                            }
                            if (!onlineState) {
                                val localBible = OfflineModuleManager.cachedBibleModuleResponse(ctx, request.url.toString())
                                if (localBible != null) {
                                    return android.webkit.WebResourceResponse(
                                        "application/json", "UTF-8", 200, "OK",
                                        mapOf("Access-Control-Allow-Origin" to "*", "Access-Control-Allow-Methods" to "GET, OPTIONS"),
                                        java.io.ByteArrayInputStream(localBible)
                                    )
                                }
                            }
                            // This callback runs on a WebView worker thread. Do not call the
                            // superclass implementation with the WebView instance: keep the
                            // interceptor strictly request-based and return null for network fallback.
                            return null
                        }
                        override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
                            localArchiveActive.set(url?.startsWith("file:") == true)
                            pageLoading = true
                            pageError = false
                            pageErrorDetails = "Connecting to the diocesan website…"
                        }
                        override fun onPageFinished(view: WebView, url: String?) {
                            // Keep every ordinary website link, form and popup navigation
                            // inside this standalone app instead of handing it to Chrome.
                            val keepNavigationInsideApp = """
                                (function() {
                                  document.querySelectorAll('a[target],form[target]').forEach(function(el) {
                                    var target = (el.getAttribute('target') || '').toLowerCase();
                                    if (target === '_blank' || target === '_new' || target === 'external') {
                                      el.setAttribute('target','_self');
                                    }
                                  });
                                  document.addEventListener('click',function(event) {
                                    var link = event.target.closest('a[href]');
                                    if (!link) return;
                                    var href = link.getAttribute('href') || '';
                                    if (/^https?:/i.test(href) && link.target && link.target.toLowerCase() !== '_self') {
                                      event.preventDefault();
                                      window.location.assign(link.href);
                                    }
                                  },true);
                                  window.open = function(url) {
                                    if (url) window.location.assign(url);
                                    return window;
                                  };
                                })();
                            """.trimIndent()
                            view.evaluateJavascript(keepNavigationInsideApp, null)

                            // Reconnect homepage media controls to the files already downloaded
                            // into the devotional/media libraries. The public page's signed
                            // Supabase URLs require internet and therefore cannot play offline.
                            if (url?.startsWith("file:") == true) {
                                val hymnRows = runCatching {
                                    org.json.JSONArray(
                                        File(File(ctx.filesDir, "offline_storage/english_hymns"), "resources.json").readText()
                                    )
                                }.getOrDefault(org.json.JSONArray())
                                val mediaRows = runCatching {
                                    org.json.JSONArray(
                                        File(File(ctx.filesDir, "offline_storage/Church_Media"), "index.json").readText()
                                    )
                                }.getOrDefault(org.json.JSONArray())
                                val localMediaScript = """
                                    (function() {
                                      const hymns = $hymnRows;
                                      const media = $mediaRows;
                                      const key = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
                                      const card = document.querySelector('.android-daily-card.hymn-preview');
                                      if (card) {
                                        const heading = key(card.querySelector('h3')?.innerText);
                                        const row = hymns.find(item => {
                                          const number = key(item.item_number || item.number || '');
                                          const title = key(item.title || '');
                                          return (number && heading.includes(number)) || (title && heading.includes(title));
                                        });
                                        if (row && row.audio_file) {
                                          let audio = card.querySelector('audio.daily-preview-audio');
                                          if (!audio) {
                                            const wrap = document.createElement('div');
                                            wrap.className = 'daily-preview-audio-wrap';
                                            const label = document.createElement('span');
                                            label.className = 'daily-preview-audio-label';
                                            label.textContent = '▶ Play downloaded hymn tune';
                                            audio = document.createElement('audio');
                                            audio.className = 'daily-preview-audio';
                                            audio.controls = true;
                                            audio.preload = 'none';
                                            audio.playsInline = true;
                                            wrap.append(label, audio);
                                            const details = card.querySelector('details');
                                            if (details) details.appendChild(wrap);
                                          }
                                          if (audio) {
                                            audio.src = 'https://offline.mcn-app/__mcn_offline/file/' + encodeURIComponent(row.audio_file);
                                            audio.load();
                                          }
                                        }
                                        const tunes = row && row.payload && (row.payload.otherTunes || row.payload.other_tunes);
                                        if (Array.isArray(tunes)) {
                                          const audioElements = card.querySelectorAll('audio.daily-preview-audio');
                                          tunes.forEach((tune, index) => {
                                            if (tune.offline_file && audioElements[index + 1]) {
                                              audioElements[index + 1].src = 'https://offline.mcn-app/__mcn_offline/file/' + encodeURIComponent(tune.offline_file);
                                              audioElements[index + 1].load();
                                            }
                                          });
                                        }
                                      }
                                      const videos = document.querySelectorAll('.homepage-video-card video');
                                      videos.forEach(video => {
                                        const title = key(video.getAttribute('aria-label') || video.closest('.homepage-video-card')?.querySelector('h3')?.innerText);
                                        const match = media.find(item => item.media_type === 'video' && key(item.title) === title);
                                        if (match && match.file) {
                                          video.src = 'https://offline.mcn-app/__mcn_offline/file/' + encodeURIComponent(match.file);
                                          video.load();
                                        }
                                      });
                                    })();
                                """.trimIndent()
                                view.evaluateJavascript(localMediaScript, null)
                            }

                            // Keep relative links and asset references relative to the bundled
                            // homepage. Rebasing them to API_BASE_URL makes an offline page call
                            // Naijacloud for its own CSS, images and internal navigation.
                            if (url?.startsWith("file:") != true) {
                                val parsed = url?.let { android.net.Uri.parse(it) }
                                val configuredHost = android.net.Uri.parse(BuildConfig.API_BASE_URL).host
                                // Save the actual diocesan root page as a local MHTML archive.
                                // Compare hosts rather than URL prefixes because redirects may add
                                // or remove a trailing slash or change the canonical root URL.
                                if (parsed != null && parsed.host == configuredHost &&
                                    (parsed.path.isNullOrBlank() || parsed.path == "/") &&
                                    !url.orEmpty().startsWith("file:")) {
                                    val archive = File(context.filesDir, "offline_homepage/diocesan-homepage.mht")
                                    view.postDelayed({
                                        archive.parentFile?.mkdirs()
                                        fun saveHomepageArchive(attempt: Int) {
                                            view.saveWebArchive(archive.absolutePath, false) { savedPath ->
                                                val saved = savedPath?.let { File(it) }
                                                if (saved != null && saved.isFile && saved.length() > 0L) {
                                                    context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
                                                        .edit()
                                                        .putBoolean("homepage_snapshot_saved", true)
                                                        .putLong("homepage_snapshot_saved_at", System.currentTimeMillis())
                                                        .apply()
                                                    Log.i("DeltaSouthOffline", "Homepage archive saved: ${saved.length()} bytes")
                                                } else if (attempt < 3) {
                                                    view.postDelayed({ saveHomepageArchive(attempt + 1) }, 1800L)
                                                } else {
                                                    Log.e("DeltaSouthOffline", "Homepage archive could not be saved after retries")
                                                }
                                            }
                                        }
                                        saveHomepageArchive(1)
                                    }, 2500L)
                                } else if (parsed != null && parsed.host == configuredHost) {
                                    val archive = offlinePageArchiveFile(context, url.orEmpty())
                                    view.postDelayed({
                                        archive.parentFile?.mkdirs()
                                        view.saveWebArchive(archive.absolutePath, false) { savedPath ->
                                            if (!savedPath.isNullOrBlank() && File(savedPath).isFile && File(savedPath).length() > 0L) {
                                                context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
                                                    .edit().putLong("homepage_snapshot_saved_at", System.currentTimeMillis()).apply()
                                            }
                                        }
                                    }, 1800L)
                                }
                            }

                            // Use the same single menu controller as the web dashboard.
                            // The app.js click handler toggles #menuPanel.open; no competing
                            // WebView onclick override is installed here.

                            // Keep the strategic Mission Map at the bottom of the standalone
                            // Android homepage, immediately before the footer, even when WebView
                            // serves an older cached homepage document.
                            val missionMapPlacement = """
                                (function() {
                                  var map = document.querySelector('#mission-map, .mission-map-section');
                                  var footer = document.querySelector('footer');
                                  if (!map || !footer || !footer.parentNode) return;
                                  if (map.nextElementSibling !== footer) {
                                    footer.parentNode.insertBefore(map, footer);
                                  }
                                  map.style.setProperty('display','block','important');
                                  map.style.setProperty('width','100%','important');
                                  map.style.setProperty('visibility','visible','important');
                                  map.style.setProperty('opacity','1','important');
                                  map.style.setProperty('position','relative','important');
                                  map.style.setProperty('clear','both','important');
                                  map.style.setProperty('margin-bottom','0','important');
                                })();
                            """.trimIndent()
                            view.evaluateJavascript(missionMapPlacement, null)
                            // Android WebView fallback for the CSS-checkbox homepage menu.
                            // Chrome uses the native label/checkbox behaviour; some embedded WebViews
                            // fail to toggle visually clipped checkbox inputs when their labels are tapped.
                            val menuBridge = """
                                (function() {
                                  if (window.__mcnAndroidMenuBridge) return;
                                  var updateLink = document.getElementById('saveOfflineApp');
                                  if (updateLink) updateLink.textContent = 'Update Offline Content';
                                  var nav = document.querySelector('.ds-site-nav');
                                  var menu = document.querySelector('.ds-menu');
                                  var trigger = document.querySelector('.ds-menu-trigger');
                                  var panel = document.querySelector('.ds-menu-panel');
                                  var toggle = document.querySelector('#dsMenuToggle');
                                  var subToggle = document.querySelector('#dsFellowshipsToggle');
                                  if (!nav || !menu || !trigger || !panel) return;
                                  window.__mcnAndroidMenuBridge = true;

                                  // Detach the real navigation panel from the page's nested layout.
                                  // This avoids WebView clipping/stacking bugs while preserving the
                                  // original anchor nodes and their existing click handlers.
                                  document.body.appendChild(panel);
                                  panel.style.cssText += ';display:none!important;position:fixed!important;left:0!important;right:0!important;width:100vw!important;top:0!important;max-height:50vh!important;overflow-y:auto!important;overflow-x:hidden!important;box-sizing:border-box!important;padding:8px 0!important;background:#08245b!important;border:1px solid rgba(255,255,255,.25)!important;z-index:2147483647!important;-webkit-overflow-scrolling:touch!important;';

                                  panel.querySelectorAll('a,.ds-menu-group-trigger').forEach(function(item) {
                                    item.style.cssText += ';display:block!important;visibility:visible!important;opacity:1!important;position:relative!important;float:none!important;width:100%!important;min-height:48px!important;height:auto!important;box-sizing:border-box!important;padding:13px 20px!important;margin:0!important;color:#fff!important;background:#08245b!important;font:600 16px/1.4 Arial,sans-serif!important;text-align:left!important;text-decoration:none!important;border:0!important;border-bottom:1px solid rgba(255,255,255,.16)!important;';
                                  });
                                  panel.querySelectorAll('.ds-menu-submenu a').forEach(function(item) {
                                    item.style.setProperty('padding-left','40px','important');
                                    item.style.setProperty('background','#061943','important');
                                  });

                                  function closeMenu() {
                                    if (toggle) toggle.checked = false;
                                    menu.classList.remove('ds-menu-open');
                                    panel.style.setProperty('display','none','important');
                                    trigger.setAttribute('aria-expanded','false');
                                  }
                                  function openMenu() {
                                    if (toggle) toggle.checked = true;
                                    menu.classList.add('ds-menu-open');
                                    var top = Math.max(0, nav.getBoundingClientRect().bottom);
                                    panel.style.setProperty('top',top+'px','important');
                                    panel.style.setProperty('max-height',Math.max(160,Math.min(window.innerHeight*0.5,window.innerHeight-top))+'px','important');
                                    panel.style.setProperty('display','block','important');
                                    panel.style.setProperty('visibility','visible','important');
                                    panel.style.setProperty('opacity','1','important');
                                    trigger.setAttribute('aria-expanded','true');
                                  }
                                  // Use document-level capture because Android WebView can fail to
                                  // dispatch the label/checkbox activation reliably on touch.
                                  // This handler receives taps even when the label contains icon/text spans.
                                  document.addEventListener('click',function(event) {
                                    var menuHit = event.target && event.target.closest ? event.target.closest('.ds-menu-trigger') : null;
                                    if (!menuHit) return;
                                    event.preventDefault();
                                    event.stopPropagation();
                                    if (event.stopImmediatePropagation) event.stopImmediatePropagation();
                                    if (panel.style.display === 'none' || getComputedStyle(panel).display === 'none') openMenu();
                                    else closeMenu();
                                  },true);
                                  // Make the full visible Menu bar an explicit touch target.
                                  trigger.style.setProperty('display','flex','important');
                                  trigger.style.setProperty('position','relative','important');
                                  trigger.style.setProperty('z-index','10','important');
                                  trigger.style.setProperty('pointer-events','auto','important');
                                  trigger.style.setProperty('touch-action','manipulation','important');
                                  panel.addEventListener('click',function(event) {
                                    var groupLabel = event.target.closest('.ds-menu-group-trigger');
                                    if (groupLabel && subToggle) {
                                      event.preventDefault();
                                      subToggle.checked = !subToggle.checked;
                                      var submenu = panel.querySelector('.ds-menu-submenu');
                                      if (submenu) submenu.style.setProperty('display',subToggle.checked?'block':'none','important');
                                      return;
                                    }
                                    var link = event.target.closest('a');
                                    if (link) {
                                      // The panel is detached from its original nav container.
                                      // Handle navigation explicitly: hiding a fixed WebView overlay
                                      // during the same click can cancel the anchor's default action.
                                      event.preventDefault();
                                      event.stopPropagation();
                                      var href = link.getAttribute('href') || '';
                                      closeMenu();
                                      window.setTimeout(function() {
                                        if (href === '#' || href === '') {
                                          if (link.id === 'saveOfflineApp') {
                                            Promise.resolve(window.mcnCacheEntireApp ? window.mcnCacheEntireApp() : null).finally(function() { window.location.href = 'mcn-app://offline'; });
                                          }
                                          return;
                                        }
                                        if (href.charAt(0) === '#') {
                                          var target = document.getElementById(href.slice(1));
                                          if (target) {
                                            target.scrollIntoView({behavior:'smooth',block:'start'});
                                            if (history && history.replaceState) history.replaceState(null,'',href);
                                          }
                                          return;
                                        }
                                        if (href.indexOf('mcn-app://') === 0) {
                                          if (href === 'mcn-app://offline') {
                                            Promise.resolve(window.mcnCacheEntireApp ? window.mcnCacheEntireApp() : null).finally(function() { window.location.href = href; });
                                          } else {
                                            window.location.href = href;
                                          }
                                          return;
                                        }
                                        window.location.assign(new URL(href, document.baseURI).href);
                                      }, 80);
                                    }
                                  },true);
                                  document.addEventListener('keydown',function(event){if(event.key==='Escape')closeMenu();});
                                  window.addEventListener('resize',function(){if(panel.style.display!=='none')openMenu();});
                                  window.addEventListener('scroll',function(){if(panel.style.display!=='none')closeMenu();},{passive:true});
                                })();
                            """.trimIndent()
                            view.evaluateJavascript(menuBridge, null)
                            // Daily Scripture and hymn use the same tested webpage implementation as Chrome.
                            pageLoading = false
                        }
                        override fun onReceivedError(view: WebView, request: android.webkit.WebResourceRequest, error: android.webkit.WebResourceError) {
                            if (request.isForMainFrame) {
                                pageLoading = false
                                val requestedPath = request.url.path.orEmpty()
                                // Failed online navigation must never strand the user on Android's
                                // generic "Webpage not available" screen. Restore the saved homepage.
                                val isLiveDiocesanPage = request.url.host == android.net.Uri.parse(BuildConfig.API_BASE_URL).host
                                if (isLiveDiocesanPage) {
                                    pageError = false
                                    pageErrorDetails = ""
                                    view.post {
                                        view.settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                                        // Recover to the homepage packaged in this APK, never an
                                        // old MHTML archive left behind by an earlier installation.
                                        view.loadUrl("file:///android_asset/offline-home/index.html")
                                    }
                                    return
                                }
                                if (requestedPath.startsWith("/devotional-centre") || requestedPath == "/media-library") {
                                    pageError = false
                                    pageErrorDetails = ""
                                    val localHtml = OfflineDevotionalPage.render(
                                        view.context,
                                        requestedPath,
                                        request.url.getQueryParameter("q").orEmpty(),
                                        request.url.getQueryParameter("translation").orEmpty()
                                    )
                                    view.post {
                                        view.loadDataWithBaseURL("https://offline.mcn-app/", localHtml, "text/html", "UTF-8", null)
                                    }
                                } else {
                                    pageErrorDetails = "The main diocesan homepage is not saved in this phone's WebView cache yet. Connect once to load it, then it can be reopened offline."
                                    pageError = true
                                }
                            }
                        }
                        override fun onReceivedHttpError(view: WebView, request: android.webkit.WebResourceRequest, response: android.webkit.WebResourceResponse) {
                            if (request.isForMainFrame && response.statusCode == 404 &&
                                (request.url.path.isNullOrBlank() || request.url.path == "/")) {
                                pageLoading = false
                                pageErrorDetails = "The main diocesan homepage returned HTTP 404. A different page will not be substituted."
                                pageError = true
                                return
                            }
                            if (request.isForMainFrame && response.statusCode >= 400) {
                                pageLoading = false
                                pageErrorDetails = "The website returned HTTP ${response.statusCode}."
                                pageError = true
                            }
                        }
                    }
                    webChromeClient = WebChromeClient()
                    settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
                    // Always start with the current homepage bundled in this APK.
                    // Do not prefer an MHTML archive from a previous app version.
                    loadUrl("file:///android_asset/offline-home/index.html")
                    webView = this
                }
            },
            update = { view ->
                // Connectivity changes must not silently replace the saved homepage.
                if (view.url.isNullOrBlank()) openSavedDiocesanHome(view)
            }
        )
        // Use the single menu rendered by the official diocesan website.
        if (pageLoading) {
            LinearProgressIndicator(Modifier.fillMaxWidth().align(androidx.compose.ui.Alignment.TopCenter))
        }
        if (offlineDownloadBusy) {
            ElevatedCard(Modifier.align(androidx.compose.ui.Alignment.BottomCenter).fillMaxWidth().padding(12.dp)) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("$offlineDownloadStage • $offlineDownloadProgress%", style = MaterialTheme.typography.bodyMedium)
                    LinearProgressIndicator(progress = { offlineDownloadProgress / 100f }, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        if (pageError) {
            ElevatedCard(Modifier.align(androidx.compose.ui.Alignment.Center).padding(24.dp)) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("The diocesan homepage could not be reached inside the app.", style = MaterialTheme.typography.titleMedium)
                    Text(pageErrorDetails, style = MaterialTheme.typography.bodySmall)
                    Text("You can retry here or open the downloaded devotional and worship libraries inside this app.")
                    Button(onClick = {
                        pageError = false
                        pageLoading = true
                        webView?.clearHistory()
                        webView?.reload()
                    }, modifier = Modifier.fillMaxWidth()) { Text("Retry homepage") }
                    OutlinedButton(onClick = {
                        pageError = false
                        val localHtml = OfflineDevotionalPage.render(context, "/devotional-centre")
                        webView?.clearHistory()
                        webView?.loadDataWithBaseURL("https://offline.mcn-app/", localHtml, "text/html", "UTF-8", null)
                    }, modifier = Modifier.fillMaxWidth()) { Text("Open downloaded devotional libraries offline") }
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
