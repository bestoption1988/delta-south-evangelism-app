package ng.mcn.deltasouth.evangelism

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import coil.compose.AsyncImage
import androidx.compose.material3.Card
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private fun Any?.asText(): String = this?.toString()?.takeIf { it != "null" } ?: ""
private fun Any?.asObject(): Map<String, Any?> = this as? Map<String, Any?> ?: emptyMap()
private fun Any?.asObjects(): List<Map<String, Any?>> =
    (this as? List<*>)?.mapNotNull { it as? Map<String, Any?> } ?: emptyList()

@Composable
fun NativePublicHomepage(
    online: Boolean,
    offlineDownloadBusy: Boolean,
    offlineDownloadProgress: Int,
    offlineDownloadStage: String,
    onStaffLogin: () -> Unit,
    onOpenOfflineLibrary: () -> Unit,
    onOfflineDownload: () -> Unit
) {
    val context = LocalContext.current
    var payload by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var loading by remember { mutableStateOf(true) }
    var loadMessage by remember { mutableStateOf("Loading saved diocesan homepage…") }

    LaunchedEffect(online) {
        loading = true
        loadMessage = if (online) "Refreshing diocesan information…" else "Opening saved offline information…"
        val result = withContext(Dispatchers.IO) {
            runCatching { Backend.api.publicHomepage() }
        }
        result.onSuccess {
            payload = it
            loadMessage = if (online) "Diocesan information is up to date." else "Showing saved diocesan information from this device."
        }.onFailure {
            loadMessage = if (online) "Could not reach the diocesan server. Check your connection or try again."
            else "No homepage has been saved on this device yet. Connect once, then download the offline modules."
        }
        loading = false
    }

    val content = payload["homepage_content"].asObject()
    val reading = payload["daily_reading"].asObject()
    val verse = reading["verse"].asObject()
    val hymn = reading["hymn"].asObject()
    val leadership = payload["leadership"].asObjects()
    val events = payload["events"].asObjects()
    val churches = payload["churches"].asObjects()
    val sermons = payload["sermons"].asObjects()
    val gallery = payload["gallery"].asObjects()
    val videos = payload["videos"].asObjects()
    val birthdays = payload["birthdays"].asObjects()
    val media = payload["media"].asObjects()

    fun openPage(path: String) {
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(BuildConfig.API_BASE_URL + path.trimStart('/'))))
        }
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Spacer(Modifier.height(10.dp))
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("WELCOME TO", style = MaterialTheme.typography.labelLarge)
                        Text(content["hero_heading"].asText().ifBlank { "METHODIST CHURCH NIGERIA" }, style = MaterialTheme.typography.headlineSmall)
                        Text(content["hero_subheading"].asText().ifBlank { "DELTA SOUTH DIOCESE" }, style = MaterialTheme.typography.headlineMedium)
                        Text("WORSHIP · WITNESS · SERVICE · DISCIPLESHIP", style = MaterialTheme.typography.bodySmall)
                        Text("“Go into all the world and preach the Gospel to every creature.” — Mark 16:15")
                        Text("A Church on Fire for Christ", style = MaterialTheme.typography.titleLarge)
                        Text("Transforming Lives and Impacting Nations.")
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(onClick = onStaffLogin, modifier = Modifier.weight(1.35f)) {
                                Text("Member / Staff Login", maxLines = 1)
                            }
                            OutlinedButton(onClick = onOpenOfflineLibrary, modifier = Modifier.weight(1f)) {
                                Text("Offline Library", maxLines = 1)
                            }
                        }
                    }
                }
            }
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("OFFLINE DOWNLOADS", style = MaterialTheme.typography.titleMedium)
                        Text(if (online) "Download the church resources to use them without an internet connection." else "You are offline. Previously downloaded resources remain available.")
                        if (offlineDownloadBusy) {
                            Text("$offlineDownloadStage · $offlineDownloadProgress%")
                            LinearProgressIndicator(progress = { offlineDownloadProgress / 100f }, modifier = Modifier.fillMaxWidth())
                        } else {
                            Button(onClick = onOfflineDownload, enabled = online) { Text("Download / Update Modules") }
                        }
                        Text(loadMessage, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("SCRIPTURE FOR TODAY", style = MaterialTheme.typography.titleMedium)
                        Text(verse["reference"].asText().ifBlank { "Daily Scripture" }, style = MaterialTheme.typography.titleLarge)
                        Text(verse["text"].asText().ifBlank { "Connect and download the Scripture module to save today's reading." })
                        Spacer(Modifier.height(4.dp))
                        Text("METHODIST HYMN FOR TODAY", style = MaterialTheme.typography.titleMedium)
                        val hymnTitle = hymn["title"].asText().ifBlank { "Daily Methodist Hymn" }
                        val hymnNumber = listOf("number", "hymn_number", "item_number").firstNotNullOfOrNull { hymn[it].asText().takeIf(String::isNotBlank) }.orEmpty()
                        Text(listOf(hymnNumber, hymnTitle).filter(String::isNotBlank).joinToString(" · "), style = MaterialTheme.typography.titleLarge)
                        Text(hymn["lyrics"].asText().ifBlank { "Download the Methodist Hymns module to read saved hymn lyrics offline." })
                        val tune = hymn["tune_name"].asText().ifBlank { hymn["tune"].asText() }
                        if (tune.isNotBlank()) Text("Tune: $tune", style = MaterialTheme.typography.bodySmall)
                        OutlinedButton(onClick = { openPage("devotional-centre") }) { Text("View All Scripture & Hymns") }
                    }
                }
            }
            item {
                Text("EXPLORE THE DIOCESE", style = MaterialTheme.typography.titleLarge)
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(
                        "Church Directory" to "churches",
                        "Fellowships & Ministries" to "fellowships",
                        "Devotional Centre" to "devotional-centre",
                        "Sermons & Media" to "live",
                        "Photo Gallery" to "media-library",
                        "Events & Announcements" to "events",
                        "Prayer Requests" to "prayer-request",
                        "Online Giving" to "giving",
                        "Live Services" to "live"
                    ).forEach { (label, route) ->
                        OutlinedButton(onClick = { openPage(route) }, modifier = Modifier.fillMaxWidth()) { Text(label) }
                    }
                }
            }
            item {
                Text("OUR LEADERSHIP", style = MaterialTheme.typography.titleLarge)
                if (leadership.isEmpty()) Text("Leadership profiles will appear after the first successful download.")
            }
            items(leadership) { person ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        val leaderPhoto = person["photo_path"].asText()
                        if (leaderPhoto.isNotBlank()) {
                            val leaderPhotoUrl = if (leaderPhoto.startsWith("http")) leaderPhoto else BuildConfig.API_BASE_URL.trimEnd('/') + "/static/" + leaderPhoto.trimStart('/')
                            AsyncImage(model = leaderPhotoUrl, contentDescription = person["full_name"].asText(), modifier = Modifier.fillMaxWidth().height(190.dp))
                        }
                        Text(person["title"].asText(), style = MaterialTheme.typography.labelLarge)
                        Text(person["full_name"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(person["biography"].asText(), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("WORSHIP WITH US", style = MaterialTheme.typography.titleLarge)
                        Text("Methodist Church Nigeria · Delta South Diocese")
                        Text(content["livestream_announcement"].asText().ifBlank { "Join our worship services and church broadcasts." })
                        Button(onClick = { openPage("live") }, modifier = Modifier.fillMaxWidth()) { Text("Watch Live Service") }
                        OutlinedButton(onClick = { openPage("giving") }, modifier = Modifier.fillMaxWidth()) { Text("Give Online") }
                    }
                }
            }
            item {
                Text("LATEST ANNOUNCEMENTS", style = MaterialTheme.typography.titleLarge)
                if (events.isEmpty()) Text("No published announcements are currently available.")
            }
            items(events) { event ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(event["title"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(event["event_date"].asText(), style = MaterialTheme.typography.labelSmall)
                        Text(event["description"].asText())
                        Text(event["venue"].asText(), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                Text("SERMONS & TEACHINGS", style = MaterialTheme.typography.titleLarge)
                if (sermons.isEmpty()) Text("Published sermons will appear here.")
            }
            items(sermons) { sermon ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(sermon["title"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(sermon["description"].asText())
                        if (sermon["video_url"].asText().isNotBlank()) {
                            OutlinedButton(onClick = {
                                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(sermon["video_url"].asText()))) }
                            }) { Text("Watch / Listen") }
                        }
                    }
                }
            }
            item {
                Text("📸 OUR CHURCH GALLERY", style = MaterialTheme.typography.titleLarge)
                if (gallery.isEmpty()) Text("Our diocesan memories will appear here when published.")
            }
            items(gallery) { photo ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        val imageUrl = photo["signed_url"].asText()
                        if (imageUrl.isNotBlank()) AsyncImage(model = imageUrl, contentDescription = photo["title"].asText(), modifier = Modifier.fillMaxWidth().height(210.dp))
                        Text(photo["title"].asText().ifBlank { "Diocesan photograph" }, style = MaterialTheme.typography.titleMedium)
                        Text(photo["description"].asText(), style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            item {
                Text("FEATURED CHURCH VIDEOS", style = MaterialTheme.typography.titleLarge)
                if (videos.isEmpty()) Text("Published church videos will appear here.")
            }
            items(videos) { video ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(video["title"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(video["description"].asText())
                        OutlinedButton(enabled = video["signed_url"].asText().isNotBlank(), onClick = { runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(video["signed_url"].asText()))) } }) { Text("Watch Video") }
                    }
                }
            }
            item {
                Text("HAPPY BIRTHDAY!", style = MaterialTheme.typography.titleLarge)
                if (birthdays.isEmpty()) Text("We celebrate our members on their birthdays.")
            }
            items(birthdays) { member ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        val photoUrl = member["photo_url"].asText()
                        if (photoUrl.isNotBlank()) AsyncImage(model = photoUrl, contentDescription = member["full_name"].asText(), modifier = Modifier.fillMaxWidth().height(160.dp))
                        Text(member["full_name"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(listOf(member["circuit"].asText(), member["church_name"].asText()).filter(String::isNotBlank).joinToString(" · "))
                    }
                }
            }
            item {
                Text("FIND A CHURCH", style = MaterialTheme.typography.titleLarge)
                if (churches.isEmpty()) Text("Church directory data will be available after download.")
            }
            items(churches) { church ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(church["church_name"].asText(), style = MaterialTheme.typography.titleMedium)
                        Text(church["circuit"].asText(), style = MaterialTheme.typography.labelLarge)
                        Text(listOf(church["address"].asText(), church["town"].asText(), church["state"].asText()).filter(String::isNotBlank).joinToString(", "))
                        Text(church["phone"].asText(), style = MaterialTheme.typography.bodySmall)
                        if (church["maps_url"].asText().isNotBlank()) {
                            OutlinedButton(onClick = {
                                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(church["maps_url"].asText()))) }
                            }) { Text("Open Map") }
                        }
                    }
                }
            }
            item {
                Text("ABOUT OUR DIOCESE", style = MaterialTheme.typography.titleLarge)
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Vision", style = MaterialTheme.typography.titleMedium)
                        Text(content["vision"].asText().ifBlank { "To be spiritually vibrant and one of the largest Churches in Nigeria." })
                        Text("Mission", style = MaterialTheme.typography.titleMedium)
                        val missionItems = listOf("mission_1", "mission_2", "mission_3").map { content[it].asText() }.filter(String::isNotBlank)
                        if (missionItems.isEmpty()) {
                            Text("• To consistently win more souls for Christ.")
                            Text("• To develop spiritually fulfilled members.")
                            Text("• To remain very active in serving humanity.")
                        } else missionItems.forEach { Text("• $it") }
                    }
                }
                Spacer(Modifier.height(28.dp))
            }
        }
    }
}
