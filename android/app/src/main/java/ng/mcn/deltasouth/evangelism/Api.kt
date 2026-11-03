package ng.mcn.deltasouth.evangelism
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
import retrofit2.http.Path
import retrofit2.http.Body
import java.util.concurrent.ConcurrentHashMap
class SessionCookieJar : CookieJar {
 private val store = ConcurrentHashMap<String, List<Cookie>>()
 override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) { store[url.host] = cookies }
 override fun loadForRequest(url: HttpUrl): List<Cookie> = store[url.host] ?: emptyList()
 fun clear() = store.clear()
}
object Backend {
 val cookies = SessionCookieJar()
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
 @GET("api/member/id-card") suspend fun memberIdCard(): Map<String, Any?>
 @GET("api/member/attendance-summary") suspend fun attendanceSummary(): Map<String, Any?>
 @GET("api/member/attendance") suspend fun memberAttendance(): List<Map<String, Any?>>
 @GET("api/member/giving-history") suspend fun givingHistory(): List<Map<String, Any?>>
 @GET("api/member/announcements") suspend fun announcements(): List<Map<String, Any?>>
 @GET("api/member/events") suspend fun events(): List<Map<String, Any?>>
 @GET("api/member/notifications") suspend fun notifications(): List<Map<String, Any?>>
 @GET("api/finance-summary") suspend fun financeSummary(): Map<String, Any?>
 @GET("api/payment-history") suspend fun paymentHistory(): Map<String, Any?>
 @GET("api/payment-reconciliation") suspend fun paymentReconciliation(): Map<String, Any?>
 @GET("api/membership/churches") suspend fun membershipChurches(): List<Map<String, Any?>>
 @GET("api/circuits") suspend fun circuits(): List<Map<String, Any?>>
 @GET("api/members") suspend fun members(): List<Map<String, Any?>>
 @GET("api/member-registrations") suspend fun memberRegistrations(): List<Map<String, Any?>>
 @POST("api/member-registrations/{id}/review") suspend fun reviewMemberRegistration(@Path("id") id: Int, @Body body: Map<String, String>): Map<String, Any?>
}
