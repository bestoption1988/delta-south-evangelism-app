package ng.mcn.deltasouth.evangelism

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { NativeDioceseApp() } }
    }
}

@Composable
private fun NativeDioceseApp() {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var signedIn by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var profile by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var dashboard by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var memberRecords by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var attendanceSummary by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var attendanceRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var givingRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var feedRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var financeSummary by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var paymentRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var reconciliationRows by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var registrations by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var directoryChurches by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var directoryCircuits by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var memberDirectory by remember { mutableStateOf<List<Map<String, Any?>>>(emptyList()) }
    var memberSearch by remember { mutableStateOf("") }
    var membershipStats by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var selected by remember { mutableStateOf("Home") }
    val scope = rememberCoroutineScope()
    val role = (profile["role"] ?: "").toString()
    val financeRoles = setOf("Admin", "Finance Officer", "Auditor", "Evangelism Minister", "Bishop / Diocesan Executive", "Diocesan Secretary")
    val canReview = role == "Admin" || role == "Evangelism Minister"

    if (!signedIn) {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
            Text("METHODIST CHURCH NIGERIA", style = MaterialTheme.typography.titleLarge)
            Text("DELTA SOUTH DIOCESE", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(username, { username = it }, label = { Text("Username") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(password, { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            Button(enabled = !busy, onClick = {
                busy = true
                message = "Signing in…"
                scope.launch {
                    val result = withContext(Dispatchers.IO) { Backend.login(username.trim(), password) }
                    result.onSuccess {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.me() } }
                            .onSuccess { profile = it; signedIn = true; selected = "Home"; message = "" }
                            .onFailure { message = it.message ?: "Could not load account profile." }
                    }.onFailure { message = it.message ?: "Sign in failed." }
                    busy = false
                }
            }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Please wait…" else "Sign in") }
            if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.error)
        }
    } else {
        val tabs = buildList {
            addAll(listOf("Home", "Profile", "Attendance", "Giving", "Feed", "Directory"))
            if (role in setOf("Admin", "Bishop / Diocesan Executive", "Evangelism Minister", "Planting Officer", "Diocesan Secretary", "Circuit Coordinator", "Local Church Evangelism Officer", "Auditor")) add("Members")
            if (financeRoles.contains(role)) add("Finance")
            if (canReview) add("Approvals")
        }
        Column(Modifier.fillMaxSize().padding(16.dp)) {
            Text("MCN Delta South Diocese", style = MaterialTheme.typography.headlineSmall)
            Text("Welcome, ${profile["full_name"] ?: profile["username"] ?: "Member"}")
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                tabs.forEach { label -> FilterChip(selected == label, { selected = label }, label = { Text(label) }) }
            }
            Spacer(Modifier.height(10.dp))
            when (selected) {
                "Home" -> {
                    ActionButton("Refresh dashboard", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.dashboard() } }
                            .onSuccess { dashboard = it }.onFailure { message = it.message ?: "Dashboard could not load." }
                    }
                    KeyValueList(dashboard)
                }
                "Profile" -> {
                    ActionButton("Load membership record", busy) {
                        runCatching { withContext(Dispatchers.IO) { Backend.api.memberRecords() } }
                            .onSuccess { memberRecords = it }.onFailure { message = it.message ?: "Membership record unavailable." }
                    }
                    KeyValueList(if (memberRecords.isEmpty()) profile else memberRecords)
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
                    RecordList(filteredMembers, listOf("member_id", "full_name", "phone", "circuit", "church_name", "fellowship", "gender", "baptised", "confirmed", "marriage"))
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
                                message = "Finance records refreshed."
                            }.onFailure { message = it.message ?: "Finance records could not be loaded." }
                    }
                    Text(message, style = MaterialTheme.typography.bodySmall)
                    val summary = financeSummary["summary"] as? Map<String, Any?> ?: emptyMap()
                    SummaryCards(summary)
                    Text("Payment history", style = MaterialTheme.typography.titleMedium)
                    RecordList(paymentRows, listOf("reference", "status", "amount", "currency", "purpose", "donor_name", "circuit", "church_name", "created_at", "paid_at"))
                    Text("Payment reconciliation", style = MaterialTheme.typography.titleMedium)
                    RecordList(reconciliationRows, listOf("reference", "payment_status", "payment_amount", "currency", "reconciliation_status", "income_id", "income_amount", "income_date"))
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
                Backend.cookies.clear()
                signedIn = false
                profile = emptyMap()
                dashboard = emptyMap()
                memberRecords = emptyMap()
                attendanceRows = emptyList()
                givingRows = emptyList()
                registrations = emptyList()
                memberDirectory = emptyList()
                memberSearch = ""
                membershipStats = emptyMap()
            }) { Text("Sign out") }
        }
    }
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
