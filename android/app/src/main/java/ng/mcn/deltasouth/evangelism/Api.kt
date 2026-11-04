package ng.mcn.deltasouth.evangelism
import android.content.Context
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Body
import retrofit2.http.DELETE
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap

class SessionCookieJar : CookieJar {
 private val store = ConcurrentHashMap<String, Cookie>()
 @Volatile private var preferences: android.content.SharedPreferences? = null
 fun initialize(context: Context) {
  if (preferences != null) return
  synchronized(this) {
   if (preferences != null) return
   val masterKey = MasterKey.Builder(context.applicationContext).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
   val prefs = EncryptedSharedPreferences.create(context.applicationContext, "delta_south_secure_session", masterKey, EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV, EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM)
   preferences = prefs
   val saved = prefs.getString("cookies", "[]") ?: "[]"
   val array = JSONArray(saved)
   for (i in 0 until array.length()) {
    val item = array.optJSONObject(i) ?: continue
    runCatching {
     val builder = Cookie.Builder().name(item.getString("name")).value(item.getString("value")).path(item.optString("path", "/"))
     val domain = item.getString("domain")
     if (item.optBoolean("hostOnly", false)) builder.hostOnlyDomain(domain) else builder.domain(domain)
     if (item.optBoolean("secure")) builder.secure()
     if (item.optBoolean("httpOnly")) builder.httpOnly()
     if (item.optBoolean("persistent")) builder.expiresAt(item.getLong("expiresAt"))
     val cookie = builder.build()
     if (!(cookie.expiresAt <= System.currentTimeMillis())) store[cookie.name + "|" + cookie.domain + "|" + cookie.path] = cookie
    }
   }
  }
 }
 override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
  cookies.forEach { cookie ->
   val key = cookie.name + "|" + cookie.domain + "|" + cookie.path
   if ((cookie.expiresAt <= System.currentTimeMillis())) store.remove(key) else store[key] = cookie
  }
  persist()
 }
 override fun loadForRequest(url: HttpUrl): List<Cookie> {
  val valid = store.values.filter { it.matches(url) && it.expiresAt > System.currentTimeMillis() }
  if (valid.size != store.size) { store.entries.removeIf { (it.value.expiresAt <= System.currentTimeMillis()) }; persist() }
  return valid
 }
 private fun persist() {
  val prefs = preferences ?: return
  val array = JSONArray()
  store.values.filter { it.expiresAt > System.currentTimeMillis() }.forEach { cookie ->
   array.put(JSONObject().put("name", cookie.name).put("value", cookie.value).put("domain", cookie.domain).put("path", cookie.path).put("hostOnly", cookie.hostOnly).put("secure", cookie.secure).put("httpOnly", cookie.httpOnly).put("persistent", cookie.persistent).put("expiresAt", cookie.expiresAt))
  }
  prefs.edit().putString("cookies", array.toString()).apply()
 }
 fun clear() { store.clear(); preferences?.edit()?.remove("cookies")?.apply() }
}
object Backend {
 val cookies = SessionCookieJar()
 fun initialize(context: Context) = cookies.initialize(context)
 val client = OkHttpClient.Builder().cookieJar(cookies).build()
 val api = Retrofit.Builder().baseUrl(BuildConfig.API_BASE_URL).client(client).addConverterFactory(GsonConverterFactory.create()).build().create(DioceseApi::class.java)
 fun login(username: String, password: String): Result<Unit> = runCatching {
  val body = FormBody.Builder().add("username", username).add("password", password).build()
  val req = Request.Builder().url(BuildConfig.API_BASE_URL + "login").post(body).build()
  client.newCall(req).execute().use { response ->
   if (!response.isSuccessful && response.code !in 300..399) error("Sign in failed: HTTP ${response.code}")
   if (cookies.loadForRequest(req.url).isEmpty()) error("No session cookie received. Check your login details.")
  }
 }
}
interface DioceseApi {
 @GET("api/me") suspend fun me(): Map<String, Any?>
 @GET("api/dashboard") suspend fun dashboard(): Map<String, Any?>
 @GET("api/member/records") suspend fun memberRecords(): Map<String, Any?>
 @PUT("api/member/profile") suspend fun updateMemberProfile(@Body body: Map<String, String>): Map<String, Any?>
 @POST("api/member/change-password") suspend fun changeMemberPassword(@Body body: Map<String, String>): Map<String, Any?>
 @GET("api/member/id-card") suspend fun memberIdCard(): Map<String, Any?>
 @GET("api/member/attendance-summary") suspend fun attendanceSummary(): Map<String, Any?>
 @GET("api/member/attendance") suspend fun memberAttendance(): List<Map<String, Any?>>
 @POST("api/member-attendance") suspend fun recordMemberAttendance(@Body body: Map<String, String>): Map<String, Any?>
 @GET("api/member/giving-history") suspend fun givingHistory(): List<Map<String, Any?>>
 @GET("api/member/announcements") suspend fun announcements(): List<Map<String, Any?>>
 @GET("api/member/events") suspend fun events(): List<Map<String, Any?>>
 @GET("api/member/notifications") suspend fun notifications(): List<Map<String, Any?>>
 @POST("api/member/notifications/{id}/read") suspend fun markNotificationRead(@Path("id") id: Int): Map<String, Any?>
 @GET("api/church-accounts") suspend fun churchAccounts(): List<Map<String, Any?>>
 @POST("api/church-accounts") suspend fun createChurchAccount(@Body body: Map<String, String>): Map<String, Any?>
 @GET("api/conference") suspend fun conferences(): List<Map<String, Any?>>
 @POST("api/conference") suspend fun createConference(@Body body: Map<String, String>): Map<String, Any?>
 @GET("api/conference/{id}") suspend fun conferenceDetail(@Path("id") id: Int): Map<String, Any?>
 @POST("api/conference/{id}/message") suspend fun sendConferenceMessage(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @POST("api/conference/{id}/participant") suspend fun addConferenceParticipant(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @GET("api/conference/{id}/presence") suspend fun conferencePresence(@Path("id") id: Int): List<Map<String, Any?>>
 @POST("api/conference/{id}/presence") suspend fun updateConferencePresence(@Path("id") id: Int, @Body body: Map<String, Any?>): Map<String, Any?>
 @DELETE("api/conference/{id}/presence") suspend fun leaveConferencePresence(@Path("id") id: Int, @Query("participant_id") participantId: String): Map<String, Any?>
 @GET("api/finance-summary") suspend fun financeSummary(): Map<String, Any?>
 @GET("api/payment-history") suspend fun paymentHistory(): Map<String, Any?>
 @GET("api/payment-reconciliation") suspend fun paymentReconciliation(): Map<String, Any?>
 @POST("api/payment-reconciliation/{reference}/reconcile") suspend fun reconcilePayment(@Path("reference") reference: String): Map<String, Any?>
 @GET("api/membership/churches") suspend fun membershipChurches(): List<Map<String, Any?>>
 @GET("api/circuits") suspend fun circuits(): List<Map<String, Any?>>
 @GET("api/members") suspend fun members(): List<Map<String, Any?>>
 @GET("api/membership-statistics") suspend fun membershipStatistics(): Map<String, Any?>
 @GET("api/member-registrations") suspend fun memberRegistrations(): List<Map<String, Any?>>
 @POST("api/member-registrations/{id}/review") suspend fun reviewMemberRegistration(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @GET("api/members/{id}/appointments") suspend fun memberAppointments(@Path("id") id: Int): Map<String, Any?>
 @POST("api/members/{id}/appointments") suspend fun createMemberAppointment(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @PUT("api/member-appointments/{id}") suspend fun updateMemberAppointment(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @POST("api/member-appointments/{id}/terminate") suspend fun terminateMemberAppointment(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @GET("api/admin/reporting-summary") suspend fun reportingSummary(): Map<String, Any?>
 @GET("api/reports") suspend fun reports(@Query("year") year: Int, @Query("circuit") circuit: String = "All"): Map<String, Any?>
 @GET("api/security/status") suspend fun securityStatus(): Map<String, Any?>
 @GET("api/security/backups") suspend fun backupHistory(): List<Map<String, Any?>>
 @POST("api/security/backup") suspend fun createSecurityBackup(): Map<String, Any?>
 @GET("api/users") suspend fun adminUsers(): List<Map<String, Any?>>
 @GET("api/account-requests") suspend fun accountRequests(): List<Map<String, Any?>>
 @POST("api/account-requests/{id}/approve") suspend fun approveAccountRequest(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @POST("api/account-requests/{id}/reject") suspend fun rejectAccountRequest(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
 @POST("api/security/users/{id}/toggle") suspend fun toggleUser(@Path("id") id: Int): Map<String, Any?>
 @GET("api/system/health") suspend fun systemHealth(): Map<String, Any?>
 @GET("api/system/data-quality") suspend fun dataQuality(): Map<String, Any?>
 @GET("api/audit") suspend fun auditLog(): List<Map<String, Any?>>
 @GET("api/customer-care") suspend fun customerCareThreads(): List<Map<String, Any?>>
 @POST("api/customer-care") suspend fun createCustomerCareThread(@Body body: Map<String, String>): Map<String, Any?>
 @GET("api/customer-care/unread-count") suspend fun customerCareUnreadCount(): Map<String, Any?>
 @POST("api/customer-care/{id}/read") suspend fun markCustomerCareRead(@Path("id") id: Int): Map<String, Any?>
 @GET("api/customer-care/{id}") suspend fun customerCareDetail(@Path("id") id: Int): Map<String, Any?>
 @POST("api/customer-care/{id}/message") suspend fun sendCustomerCareMessage(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>

}
