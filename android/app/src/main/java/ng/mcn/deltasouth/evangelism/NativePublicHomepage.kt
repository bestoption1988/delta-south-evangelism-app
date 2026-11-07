package ng.mcn.deltasouth.evangelism

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import coil.compose.AsyncImage
import coil.compose.rememberAsyncImagePainter
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private fun Any?.asText(): String = this?.toString()?.takeIf { it != "null" } ?: ""
private fun Any?.asObject(): Map<String, Any?> = this as? Map<String, Any?> ?: emptyMap()
private fun Any?.asObjects(): List<Map<String, Any?>> =
    (this as? List<*>)?.mapNotNull { it as? Map<String, Any?> } ?: emptyList()

private val DioceseNavy = Color(0xFF0B1D49)
private val DioceseRed = Color(0xFFD7193F)
private val DioceseGold = Color(0xFFF2C230)
private val PageBackground = Color(0xFFF1F4F9)
private val CardText = Color(0xFF17233D)

@Composable
private fun SectionTitle(title: String) {
    Text(title, color = DioceseNavy, fontSize = 20.sp, fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(top = 8.dp, bottom = 2.dp))
}

@Composable
private fun ExploreTile(title: String, subtitle: String, symbol: String, color: Color, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().heightIn(min = 116.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(horizontal = 6.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                modifier = Modifier.size(48.dp).clip(RoundedCornerShape(50)).background(color),
                contentAlignment = Alignment.Center
            ) {
                Text(symbol, color = Color.White, fontSize = 23.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(8.dp))
            Text(title, color = CardText, fontWeight = FontWeight.Bold, fontSize = 13.sp, textAlign = TextAlign.Center)
            Text(subtitle, color = Color(0xFF687386), fontSize = 11.sp, textAlign = TextAlign.Center)
        }
    }
}

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
    var loadMessage by remember { mutableStateOf("Loading diocesan information…") }

    LaunchedEffect(online) {
        loadMessage = if (online) "Refreshing diocesan information…" else "Opening saved diocesan information…"
        val result = withContext(Dispatchers.IO) { runCatching { Backend.api.publicHomepage() } }
        result.onSuccess {
            payload = it
            loadMessage = if (online) "Diocesan information is up to date." else "Showing saved diocesan information."
        }.onFailure {
            loadMessage = if (online) "Unable to refresh. Check your connection." else "Connect once and download the public modules for offline use."
        }
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

    fun openPage(path: String) {
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(BuildConfig.API_BASE_URL + path.trimStart('/'))))
        }
    }
    fun imageUrl(path: String): String = when {
        path.isBlank() -> ""
        path.startsWith("http://") || path.startsWith("https://") -> path
        path.startsWith("/") -> BuildConfig.API_BASE_URL.trimEnd('/') + path
        path.startsWith("static/") -> BuildConfig.API_BASE_URL.trimEnd('/') + "/" + path
        else -> BuildConfig.API_BASE_URL.trimEnd('/') + "/static/" + path
    }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = PageBackground) {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 10.dp, bottom = 30.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(Modifier.size(58.dp).clip(RoundedCornerShape(50)).background(Color(0xFFF5F6F8)), contentAlignment = Alignment.Center) {
                            Text("✝", color = DioceseRed, fontSize = 34.sp, fontWeight = FontWeight.Bold)
                        }
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("METHODIST CHURCH NIGERIA", color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            Text("DELTA SOUTH DIOCESE", color = DioceseRed, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                            Text("WORSHIP · WITNESS · SERVICE · DISCIPLESHIP", color = Color.Gray, fontSize = 9.sp)
                        }
                    }
                }
                item {
                    Column(
                        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp))
                            .background(Brush.linearGradient(listOf(DioceseNavy, Color(0xFF142D65), Color(0xFF744B42))))
                            .padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text("WELCOME TO", color = DioceseGold, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                        Text("METHODIST CHURCH NIGERIA", color = Color.White, fontSize = 29.sp, lineHeight = 34.sp, fontWeight = FontWeight.ExtraBold)
                        Text("DELTA SOUTH DIOCESE", color = DioceseGold, fontSize = 29.sp, lineHeight = 34.sp, fontWeight = FontWeight.ExtraBold)
                        Text("“Go into all the world and preach the Gospel to every creature.” — Mark 16:15",
                            color = Color.White, fontSize = 17.sp, lineHeight = 25.sp)
                        Text("A Church on Fire for Christ", color = Color.White, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        Text("Transforming Lives and Impacting Nations.", color = Color(0xFFE8ECF6), fontSize = 16.sp)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                            Button(onClick = onStaffLogin, modifier = Modifier.weight(1.2f),
                                colors = ButtonDefaults.buttonColors(containerColor = DioceseRed)) { Text("Member / Staff", maxLines = 1) }
                            OutlinedButton(onClick = onOpenOfflineLibrary, modifier = Modifier.weight(1f),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)) { Text("Offline", maxLines = 1) }
                        }
                    }
                }
                item {
                    Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                            Text("OFFLINE DOWNLOADS", color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text("Download church resources to use them without an internet connection.", color = CardText)
                            if (offlineDownloadBusy) {
                                Text("$offlineDownloadStage · $offlineDownloadProgress%", color = DioceseNavy, fontWeight = FontWeight.SemiBold)
                                LinearProgressIndicator(progress = { offlineDownloadProgress / 100f }, modifier = Modifier.fillMaxWidth())
                            } else {
                                Button(onClick = onOfflineDownload, enabled = online,
                                    colors = ButtonDefaults.buttonColors(containerColor = DioceseNavy),
                                    modifier = Modifier.fillMaxWidth()) { Text("Download / Update Modules") }
                            }
                            Text(loadMessage, color = Color.Gray, fontSize = 12.sp)
                        }
                    }
                }
                item {
                    Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("SCRIPTURE FOR TODAY", color = DioceseRed, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                            Text(verse["reference"].asText().ifBlank { "Daily Scripture" }, color = DioceseNavy, fontSize = 24.sp, fontWeight = FontWeight.Bold)
                            Text(verse["text"].asText().ifBlank { "Today's Scripture will appear here when the diocesan content is available." },
                                color = CardText, fontSize = 16.sp, lineHeight = 25.sp)
                            Divider(color = PageBackground)
                            Text("♫ METHODIST HYMN FOR TODAY", color = DioceseRed, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                            val hymnTitle = hymn["title"].asText().ifBlank { "Daily Methodist Hymn" }
                            val hymnNumber = listOf("number", "hymn_number", "item_number")
                                .firstNotNullOfOrNull { hymn[it].asText().takeIf(String::isNotBlank) }.orEmpty()
                            Text(listOf(hymnNumber, hymnTitle).filter(String::isNotBlank).joinToString(" "),
                                color = DioceseNavy, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                            Text(hymn["lyrics"].asText().ifBlank { "Hymn lyrics will appear here when available." },
                                color = CardText, fontSize = 16.sp, lineHeight = 25.sp)
                            val tune = hymn["tune_name"].asText().ifBlank { hymn["tune"].asText() }
                            if (tune.isNotBlank()) Text("Tune: $tune", color = Color.Gray, fontSize = 13.sp)
                            OutlinedButton(onClick = { openPage("devotional-centre") }, modifier = Modifier.fillMaxWidth()) {
                                Text("View All Scripture & Hymns", color = DioceseNavy)
                            }
                        }
                    }
                }
                item {
                    SectionTitle("EXPLORE THE DIOCESE")
                    val tiles = listOf(
                        Triple("Church Directory", "Locate a Church", "⌖") to ("churches" to DioceseNavy),
                        Triple("New Converts", "Start Your Journey", "▤") to ("new-converts" to Color(0xFF087344)),
                        Triple("Prayer Request", "We Pray With You", "🙏") to ("prayer-request" to Color(0xFFB58B20)),
                        Triple("Give Online", "Support God's Work", "♡") to ("giving" to DioceseRed),
                        Triple("Events", "Stay Informed", "▦") to ("events" to Color(0xFF087CB5)),
                        Triple("Live Streaming", "Watch Our Services", "▶") to ("live" to Color(0xFF4822B5)),
                        Triple("Sermons", "Listen & Be Blessed", "♫") to ("sermons" to DioceseNavy),
                        Triple("Fellowships", "Ministries & Groups", "✥") to ("fellowships" to Color(0xFF263D9B)),
                        Triple("Member Portal", "Registration & Login", "♙") to ("member/login" to Color(0xFF087344))
                    )
                    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        tiles.chunked(3).forEach { rowTiles ->
                            Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                                rowTiles.forEach { (tile, destination) ->
                                    Box(Modifier.weight(1f)) {
                                        ExploreTile(tile.first, tile.second, tile.third, destination.second) { openPage(destination.first) }
                                    }
                                }
                                if (rowTiles.size < 3) repeat(3 - rowTiles.size) { Spacer(Modifier.weight(1f)) }
                            }
                        }
                    }
                }
                item { SectionTitle("OUR LEADERSHIP") }
                items(leadership) { person ->
                    Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                            val photo = imageUrl(person["photo_path"].asText())
                            if (photo.isNotBlank()) {
                                AsyncImage(model = photo, contentDescription = person["full_name"].asText(),
                                    modifier = Modifier.fillMaxWidth().height(235.dp).clip(RoundedCornerShape(12.dp)).background(Color(0xFFF4F5F8)),
                                    contentScale = ContentScale.Fit)
                            }
                            Text(person["title"].asText(), color = DioceseRed, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text(person["full_name"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 21.sp)
                            Text(person["biography"].asText(), color = Color(0xFF667085), fontSize = 14.sp)
                        }
                    }
                }
                item {
                    Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = DioceseNavy)) {
                        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("WORSHIP WITH US", color = DioceseGold, fontWeight = FontWeight.Bold, fontSize = 19.sp)
                            Text("Methodist Church Nigeria · Delta South Diocese", color = Color.White, fontSize = 17.sp)
                            Text(content["livestream_announcement"].asText().ifBlank { "Join our worship services and church broadcasts." },
                                color = Color(0xFFE7EAF2))
                            Button(onClick = { openPage("live") }, modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(containerColor = DioceseRed)) { Text("Watch Live Service") }
                            OutlinedButton(onClick = { openPage("giving") }, modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)) { Text("Give Online") }
                        }
                    }
                }
                item { SectionTitle("LATEST ANNOUNCEMENTS") }
                items(events) { event ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(16.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Text(event["title"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text(event["event_date"].asText(), color = DioceseRed, fontSize = 12.sp)
                            Text(event["description"].asText(), color = CardText)
                            Text(event["venue"].asText(), color = Color.Gray, fontSize = 13.sp)
                        }
                    }
                }
                item { SectionTitle("SERMONS & TEACHINGS") }
                items(sermons) { sermon ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(16.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                            Text(sermon["title"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text(sermon["description"].asText(), color = CardText)
                            if (sermon["video_url"].asText().isNotBlank()) OutlinedButton(onClick = {
                                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(sermon["video_url"].asText()))) }
                            }) { Text("Watch / Listen") }
                        }
                    }
                }
                item { SectionTitle("OUR CHURCH GALLERY") }
                items(gallery) { photo ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(16.dp)) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            val url = photo["signed_url"].asText()
                            if (url.isNotBlank()) AsyncImage(model = url, contentDescription = photo["title"].asText(),
                                modifier = Modifier.fillMaxWidth().height(210.dp).clip(RoundedCornerShape(10.dp)), contentScale = ContentScale.Crop)
                            Text(photo["title"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold)
                            Text(photo["description"].asText(), color = Color.Gray, fontSize = 13.sp)
                        }
                    }
                }
                item { SectionTitle("FEATURED CHURCH VIDEOS") }
                items(videos) { video ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(16.dp)) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(video["title"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text(video["description"].asText(), color = CardText)
                            val url = video["signed_url"].asText()
                            OutlinedButton(enabled = url.isNotBlank(), onClick = {
                                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
                            }) { Text("Watch Video") }
                        }
                    }
                }
                item {
                    SectionTitle("HAPPY BIRTHDAY!")
                    Text("We celebrate our members on their birthdays.", color = CardText)
                }
                items(birthdays) { member ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(14.dp)) {
                        Column(Modifier.padding(12.dp)) {
                            Text(member["full_name"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold)
                            Text(listOf(member["circuit"].asText(), member["church_name"].asText()).filter(String::isNotBlank).joinToString(" · "),
                                color = Color.Gray, fontSize = 13.sp)
                        }
                    }
                }
                item { SectionTitle("FIND A CHURCH") }
                items(churches) { church ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(14.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(church["church_name"].asText(), color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                            Text(church["circuit"].asText(), color = DioceseRed, fontWeight = FontWeight.SemiBold)
                            Text(listOf(church["address"].asText(), church["town"].asText(), church["state"].asText()).filter(String::isNotBlank).joinToString(", "),
                                color = CardText)
                            Text(church["phone"].asText(), color = Color.Gray, fontSize = 13.sp)
                            if (church["maps_url"].asText().isNotBlank()) OutlinedButton(onClick = {
                                runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(church["maps_url"].asText()))) }
                            }) { Text("Open Map") }
                        }
                    }
                }
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = DioceseNavy), shape = RoundedCornerShape(18.dp)) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                            Text("ABOUT OUR DIOCESE", color = DioceseGold, fontWeight = FontWeight.Bold, fontSize = 19.sp)
                            Text("Vision", color = Color.White, fontWeight = FontWeight.Bold)
                            Text(content["vision"].asText().ifBlank { "To be spiritually vibrant and one of the largest Churches in Nigeria." }, color = Color.White)
                            Text("Mission", color = Color.White, fontWeight = FontWeight.Bold)
                            val mission = listOf("mission_1", "mission_2", "mission_3").map { content[it].asText() }.filter(String::isNotBlank)
                            if (mission.isEmpty()) {
                                Text("• To consistently win more souls for Christ.\n• To develop spiritually fulfilled members.\n• To remain active in serving humanity.", color = Color.White)
                            } else mission.forEach { Text("• $it", color = Color.White) }
                        }
                    }
                }
            }
        }
    }
}
