package ng.mcn.deltasouth.evangelism
import java.util.Locale

import android.content.Context
import android.text.Html
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.ExistingWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import okhttp3.Request
import android.database.sqlite.SQLiteDatabase
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.util.concurrent.TimeUnit
import java.util.concurrent.Executors

data class OfflineDownloadSummary(val downloaded: Int, val unavailable: Int, val failed: Int, val mediaDownloaded: Int = 0)

object OfflineAttendanceQueue {
    @Volatile private var preferences: android.content.SharedPreferences? = null

    private fun store(context: Context): android.content.SharedPreferences {
        preferences?.let { return it }
        synchronized(this) {
            preferences?.let { return it }
            val key = MasterKey.Builder(context.applicationContext)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
            val created = EncryptedSharedPreferences.create(
                context.applicationContext,
                "mcn_offline_attendance_queue",
                key,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            preferences = created
            return created
        }
    }

    fun enqueueAttendance(context: Context, data: Map<String, String>): String {
        val prefs = store(context)
        val queue = JSONArray(prefs.getString("items", "[]") ?: "[]")
        val id = UUID.randomUUID().toString()
        val payload = JSONObject()
        data.forEach { (key, value) -> payload.put(key, value) }
        queue.put(JSONObject()
            .put("operation_id", id)
            .put("type", "attendance")
            .put("data", payload)
            .put("queued_at", System.currentTimeMillis()))
        prefs.edit().putString("items", queue.toString()).apply()
        return id
    }

    fun pendingCount(context: Context): Int =
        runCatching { JSONArray(store(context).getString("items", "[]") ?: "[]").length() }.getOrDefault(0)

    suspend fun syncPending(context: Context): Int {
        val prefs = store(context)
        val queue = JSONArray(prefs.getString("items", "[]") ?: "[]")
        val remaining = JSONArray()
        var synced = 0
        for (index in 0 until queue.length()) {
            val item = queue.optJSONObject(index) ?: continue
            try {
                val dataObject = item.optJSONObject("data") ?: JSONObject()
                val data = mutableMapOf<String, String>()
                val keys = dataObject.keys()
                while (keys.hasNext()) {
                    val key = keys.next()
                    data[key] = dataObject.optString(key)
                }
                val operation = mapOf(
                    "operation_id" to item.optString("operation_id"),
                    "type" to item.optString("type"),
                    "data" to data
                )
                val result = Backend.api.syncOfflineAttendance(mapOf("operation" to operation))
                if (result["ok"] == true) synced++ else remaining.put(item)
            } catch (_: Exception) {
                remaining.put(item)
            }
        }
        prefs.edit().putString("items", remaining.toString()).apply()
        return synced
    }
}

object OfflineModuleManager {
    // These are the native app's role-protected read modules. Server authorization remains authoritative.
    private val moduleRequests = listOf(
        "api/me",
        "api/dashboard",
        "api/communications",
        "api/command-centre",
        "api/public/churches",
        "api/member/records",
        "api/member/id-card",
        "api/member/attendance-summary",
        "api/member/attendance",
        "api/member/giving-history",
        "api/member/announcements",
        "api/member/events",
        "api/member/notifications",
        "api/member/testimonies",
        "api/member/appreciations",
        "api/membership/churches",
        "api/circuits",
        "api/members",
        "api/membership-statistics",
        "api/member-registrations",
        "api/member-appointment-options",
        "api/conference",
        "api/finance-summary",
        "api/payment-history",
        "api/payment-reconciliation",
        "api/admin/reporting-summary",
        "api/financial-accountability-report",
        "api/user-linkable-members",
        "api/security/status",
        "api/security/backups",
        "api/users",
        "api/account-requests",
        "api/system/health",
        "api/system/data-quality",
        "api/system/data-quality/details",
        "api/system/workflow-check",
        "api/system/info",
        "api/system/deployment-check",
        "api/audit",
        "api/customer-care",
        "api/customer-care/unread-count",
        "api/church-accounts",
    )

    fun downloadAll(context: Context, onProgress: (String, Int) -> Unit = { _, _ -> }): OfflineDownloadSummary {
        Backend.initialize(context.applicationContext)
        var downloaded = 0
        var unavailable = 0
        var failed = 0
        var mediaDownloaded = 0
        val totalSteps = moduleRequests.size + 5
        var completedSteps = 0
        fun report(stage: String) { completedSteps++; onProgress(stage, (completedSteps * 100 / totalSteps).coerceIn(0, 99)) }
        onProgress("Preparing secure offline package…", 0)
        moduleRequests.forEach { path ->
            try {
                val request = Request.Builder()
                    .url(BuildConfig.API_BASE_URL + path)
                    .get()
                    .build()
                Backend.client.newCall(request).execute().use { response ->
                    val type = response.body?.contentType()?.subtype.orEmpty()
                    if (response.isSuccessful && type.contains("json", ignoreCase = true)) {
                        // Reading the body causes OfflineResponseCache's interceptor to persist it encrypted.
                        response.body?.string()
                        downloaded++
                    } else if (response.code == 401 || response.code == 403 || response.code == 404) {
                        unavailable++
                    } else {
                        failed++
                    }
                }
            } catch (_: Exception) {
                failed++
            }
            report("Saving account data: ${path.substringAfterLast('/')}")
        }
        try {
            onProgress("Downloading hymns, Scripture and worship books…", completedSteps * 100 / totalSteps)
            val devotionalCount = downloadAllDevotionalResources(context)
            if (devotionalCount > 0) downloaded++
        } catch (_: Exception) {
            failed++
        }
        report("Devotional readings saved")
        // Save published hymn recordings as part of the same whole-app package.
        try {
            downloadHymnAudio(context) { stage, percent -> onProgress(stage, ((completedSteps + percent / 100f) * 100 / totalSteps).toInt().coerceIn(0, 99)) }
        } catch (_: Exception) {
            failed++
        }
        report("Hymn recordings processed")
        try {
            onProgress("Saving lectionary…", completedSteps * 100 / totalSteps)
            downloadLectionary(context)
            downloaded++
        } catch (_: Exception) {
            failed++
        }
        report("Lectionary saved")
        // Save the user's uploaded MyBible modules into the phone's Bible library.
        try {
            onProgress("Downloading uploaded Bible library modules…", completedSteps * 100 / totalSteps)
            val savedBibleModules = downloadBibleModules(context) { stage, percent ->
                onProgress(stage, ((completedSteps + percent / 100f) * 100 / totalSteps).toInt().coerceIn(0, 99))
            }
            if (savedBibleModules > 0) downloaded++
            else unavailable++
        } catch (_: Exception) {
            failed++
        }
        report("Uploaded Bible library saved")
        try {
            mediaDownloaded = downloadPublishedMedia(context, null) { stage, percent -> onProgress(stage, ((completedSteps + percent / 100f) * 100 / totalSteps).toInt().coerceIn(0, 99)) }
        } catch (_: Exception) {
            failed++
        }
        report("Church audio, video and documents saved")
        onProgress("Offline package complete", 100)
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
            .edit()
            .putLong("last_download_at", System.currentTimeMillis())
            .putInt("last_downloaded_count", downloaded)
            .putInt("last_unavailable_count", unavailable)
            .putInt("last_failed_count", failed)
            .putInt("last_media_downloaded_count", mediaDownloaded)
            .apply()
        return OfflineDownloadSummary(downloaded, unavailable, failed, mediaDownloaded)
    }

    private val devotionalCollections = listOf(
        "english_hymns", "yoruba_hymns", "akokun", "bible_verses",
        "canticles", "communion_english", "communion_yoruba", "creeds"
    )

    private fun devotionalDirectory(context: Context): File =
        File(context.filesDir, "offline_devotional").apply { mkdirs() }

    fun downloadAllDevotionalResources(context: Context): Int {
        var total = 0
        val failures = mutableListOf<String>()
        devotionalCollections.forEach { collection ->
            try {
                total += downloadDevotionalCollection(context, collection, includeAudio = false)
            } catch (error: Exception) {
                failures += "$collection: ${error.message ?: "download failed"}"
            }
        }
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
            .edit().putInt("last_devotional_resources_count", total).apply()
        if (failures.isNotEmpty()) {
            throw IllegalStateException("Downloaded $total resources. Some collections failed: " + failures.joinToString("; "))
        }
        return total
    }

    fun downloadDevotionalCollection(context: Context, collection: String, includeAudio: Boolean = false, onProgress: (String, Int) -> Unit = { _, _ -> }): Int {
        require(collection in devotionalCollections)
        Backend.initialize(context.applicationContext)
        val directory = devotionalDirectory(context)
        val longClient = Backend.client.newBuilder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(300, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.MINUTES)
            .build()
        val allItems = JSONArray()
        var audioDownloaded = 0
        var page = 1
        var pages = 1
        do {
            val url = BuildConfig.API_BASE_URL +
                "api/offline/devotional-resources?collection=" + collection +
                "&page=" + page + "&per_page=100&include_audio=" + if (includeAudio) "1" else "0"
            val request = Request.Builder().url(url).get().build()
            val responseJson = longClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IllegalStateException("Devotional $collection HTTP " + response.code)
                response.body?.string() ?: throw IllegalStateException("Empty devotional response")
            }
            val result = JSONObject(responseJson)
            pages = result.optInt("pages", 1).coerceAtLeast(1)
            val items = result.optJSONArray("items") ?: JSONArray()
            for (index in 0 until items.length()) {
                val item = items.optJSONObject(index) ?: continue
                if (includeAudio) {
                    val id = item.optString("resource_id").replace(Regex("[^A-Za-z0-9_-]"), "_")
                    val audioUrl = item.optString("audio_url")
                    if (audioUrl.isNotBlank()) {
                        val ext = mediaExtension(item.optString("audio_extension"), "audio")
                        val target = File(directory, "hymn_" + id + ext)
                        if (downloadSignedFile(longClient, audioUrl, target) { done, total -> onProgress("Hymn audio: " + item.optString("title", collection), if (total > 0L) (done * 100 / total).toInt() else 0) }) {
                            item.put("audio_file", target.name)
                            audioDownloaded++
                        }
                    }
                    val payload = item.optJSONObject("payload") ?: JSONObject()
                    val tunes = payload.optJSONArray("otherTunes")
                    if (tunes != null) {
                        for (tuneIndex in 0 until tunes.length()) {
                            val tune = tunes.optJSONObject(tuneIndex) ?: continue
                            val tuneUrl = tune.optString("signed_url")
                            if (tuneUrl.isBlank()) continue
                            val tuneExt = mediaExtension(tune.optString("audio_extension"), "audio")
                            val tuneFile = File(directory, "hymn_" + id + "_tune" + tuneIndex + tuneExt)
                            if (downloadSignedFile(longClient, tuneUrl, tuneFile) { done, total -> onProgress("Hymn tune: " + item.optString("title", collection), if (total > 0L) (done * 100 / total).toInt() else 0) }) {
                                tune.put("offline_file", tuneFile.name)
                                audioDownloaded++
                            }
                        }
                    }
                    item.put("payload", payload)
                }
                allItems.put(item)
            }
            page++
        } while (page <= pages)
        val target = File(directory, collection + ".json")
        val temporary = File(directory, collection + ".json.part")
        temporary.writeText(allItems.toString())
        if (target.exists()) target.delete()
        if (!temporary.renameTo(target)) {
            temporary.copyTo(target, overwrite = true)
            temporary.delete()
        }
        return if (includeAudio) audioDownloaded else allItems.length()
    }

    fun downloadHymnAudio(context: Context, onProgress: (String, Int) -> Unit = { _, _ -> }): Int {
        var total = 0
        val failures = mutableListOf<String>()
        val collections = listOf("english_hymns", "yoruba_hymns", "akokun")
        collections.forEachIndexed { index, collection ->
            try {
                onProgress("Downloading hymn audio: ${collection.replace('_', ' ')} (${index + 1}/${collections.size})", index * 100 / collections.size)
                total += downloadDevotionalCollection(context, collection, includeAudio = true, onProgress = onProgress)
            } catch (error: Exception) {
                failures += "$collection: ${error.message ?: "download failed"}"
            }
            onProgress("Hymn audio: ${collection.replace('_', ' ')} processed", (index + 1) * 100 / collections.size)
        }
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
            .edit().putInt("last_devotional_audio_count", total).apply()
        if (failures.isNotEmpty()) {
            throw IllegalStateException("Saved $total audio files. Some hymn collections failed: " + failures.joinToString("; "))
        }
        if (total == 0) throw IllegalStateException("No hymn recordings were downloaded. Please check that the audio files are published.")
        return total
    }

    fun downloadLectionary(context: Context): Boolean {
        val request = Request.Builder().url(BuildConfig.API_BASE_URL + "api/offline/lectionary").get().build()
        val json = Backend.client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IllegalStateException("Lectionary HTTP " + response.code)
            response.body?.string() ?: throw IllegalStateException("Empty lectionary")
        }
        val content = JSONObject(json).optString("content")
        File(devotionalDirectory(context), "lectionary_2027.txt").writeText(content)
        return true
    }

    fun removeLegacyBibleFiles(context: Context) {
        runCatching { File(context.filesDir, "offline_web_bible").deleteRecursively() }
        runCatching { File(devotionalDirectory(context), "csb_pew_bible.pdf").delete() }
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE).edit()
            .remove("last_web_bible_chapter_count")
            .remove("last_web_bible_missing_count")
            .apply()
    }

    fun bibleModuleDirectory(context: Context): File =
        File(context.filesDir, "bible_modules").apply { mkdirs() }

    fun downloadBibleModules(context: Context, onProgress: (String, Int) -> Unit = { _, _ -> }): Int {
        Backend.initialize(context.applicationContext)
        val listRequest = Request.Builder()
            .url(BuildConfig.API_BASE_URL + "api/offline/bible-modules")
            .get().build()
        val modulesJson = Backend.client.newCall(listRequest).execute().use { response ->
            if (!response.isSuccessful) throw IllegalStateException("Uploaded Bible library HTTP " + response.code)
            JSONObject(response.body?.string() ?: "{}")
        }
        val modules = modulesJson.optJSONArray("modules") ?: JSONArray()
        val directory = bibleModuleDirectory(context)
        val index = JSONArray()
        var saved = 0
        val available = (0 until modules.length()).mapNotNull { modules.optJSONObject(it) }
            .filter { it.optString("id").isNotBlank() && it.optString("id") != "web" }
        available.forEachIndexed { position, module ->
            val code = module.optString("id").lowercase(Locale.ROOT)
            val title = module.optString("title", code.uppercase(Locale.ROOT))
            val filename = module.optString("filename").ifBlank { code + ".bbl.mybible" }
            val safeFilename = filename.substringAfterLast('/').replace(Regex("[^A-Za-z0-9._-]"), "_")
            val target = File(directory, safeFilename)
            if (!target.isFile || target.length() < 1024L) {
                val temporary = File(directory, safeFilename + ".part")
                val request = Request.Builder()
                    .url(BuildConfig.API_BASE_URL + "api/offline/bible-module/" + code)
                    .get().build()
                Backend.client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) throw IllegalStateException("Bible module " + code + " HTTP " + response.code)
                    val body = response.body ?: throw IllegalStateException("Empty Bible module " + code)
                    body.byteStream().use { input -> temporary.outputStream().use { output -> input.copyTo(output) } }
                }
                if (temporary.length() < 1024L || !temporary.inputStream().use { input ->
                    val header = ByteArray(16); input.read(header); String(header, Charsets.US_ASCII).startsWith("SQLite format 3")
                }) {
                    temporary.delete()
                    throw IllegalStateException("Invalid uploaded Bible module: " + code)
                }
                if (target.exists()) target.delete()
                if (!temporary.renameTo(target)) temporary.copyTo(target, overwrite = true).also { temporary.delete() }
            }
            index.put(JSONObject().put("id", code).put("title", title).put("file", safeFilename))
            saved++
            onProgress("Bible library: " + title, ((position + 1) * 100 / available.size.coerceAtLeast(1)))
        }
        val indexFile = File(directory, "index.json")
        val temporaryIndex = File(directory, "index.json.part")
        temporaryIndex.writeText(index.toString())
        if (indexFile.exists()) indexFile.delete()
        if (!temporaryIndex.renameTo(indexFile)) temporaryIndex.copyTo(indexFile, overwrite = true).also { temporaryIndex.delete() }
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
            .edit().putInt("last_uploaded_bible_module_count", saved).apply()
        return saved
    }

    private fun localBibleModule(context: Context, code: String): File? {
        if (code.isBlank() || code.equals("web", ignoreCase = true)) return null
        val indexFile = File(bibleModuleDirectory(context), "index.json")
        if (!indexFile.isFile) return null
        val index = JSONArray(indexFile.readText())
        for (i in 0 until index.length()) {
            val item = index.optJSONObject(i) ?: continue
            if (item.optString("id").equals(code, ignoreCase = true)) {
                val file = File(bibleModuleDirectory(context), item.optString("file"))
                return file.takeIf { it.isFile && it.length() > 1024L }
            }
        }
        return null
    }

    fun cachedBibleModuleResponse(context: Context, requestUrl: String): ByteArray? {
        return runCatching {
            val uri = android.net.Uri.parse(requestUrl)
            val path = uri.path.orEmpty()
            if (path != "/devotional-centre/holy-bible/books" &&
                path != "/devotional-centre/holy-bible/chapter") return null
            val code = uri.getQueryParameter("translation")?.lowercase(Locale.ROOT).orEmpty()
            val file = localBibleModule(context, code) ?: return null
            val db = SQLiteDatabase.openDatabase(file.absolutePath, null, SQLiteDatabase.OPEN_READONLY)
            try {
                val result = if (path.endsWith("/books")) {
                    val books = JSONArray()
                    db.rawQuery("SELECT Book, MAX(Chapter) AS chapters FROM Bible GROUP BY Book ORDER BY Book", null).use { cursor ->
                        while (cursor.moveToNext()) {
                            books.put(JSONObject().put("id", cursor.getInt(0)).put("chapters", cursor.getInt(1)))
                        }
                    }
                    JSONObject().put("translation", code).put("books", books).toString()
                } else {
                    val book = uri.getQueryParameter("book")?.toIntOrNull() ?: return null
                    val chapter = uri.getQueryParameter("chapter")?.toIntOrNull() ?: return null
                    val verses = JSONArray()
                    db.rawQuery(
                        "SELECT Verse, Scripture FROM Bible WHERE Book=? AND Chapter=? ORDER BY Verse",
                        arrayOf(book.toString(), chapter.toString())
                    ).use { cursor ->
                        while (cursor.moveToNext()) {
                            val scripture = cursor.getString(1).orEmpty()
                                .replace(Regex("<RF>.*?<Rf>", RegexOption.IGNORE_CASE), "")
                                .replace(Regex("<[^>]*>"), "")
                                .replace(Regex("\\s+"), " ").trim()
                            verses.put(JSONObject().put("verse", cursor.getInt(0)).put("text", scripture))
                        }
                    }
                    JSONObject().put("translation", code).put("book", book)
                        .put("chapter", chapter).put("verses", verses).toString()
                }
                result.toByteArray(Charsets.UTF_8)
            } finally {
                db.close()
            }
        }.getOrNull()
    }

    private fun mediaExtension(path: String, type: String): String {
        val ext = path.substringAfterLast('.', "").substringBefore('?').lowercase(Locale.ROOT)
        return if (ext.matches(Regex("[a-z0-9]{2,5}"))) ".$ext" else if (type == "audio") ".mp3" else ".bin"
    }

    private fun downloadSignedFile(client: okhttp3.OkHttpClient, url: String, target: File, onBytes: (Long, Long) -> Unit = { _, _ -> }): Boolean {
        return runCatching {
            if (target.exists() && target.length() > 0L) return true
            val temporary = File(target.parentFile, target.name + ".part")
            val request = Request.Builder().url(url).get().build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IllegalStateException("Media HTTP " + response.code)
                val body = response.body ?: throw IllegalStateException("Empty media body")
                body.byteStream().use { input ->
                    temporary.outputStream().use { output ->
                        val buffer = ByteArray(64 * 1024)
                        var copied = 0L
                        val totalBytes = body.contentLength()
                        while (true) {
                            val read = input.read(buffer)
                            if (read < 0) break
                            output.write(buffer, 0, read)
                            copied += read
                            onBytes(copied, totalBytes)
                        }
                    }
                }
            }
            if (temporary.length() <= 0L) throw IllegalStateException("Empty downloaded file")
            if (target.exists()) target.delete()
            if (!temporary.renameTo(target)) {
                temporary.copyTo(target, overwrite = true)
                temporary.delete()
            }
            true
        }.getOrDefault(false)
    }

    fun downloadMediaCategory(context: Context, mediaType: String, onProgress: (String, Int) -> Unit = { _, _ -> }): Int {
        require(mediaType in setOf("audio", "video", "document"))
        val count = downloadPublishedMedia(context, setOf(mediaType), onProgress)
        val directory = offlineMediaDirectory(context)
        val index = runCatching { JSONArray(File(directory, "index.json").readText()) }.getOrDefault(JSONArray())
        context.getSharedPreferences("mcn_offline_status", Context.MODE_PRIVATE)
            .edit().putInt("last_media_downloaded_count", index.length()).apply()
        return count
    }

    private fun downloadPublishedMedia(context: Context, filterTypes: Set<String>?, onProgress: (String, Int) -> Unit = { _, _ -> }): Int {
        val catalogueRequest = Request.Builder()
            .url(BuildConfig.API_BASE_URL + "api/offline/media-catalogue")
            .get()
            .build()
        val longClient = Backend.client.newBuilder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(300, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.MINUTES)
            .build()
        val json = runCatching {
            longClient.newCall(catalogueRequest).execute().use { response ->
                if (!response.isSuccessful) throw IllegalStateException("Media catalogue HTTP " + response.code)
                response.body?.string() ?: throw IllegalStateException("Empty media catalogue")
            }
        }.getOrElse {
            // Older production deployments may not yet expose the JSON catalogue endpoint.
            // The existing public media-library page already contains signed published-media links.
            fetchLegacyMediaCatalogue(longClient)
        }
        val items = org.json.JSONObject(json).optJSONArray("items") ?: JSONArray()
        val directory = File(context.filesDir, "offline_media")
        if (!directory.exists()) directory.mkdirs()
        val oldIndex = runCatching { JSONArray(File(directory, "index.json").readText()) }.getOrDefault(JSONArray())
        val oldEntries = linkedMapOf<String, JSONObject>()
        val oldVersions = mutableMapOf<String, String>()
        for (i in 0 until oldIndex.length()) {
            val old = oldIndex.optJSONObject(i) ?: continue
            oldEntries[old.optString("id")] = old
            oldVersions[old.optString("id")] = old.optString("created_at")
        }
        val selectedItems = (0 until items.length()).mapNotNull { items.optJSONObject(it) }.filter { filterTypes == null || it.optString("media_type", "document") in filterTypes }
        val totalItems = selectedItems.size
        var count = 0
        for ((position, item) in selectedItems.withIndex()) {
            val mediaType = item.optString("media_type", "document")
            val id = item.optString("id")
            val url = item.optString("download_url")
            if (id.isBlank() || url.isBlank()) continue
            val mime = item.optString("mime_type", "application/octet-stream")
            val extension = when {
                mime.contains("pdf", true) -> ".pdf"
                mime.contains("audio", true) -> when {
                    mime.contains("mpeg", true) -> ".mp3"
                    mime.contains("wav", true) -> ".wav"
                    mime.contains("ogg", true) -> ".ogg"
                    mime.contains("mp4", true) -> ".m4a"
                    else -> ".audio"
                }
                mime.contains("video", true) -> when {
                    mime.contains("webm", true) -> ".webm"
                    else -> ".mp4"
                }
                mime.contains("word", true) -> ".docx"
                else -> ".bin"
            }
            val safeId = id.replace(Regex("[^A-Za-z0-9_-]"), "_")
            val target = File(directory, safeId + extension)
            val currentVersion = item.optString("created_at")
            try {
                if (!target.exists() || target.length() == 0L || (currentVersion.isNotBlank() && oldVersions[id] != currentVersion)) {
                    val mediaRequest = Request.Builder().url(url).get().build()
                    longClient.newCall(mediaRequest).execute().use { response ->
                        if (!response.isSuccessful) throw IllegalStateException("Media download HTTP " + response.code)
                        val body = response.body ?: throw IllegalStateException("Empty media file")
                        val temporary = File(directory, safeId + extension + ".part")
                        body.byteStream().use { input ->
                            temporary.outputStream().use { output ->
                                val buffer = ByteArray(64 * 1024)
                                var copied = 0L
                                val totalBytes = body.contentLength()
                                while (true) {
                                    val read = input.read(buffer)
                                    if (read < 0) break
                                    output.write(buffer, 0, read)
                                    copied += read
                                    val itemPercent = if (totalBytes > 0L) (copied * 100 / totalBytes).toInt() else 0
                                    onProgress("Downloading " + mediaType + ": " + item.optString("title", "media item") + " • " + itemPercent + "%", if (totalItems > 0) (position * 100 / totalItems + itemPercent / totalItems).coerceIn(0, 99) else 0)
                                }
                            }
                        }
                        if (temporary.length() == 0L) {
                            temporary.delete()
                            throw IllegalStateException("Downloaded media is empty")
                        }
                        if (target.exists()) target.delete()
                        if (!temporary.renameTo(target)) {
                            temporary.copyTo(target, overwrite = true)
                            temporary.delete()
                        }
                    }
                }
                oldEntries[id] = JSONObject()
                    .put("id", id)
                    .put("title", item.optString("title"))
                    .put("description", item.optString("description"))
                    .put("mime_type", mime)
                    .put("media_type", mediaType)
                    .put("file", target.name)
                    .put("created_at", currentVersion)
                count++
            } catch (_: Exception) {
                // One unavailable media object must not cancel the rest of the library.
            }
            val title = item.optString("title", "media item")
            onProgress("Downloading $mediaType: $title (${position + 1}/$totalItems)", if (totalItems == 0) 100 else (position + 1) * 100 / totalItems)
        }
        val index = JSONArray()
        oldEntries.values.forEach { entry ->
            val file = File(directory, entry.optString("file"))
            if (file.exists() && file.length() > 0L) index.put(entry)
        }
        val indexFile = File(directory, "index.json")
        val temporaryIndex = File(directory, "index.json.part")
        temporaryIndex.writeText(index.toString())
        if (indexFile.exists()) indexFile.delete()
        if (!temporaryIndex.renameTo(indexFile)) {
            temporaryIndex.copyTo(indexFile, overwrite = true)
            temporaryIndex.delete()
        }
        return count
    }

    private fun fetchLegacyMediaCatalogue(client: okhttp3.OkHttpClient): String {
        val request = Request.Builder().url(BuildConfig.API_BASE_URL + "media-library").get().build()
        val html = client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IllegalStateException("Public media library HTTP " + response.code)
            response.body?.string() ?: throw IllegalStateException("Empty public media library")
        }
        val items = JSONArray()
        val cards = Regex("(?is)<article\\s+class=[\"']card[\"']>(.*?)</article>").findAll(html)
        for (match in cards) {
            val card = match.groupValues[1]
            val titleRaw = Regex("(?is)<h2>(.*?)</h2>").find(card)?.groupValues?.get(1) ?: continue
            val mediaMatch = Regex("(?is)<(audio|video)[^>]*src=[\"']([^\"']+)[\"']").find(card)
            val linkMatch = Regex("(?is)<a[^>]*href=[\"']([^\"']+)[\"']").find(card)
            val sourceRaw = mediaMatch?.groupValues?.get(2) ?: linkMatch?.groupValues?.get(1) ?: continue
            val source = Html.fromHtml(sourceRaw.replace("&amp;", "&"), Html.FROM_HTML_MODE_LEGACY).toString()
            val title = Html.fromHtml(titleRaw, Html.FROM_HTML_MODE_LEGACY).toString().trim()
            val path = runCatching { android.net.Uri.parse(source).path.orEmpty() }.getOrDefault("")
            val ext = path.substringAfterLast('.', "").lowercase(Locale.ROOT)
            val mime = when (ext) {
                "pdf" -> "application/pdf"
                "doc", "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                "mp3" -> "audio/mpeg"
                "wav" -> "audio/wav"
                "ogg" -> "audio/ogg"
                "m4a", "aac" -> "audio/mp4"
                "mp4", "mov" -> "video/mp4"
                "webm" -> "video/webm"
                else -> "application/octet-stream"
            }
            val type = when (mediaMatch?.groupValues?.get(1)?.lowercase(Locale.ROOT)) {
                "audio" -> "audio"
                "video" -> "video"
                else -> "document"
            }
            val stableId = path.hashCode().toString().replace("-", "")
            items.put(JSONObject()
                .put("id", stableId)
                .put("title", title)
                .put("description", "")
                .put("mime_type", mime)
                .put("media_type", type)
                .put("created_at", "")
                .put("download_url", source))
        }
        return JSONObject().put("items", items).put("count", items.length()).toString()
    }

    fun offlineMediaDirectory(context: Context): File = File(context.filesDir, "offline_media")

    fun scheduleImmediateUpdate(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<OfflineRefreshWorker>()
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context.applicationContext).enqueueUniqueWork(
            "mcn-delta-south-offline-refresh-now",
            ExistingWorkPolicy.KEEP,
            request
        )
    }

    fun scheduleAutomaticUpdates(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = PeriodicWorkRequestBuilder<OfflineRefreshWorker>(6, TimeUnit.HOURS)
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context.applicationContext).enqueueUniquePeriodicWork(
            "mcn-delta-south-offline-refresh",
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }
}

class OfflineRefreshWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return try {
            OfflineAttendanceQueue.syncPending(applicationContext)
            val result = OfflineModuleManager.downloadAll(applicationContext)
            if (result.failed == 0) Result.success() else Result.retry()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
