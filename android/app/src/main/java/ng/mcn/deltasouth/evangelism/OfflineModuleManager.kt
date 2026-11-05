package ng.mcn.deltasouth.evangelism

import android.content.Context
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
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.util.concurrent.TimeUnit

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

    fun downloadAll(context: Context): OfflineDownloadSummary {
        Backend.initialize(context.applicationContext)
        var downloaded = 0
        var unavailable = 0
        var failed = 0
        var mediaDownloaded = 0
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
        }
        try {
            mediaDownloaded = downloadPublishedMedia(context)
        } catch (_: Exception) {
            failed++
        }
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

    private fun downloadPublishedMedia(context: Context): Int {
        val catalogueRequest = Request.Builder()
            .url(BuildConfig.API_BASE_URL + "api/offline/media-catalogue")
            .get()
            .build()
        val longClient = Backend.client.newBuilder()
            .readTimeout(180, TimeUnit.SECONDS)
            .callTimeout(5, TimeUnit.MINUTES)
            .build()
        val json = longClient.newCall(catalogueRequest).execute().use { response ->
            if (!response.isSuccessful) throw IllegalStateException("Media catalogue HTTP " + response.code)
            response.body?.string() ?: throw IllegalStateException("Empty media catalogue")
        }
        val items = org.json.JSONObject(json).optJSONArray("items") ?: JSONArray()
        val directory = File(context.filesDir, "offline_media")
        if (!directory.exists()) directory.mkdirs()
        val oldIndex = runCatching { JSONArray(File(directory, "index.json").readText()) }.getOrDefault(JSONArray())
        val oldVersions = mutableMapOf<String, String>()
        for (i in 0 until oldIndex.length()) {
            val old = oldIndex.optJSONObject(i) ?: continue
            oldVersions[old.optString("id")] = old.optString("created_at")
        }
        var count = 0
        val index = JSONArray()
        for (i in 0 until items.length()) {
            val item = items.optJSONObject(i) ?: continue
            val id = item.optString("id")
            val url = item.optString("download_url")
            if (id.isBlank() || url.isBlank()) continue
            val mime = item.optString("mime_type", "application/octet-stream")
            val extension = when {
                mime.contains("pdf", true) -> ".pdf"
                mime.contains("audio", true) -> ".audio"
                mime.contains("video", true) -> ".video"
                mime.contains("word", true) -> ".doc"
                else -> ".bin"
            }
            val safeId = id.replace(Regex("[^A-Za-z0-9_-]"), "_")
            val target = File(directory, safeId + extension)
            val currentVersion = item.optString("created_at")
            if (!target.exists() || target.length() == 0L || oldVersions[id] != currentVersion) {
                val mediaRequest = Request.Builder().url(url).get().build()
                longClient.newCall(mediaRequest).execute().use { response ->
                    if (!response.isSuccessful) throw IllegalStateException("Media download HTTP " + response.code)
                    val body = response.body ?: throw IllegalStateException("Empty media file")
                    val temporary = File(directory, safeId + extension + ".part")
                    body.byteStream().use { input ->
                        temporary.outputStream().use { output -> input.copyTo(output) }
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
            index.put(org.json.JSONObject()
                .put("id", id)
                .put("title", item.optString("title"))
                .put("description", item.optString("description"))
                .put("mime_type", mime)
                .put("media_type", item.optString("media_type"))
                .put("file", target.name)
                .put("created_at", item.optString("created_at")))
            count++
        }
        File(directory, "index.json").writeText(index.toString())
        return count
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
