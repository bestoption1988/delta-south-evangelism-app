package ng.mcn.deltasouth.evangelism

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.basicMarquee
import androidx.compose.foundation.clickable
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.background
import androidx.compose.foundation.Image
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.*
import androidx.compose.foundation.rememberScrollState
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

private fun churchCircuitKey(value: String): String = value.lowercase().replace(" circuit", "").trim()

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
    var menuExpanded by remember { mutableStateOf(false) }

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
    val churches = payload["churches"].asObjects().filterNot { church ->
        val name = church["church_name"].asText().trim()
        Regex("(?i)^.*\\b(local\\s+)?church\\s*\\d+$").matches(name)
    }.sortedWith(compareBy<Map<String, Any?>> {
        when (churchCircuitKey(it["circuit"].asText())) { "effurun" -> 0; "warri" -> 1; "sapele" -> 2; "steel town" -> 3; else -> 4 }
    }.thenBy { it["church_name"].asText().lowercase() })
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
                        modifier = Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(14.dp)).padding(horizontal = 10.dp, vertical = 9.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Image(
                            painter = painterResource(id = R.drawable.app_logo),
                            contentDescription = "Methodist Church Nigeria crest",
                            modifier = Modifier.size(54.dp),
                            contentScale = ContentScale.Fit
                        )
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("METHODIST CHURCH NIGERIA", color = DioceseNavy, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("DELTA SOUTH DIOCESE", color = DioceseRed, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("WORSHIP · WITNESS · SERVICE · DISCIPLESHIP", color = Color.Gray, fontSize = 8.sp)
                        }
                        Button(onClick = onStaffLogin, contentPadding = PaddingValues(horizontal = 8.dp, vertical = 7.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = DioceseRed)) { Text("Member Portal / Login", fontSize = 9.sp, maxLines = 2) }
                    }
                    Box(Modifier.fillMaxWidth()) {
                        Button(onClick = { menuExpanded = true }, modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = DioceseNavy)) {
                            Text("☰   Menu", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Start, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        }
                        DropdownMenu(expanded = menuExpanded, onDismissRequest = { menuExpanded = false },
                            modifier = Modifier.fillMaxWidth().background(Color.White)) {
                            listOf("Home" to "/", "Church Membership" to "/login",
                                "New Converts / Registration" to "/account-registration", "Member Portal / Login" to "/login",
                                "Admin & Staff Portal" to "/login", "Prayer Request" to "/prayer-request",
                                "Online Giving" to "/giving", "Events & Announcements" to "/#events",
                                "Live Streaming" to "/live", "Sermons & Media Library" to "/#watch",
                                "Devotional Centre" to "/devotional-centre", "Photo Gallery" to "/#photo-gallery",
                                "Church Directory" to "/#churches", "Fellowships" to "/fellowships",
                                "Contact Us" to "/#contact").forEach { (label, route) ->
                                DropdownMenuItem(text = { Text(label, color = DioceseNavy) },
                                    onClick = { menuExpanded = false; if (route != "/") openPage(route) })
                            }
                        }
                    }
                }
                item {
                    val scriptureLine = "✝ SCRIPTURE: " + verse["reference"].asText() + " — " + verse["text"].asText().replace("\n"," ")
                    val hymnLine = "♫ HYMN: " + hymn["title"].asText() + " — " + hymn["lyrics"].asText().replace("\n"," ")
                    var readingPopup by remember { mutableStateOf("") }
                    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(14.dp)) {
                        Column(Modifier.fillMaxWidth().padding(vertical = 9.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text((scriptureLine + "     •     " + hymnLine).replace(Regex("\\s+"), " ").trim(),
                                modifier = Modifier.fillMaxWidth().clickable { readingPopup = "scripture" }.basicMarquee().padding(horizontal = 12.dp),
                                color = DioceseNavy, maxLines = 1, softWrap = false, fontSize = 13.sp)
                            Row(Modifier.fillMaxWidth().padding(horizontal = 8.dp), horizontalArrangement = Arrangement.End) {
                                TextButton(onClick = { readingPopup = "scripture" }) { Text("View Full Scripture", color = DioceseRed, fontSize = 11.sp) }
                                TextButton(onClick = { readingPopup = "hymn" }) { Text("View Full Hymn", color = DioceseRed, fontSize = 11.sp) }
                            }
                        }
                    }
                    if (readingPopup.isNotBlank()) {
                        val isHymn = readingPopup == "hymn"
                        AlertDialog(
                            onDismissRequest = { readingPopup = "" },
                            confirmButton = { TextButton(onClick = { readingPopup = "" }) { Text("Close") } },
                            title = { Text(if (isHymn) hymn["title"].asText().ifBlank { "Methodist Hymn for Today" } else verse["reference"].asText().ifBlank { "Scripture for Today" }, color = DioceseNavy) },
                            text = {
                                Column(Modifier.heightIn(max = 420.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text(if (isHymn) hymn["lyrics"].asText().ifBlank { "Hymn lyrics are not available." } else verse["text"].asText().ifBlank { "Scripture text is not available." }, color = CardText)
                                    if (isHymn) {
                                        val tune = hymn["tune_name"].asText().ifBlank { hymn["tune"].asText().ifBlank { hymn["meter"].asText() } }
                                        if (tune.isNotBlank()) Text("Tune: $tune", color = DioceseRed, fontWeight = FontWeight.SemiBold)
                                        val audio = hymn["audio_url"].asText()
                                        if (audio.isNotBlank()) Button(onClick = { runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(audio))) } }, modifier = Modifier.fillMaxWidth()) { Text("▶ Play Hymn Tune") }
                                    }
                                    TextButton(onClick = { openPage("/devotional-centre") }) { Text("View All Scripture & Hymns") }
                                }
                            }
                        )
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
                    Card(shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = DioceseNavy)) {
                        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("LIVE SERVICE", color = Color.White, fontWeight = FontWeight.Bold,
                                modifier = Modifier.background(DioceseRed, RoundedCornerShape(8.dp)).padding(9.dp))
                            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(
                                Brush.linearGradient(listOf(Color(0xFF17264A), Color(0xFF9C7655), Color(0xFF101C3D))))
                                .height(270.dp), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text("✝", color = DioceseGold, fontSize = 48.sp)
                                    Text("Worship with Us", color = Color.White, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                                    Text("Methodist Church Nigeria\nDelta South Diocese", color = Color.White, textAlign = TextAlign.Center, fontSize = 17.sp)
                                    Button(onClick = { openPage("/live") }, colors = ButtonDefaults.buttonColors(containerColor = DioceseRed)) { Text("Watch & Listen") }
                                    OutlinedButton(onClick = onStaffLogin, colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)) { Text("Member Conference Login") }
                                }
                            }
                            Text(content["livestream_announcement"].asText().ifBlank { "Live service video will appear here when the official stream is configured." }, color = Color(0xFFDCE3F4))
                        }
                    }
                }
                item {
                    SectionTitle("EXPLORE THE DIOCESE")
                    val tiles = listOf(
                        Triple("Church Directory", "Locate a Church", "⌖") to ("/#churches" to DioceseNavy),
                        Triple("New Converts", "Start Your Journey", "▤") to ("/account-registration" to Color(0xFF087344)),
                        Triple("Prayer Request", "We Pray With You", "🙏") to ("/prayer-request" to Color(0xFFB58B20)),
                        Triple("Give Online", "Support God's Work", "♡") to ("/giving" to DioceseRed),
                        Triple("Events", "Stay Informed", "▦") to ("/#events" to Color(0xFF087CB5)),
                        Triple("Live Streaming", "Watch Our Services", "▶") to ("/live" to Color(0xFF4822B5)),
                        Triple("Sermons", "Listen & Be Blessed", "♫") to ("/#watch" to DioceseNavy),
                        Triple("Fellowships", "Ministries & Groups", "✥") to ("/fellowships" to Color(0xFF263D9B)),
                        Triple("Member Portal", "Registration & Login", "♙") to ("/login" to Color(0xFF087344))
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
                            Button(onClick = { openPage("/live") }, modifier = Modifier.fillMaxWidth(),
                                colors = ButtonDefaults.buttonColors(containerColor = DioceseRed)) { Text("Watch Live Service") }
                            OutlinedButton(onClick = { openPage("/giving") }, modifier = Modifier.fillMaxWidth(),
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
                item {
                    SectionTitle("WATCH & LISTEN")
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(
                            Triple("▶", "Live Service", "/live"),
                            Triple("🎙", "Recent Sermons", "/media-library/sermons"),
                            Triple("📖", "Bible Teachings", "/media-library/bible-teachings"),
                            Triple("🎤", "Special Programmes", "/media-library?type=video"),
                            Triple("♫", "Choir & Music", "/media-library/choir-music"),
                            Triple("♡", "Testimonies", "/#resources")
                        ).forEach { item ->
                            Card(onClick = { openPage(item.third) }, colors = CardDefaults.cardColors(containerColor = Color.White)) {
                                Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Text(item.first, fontSize = 22.sp)
                                    Spacer(Modifier.width(12.dp))
                                    Text(item.second, color = DioceseNavy, fontWeight = FontWeight.SemiBold)
                                    Spacer(Modifier.weight(1f))
                                    Text("›", color = DioceseRed, fontSize = 22.sp)
                                }
                            }
                        }
                    }
                }
                item { SectionTitle("SERMONS & TEACHINGS") }
                if (sermons.isEmpty()) item { Text("No sermons have been published yet. Please check back soon.", color = Color.Gray) }
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
                item {
                    SectionTitle("OUR CHURCH GALLERY")
                    if (gallery.isEmpty()) {
                        Text("Church photographs will appear here when published.", color = Color.Gray)
                    } else {
                        var galleryIndex by remember { mutableIntStateOf(0) }
                        LaunchedEffect(gallery.size) {
                            while (gallery.size > 1) {
                                kotlinx.coroutines.delay(4500)
                                galleryIndex = (galleryIndex + 1) % gallery.size
                            }
                        }
                        val photo = gallery[galleryIndex]
                        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
                            Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                AsyncImage(model = photo["signed_url"].asText().ifBlank { photo["public_url"].asText().ifBlank { photo["image_url"].asText() } }, contentDescription = photo["title"].asText(),
                                    modifier = Modifier.fillMaxWidth().height(230.dp).clip(RoundedCornerShape(12.dp)),
                                    contentScale = ContentScale.Crop)
                                Text(photo["title"].asText().takeUnless { it.matches(Regex("(?i)^file_[a-f0-9]{12,}$")) } ?: "Diocesan Gallery",
                                    color = DioceseNavy, fontWeight = FontWeight.Bold)
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    TextButton(onClick = { galleryIndex = (galleryIndex - 1 + gallery.size) % gallery.size }) { Text("‹ Previous") }
                                    Text("${galleryIndex + 1} / ${gallery.size}", color = Color.Gray)
                                    TextButton(onClick = { galleryIndex = (galleryIndex + 1) % gallery.size }) { Text("Next ›") }
                                }
                                TextButton(onClick = { openPage("/#photo-gallery") }, modifier = Modifier.align(Alignment.End)) { Text("View Gallery") }
                            }
                        }
                    }
                }
                item { SectionTitle("FEATURED CHURCH VIDEOS") }
                if (videos.isEmpty()) item { Text("No church videos have been published yet.", color = Color.Gray) }
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
                if (birthdays.isEmpty()) item { Text("There are no member birthdays listed for today.", color = Color.Gray) }
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
                if (churches.isEmpty()) item { Text("Church directory records are being updated. Please check again soon.", color = Color.Gray) }
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
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = DioceseNavy), shape = RoundedCornerShape(18.dp)) {
                        Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Image(painter = painterResource(id = R.drawable.app_logo), contentDescription = "Methodist Church Nigeria",
                                    modifier = Modifier.size(54.dp), contentScale = ContentScale.Fit)
                                Spacer(Modifier.width(10.dp))
                                Column {
                                    Text("METHODIST CHURCH NIGERIA", color = Color.White, fontWeight = FontWeight.Bold)
                                    Text("DELTA SOUTH DIOCESE", color = DioceseGold, fontWeight = FontWeight.Bold)
                                }
                            }
                            Text("WORSHIP · WITNESS · SERVICE · DISCIPLESHIP", color = Color.White)
                            Text("CONTACT THE DIOCESE", color = DioceseGold, fontWeight = FontWeight.Bold)
                            val contactEmail = content["contact_email"].asText()
                            val contactPhone = content["contact_phone"].asText()
                            val contactAddress = content["contact_address"].asText()
                            if (contactPhone.isNotBlank()) Text("Phone: $contactPhone", color = Color.White)
                            if (contactEmail.isNotBlank()) Text("Email: $contactEmail", color = Color.White)
                            if (contactAddress.isNotBlank()) Text("Address: $contactAddress", color = Color.White)
                            Text("Useful Links", color = DioceseGold, fontWeight = FontWeight.Bold)
                            listOf("About Us" to "/#about", "Our Diocese" to "/#diocese", "Ministries & Fellowships" to "/fellowships",
                                "Events" to "/#events", "Sermons" to "/#watch", "Photo Gallery" to "/#photo-gallery",
                                "Devotional Centre" to "/devotional-centre", "Member Login" to "/login",
                                "Online Giving" to "/giving", "Prayer Request" to "/prayer-request", "Live Service" to "/live").forEach { (label, route) ->
                                TextButton(onClick = { openPage(route) }) { Text(label, color = Color.White) }
                            }
                            Text("“Together for a Greater Harvest in His Kingdom.”", color = Color.White)
                            Text("© ${java.util.Calendar.getInstance().get(java.util.Calendar.YEAR)} Methodist Church Nigeria, Delta South Diocese. All rights reserved.",
                                color = Color(0xFFD9DEEA), fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}
