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
 override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { MaterialTheme { NativeDioceseApp() } } }
}
@Composable private fun NativeDioceseApp() {
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
 var selected by remember { mutableStateOf("Home") }
 val scope = rememberCoroutineScope()
 if (!signedIn) {
  Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
   Text("METHODIST CHURCH NIGERIA", style = MaterialTheme.typography.titleLarge)
   Text("DELTA SOUTH DIOCESE", style = MaterialTheme.typography.titleMedium)
   Spacer(Modifier.height(24.dp))
   OutlinedTextField(username, { username = it }, label = { Text("Username") }, modifier = Modifier.fillMaxWidth())
   OutlinedTextField(password, { password = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth())
   Spacer(Modifier.height(12.dp))
   Button(enabled = !busy, onClick = {
    busy = true; message = "Signing in…"
    scope.launch {
     val result = withContext(Dispatchers.IO) { Backend.login(username.trim(), password) }
     result.onSuccess {
      runCatching { withContext(Dispatchers.IO) { Backend.api.me() } }
       .onSuccess { profile = it; signedIn = true; message = "" }
       .onFailure { message = it.message ?: "Could not load account profile." }
     }.onFailure { message = it.message ?: "Sign in failed." }
     busy = false
    }
   }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Please wait…" else "Sign in") }
   if (message.isNotBlank()) Text(message, color = MaterialTheme.colorScheme.error)
  }
 } else {
  Column(Modifier.fillMaxSize().padding(16.dp)) {
   Text("MCN Delta South Diocese", style = MaterialTheme.typography.headlineSmall)
   Text("Welcome, ${profile["full_name"] ?: profile["username"] ?: "Member"}")
   Spacer(Modifier.height(12.dp))
   Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
    listOf("Home", "Profile", "Attendance", "Giving", "Feed").forEach { label -> FilterChip(selected == label, { selected = label }, label = { Text(label) }) }
   }
   Spacer(Modifier.height(12.dp))
   when (selected) {
    "Home" -> {
     Button(onClick = {
      busy = true
      scope.launch {
       runCatching { withContext(Dispatchers.IO) { Backend.api.dashboard() } }
        .onSuccess { dashboard = it }.onFailure { message = it.message ?: "Dashboard could not load." }
       busy = false
      }
     }) { Text("Refresh dashboard") }
     if (dashboard.isEmpty()) Text("Your diocesan dashboard is ready. Tap refresh to load current data.")
     KeyValueList(dashboard)
    }
    "Profile" -> {
     Button(onClick = {
      busy = true
      scope.launch {
       runCatching { withContext(Dispatchers.IO) { Backend.api.memberRecords() } }
        .onSuccess { memberRecords = it }.onFailure { message = it.message ?: "Membership record unavailable." }
       busy = false
      }
     }) { Text("Load membership record") }
     KeyValueList(if (memberRecords.isEmpty()) profile else memberRecords)
    }
    "Attendance" -> {
     Button(onClick = {
      busy = true
      scope.launch {
       runCatching { withContext(Dispatchers.IO) { Backend.api.attendanceSummary() to Backend.api.memberAttendance() } }
        .onSuccess { attendanceSummary = it.first; attendanceRows = it.second }
        .onFailure { message = it.message ?: "Attendance history unavailable." }
       busy = false
      }
     }) { Text("Refresh attendance") }
     KeyValueList(attendanceSummary)
     Text("Attendance history", style = MaterialTheme.typography.titleMedium)
     RecordList(attendanceRows, listOf("attendance_date", "meeting_type", "status", "circuit", "church_name"))
    }
    "Giving" -> {
     Button(onClick = {
      busy = true
      scope.launch {
       runCatching { withContext(Dispatchers.IO) { Backend.api.givingHistory() } }
        .onSuccess { givingRows = it }.onFailure { message = it.message ?: "Giving history unavailable." }
       busy = false
      }
     }) { Text("Refresh giving history") }
     Text("Your recorded contributions", style = MaterialTheme.typography.titleMedium)
     RecordList(givingRows, listOf("date", "source", "fund", "amount", "method", "reference"))
    }
    else -> {
     Text("Church announcements and events")
     Button(onClick = {
      busy = true
      scope.launch {
       runCatching { withContext(Dispatchers.IO) { Backend.api.announcements() } }
        .onSuccess { feedRows = it; message = "${it.size} announcements loaded." }.onFailure { message = it.message ?: "Feed unavailable." }
       busy = false
      }
     }) { Text("Load announcements") }
     Text(message)
     RecordList(feedRows, listOf("title", "message", "created_at", "status"))
    }
   }
   Spacer(Modifier.height(16.dp))
   OutlinedButton(onClick = { Backend.cookies.clear(); signedIn = false; profile = emptyMap(); dashboard = emptyMap(); memberRecords = emptyMap(); attendanceRows = emptyList(); givingRows = emptyList() }) { Text("Sign out") }
  }
 }
}
@Composable private fun KeyValueList(values: Map<String, Any?>) {
 LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
  items(values.entries.toList()) { entry ->
   ElevatedCard(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text(entry.key, style = MaterialTheme.typography.labelMedium); Text(entry.value?.toString() ?: "—") } }
  }
 }
}

@Composable private fun RecordList(rows: List<Map<String, Any?>>, fields: List<String>) {
 if (rows.isEmpty()) {
  Text("No records loaded yet. Tap the refresh button to retrieve your records.", style = MaterialTheme.typography.bodySmall)
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
\n@Composable private fun SummaryCards(summary: Map<String, Any?>) {\n val labels = listOf("income_total" to "Total income", "expense_total" to "Total expenses", "net_balance" to "Net balance", "paid_online_total" to "Online payments", "matched_online_total" to "Matched online", "unmatched_online_total" to "Unmatched online")\n Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {\n  labels.chunked(2).forEach { pair ->\n   Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {\n    pair.forEach { (key, label) ->\n     ElevatedCard(Modifier.weight(1f)) { Column(Modifier.padding(12.dp)) { Text(label, style = MaterialTheme.typography.labelSmall); Text("₦" + String.format("%,.2f", (summary[key] as? Number)?.toDouble() ?: 0.0), style = MaterialTheme.typography.titleMedium) } }\n    }\n   }\n  }\n }\n}\n