package ng.mcn.deltasouth.evangelism
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.net.Uri
import android.webkit.WebResourceResponse
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale

object OfflineDevotionalPage {
    private data class C(val slug:String,val key:String,val title:String,val icon:String)
    private val cs=listOf(C("english-hymns","english_hymns","English Methodist Hymns","𝄞"),C("yoruba-hymns","yoruba_hymns","Yoruba Methodist Hymns","📖"),C("akokun","akokun","Akokun Hymns","♫"),C("bible-verses","bible_verses","Bible Verses","✝"),C("canticles","canticles","Canticles","🙏"),C("communion","communion_english","English Communion","🍞"),C("yoruba-communion","communion_yoruba","Yoruba Communion","🕊️"),C("creeds","creeds","Creeds & Confessions","📜"))
    private fun d(c:Context)=File(c.filesDir,"offline_storage")
    private fun a(c:Context,k:String)=runCatching{JSONArray(File(File(d(c),k),"resources.json").readText())}.getOrElse{runCatching{JSONArray(File(c.filesDir,"offline_devotional/$k.json").readText())}.getOrDefault(JSONArray())}
    private fun e(s:String)=s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\"","&quot;").replace("'","&#39;")
    private fun sortedRows(rows:JSONArray):List<JSONObject> {
        val out=mutableListOf<JSONObject>()
        for(i in 0 until rows.length()) rows.optJSONObject(i)?.let{out.add(it)}
        fun number(r:JSONObject):Long {
            val raw=r.optString("item_number").ifBlank{r.optString("title")}
            return Regex("\\d+").find(raw)?.value?.toLongOrNull() ?: Long.MAX_VALUE
        }
        return out.sortedWith(compareBy<JSONObject>{number(it)}.thenBy{it.optString("title").lowercase(Locale.ROOT)})
    }
    private fun page(t:String,b:String)= """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${e(t)}</title><style>*{box-sizing:border-box}body{margin:0;background:#f2f5f9;color:#172b4d;font:16px/1.55 system-ui}header{background:linear-gradient(125deg,#071b48,#153c78 62%,#0d684c);color:white;padding:26px 18px}header small{color:#f4d36e;font-weight:800}h1{font:800 30px Georgia;margin:8px 0}main{max-width:1000px;margin:auto;padding:16px 13px 45px}nav{display:flex;gap:16px;margin-bottom:18px;flex-wrap:wrap}a{color:#12664b;text-decoration:none;font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.card,.item,.paper{background:white;border:1px solid #dfe6ee;border-radius:15px;padding:15px;margin-bottom:12px}.icon{font-size:32px}.card h2,.item h2{font-size:18px;margin:7px 0}.muted{color:#69768b}.pill{display:inline-block;background:#edf4f0;color:#176247;border-radius:24px;padding:6px 11px;font-weight:800;font-size:12px;margin-top:8px}.btn,button{display:inline-block;background:#123363;color:white;padding:10px 14px;border:0;border-radius:9px;font-weight:800}input{font:inherit;padding:11px;border:1px solid #cbd5e1;border-radius:8px;width:70%}.paper{font:17px/1.8 Georgia;white-space:pre-wrap}audio,video{width:100%;margin-top:10px}@media(max-width:520px){.card{padding:12px}.card h2{font-size:16px}}</style></head><body><header><small>METHODIST CHURCH NIGERIA · DELTA SOUTH DIOCESE · OFFLINE</small><h1>${e(t)}</h1><div>Downloaded resources saved on this phone. No internet required.</div></header><main><nav><a href="mcn-app://home">← Offline home</a><a href="/devotional-centre">All library cards</a><a href="mcn-app://live-home">Open live website (internet)</a></nav>$b</main></body></html>"""
    fun render(c:Context,path:String,q:String="",translation:String=""):String {
        val p=if(path=="/") "/" else path.trimEnd('/').ifBlank{"/devotional-centre"}
        if(p=="/media-library")return media(c)
        if(p=="/devotional-centre/communion-document/english")return communionDocument(c,"communion_english","English Communion")
        if(p=="/devotional-centre/communion-document/yoruba")return communionDocument(c,"communion_yoruba","Yoruba Communion")
        if(p=="/devotional-centre/holy-bible")return bible(c)
        if(p.startsWith("/devotional-centre/offline-bible"))return bibleReader(c,translation)
        if(p.startsWith("/devotional-centre/collection/"))return collection(c,Uri.decode(p.substringAfterLast('/')),q)
        if(p.startsWith("/devotional-centre/item/"))return item(c,Uri.decode(p.substringAfterLast('/')))
        if(p=="/devotional-centre/lectionary")return lectionary(c)
        return home(c)
    }
    private fun lectionary(c:Context):String {
        val file = File(File(d(c), "Lectionary"), "lectionary_2027.txt")
        if (!file.isFile || file.length() == 0L) {
            return page("Yearly Lectionary", "<article class='paper'>The lectionary has not yet been downloaded to this phone. Connect once and use Save Offline to include it.</article>")
        }
        val content = e(file.readText())
        val body = """<div class='item'><strong>YEAR B · 2027 / YEAR C · 2028</strong><p class='muted'>Diocesan appointed readings · Saved on this phone · No internet required</p><input id='lectionarySearch' type='search' placeholder='Search date, Sunday, feast or Bible reference' style='width:100%;margin:8px 0'><p id='lectionaryCount' class='muted'>All appointed readings shown</p></div><article id='lectionaryText' class='paper' style='font:16px/1.65 Georgia,serif;white-space:pre-wrap'>$content</article><script>(function(){const q=document.getElementById('lectionarySearch'),box=document.getElementById('lectionaryText'),count=document.getElementById('lectionaryCount'),original=box.textContent;function run(){const term=q.value.trim().toLocaleLowerCase();if(!term){box.textContent=original;count.textContent='All appointed readings shown';return;}const sections=original.split(/\\n\\s*\\n/).filter(x=>x.toLocaleLowerCase().includes(term));box.textContent=sections.join('\\n\\n');count.textContent=sections.length+' matching reading sections';}q.addEventListener('input',run);})();</script>"""
        return page("Yearly Lectionary", body)
    }
    private fun home(c:Context):String {
        val b = """
        <style>
          body{background:#f1f4f9;color:#10234d}
          .brand{display:flex;align-items:center;gap:14px;margin-bottom:20px}
          .brand-mark{font-size:54px;background:white;color:#0b4a35;border-radius:50%;width:76px;height:76px;display:grid;place-items:center}
          .brand strong{display:block;font:800 21px Georgia;color:#0b234e}
          .brand b{display:block;font:800 20px Georgia;color:#a91e37}
          .brand small{display:block;color:#667085;font-size:11px;letter-spacing:1px;margin-top:7px}
          .menu{background:#091f55;color:white;padding:16px;border-radius:12px;margin:12px 0 18px}
          .menu a{color:white;margin-right:13px;display:inline-block;padding:5px 0}
          .hero{background:linear-gradient(120deg,#081b4a,#242443 70%,#70503f);color:white;border-radius:16px;padding:26px 20px;margin-bottom:18px}
          .eyebrow{color:#f6cf45;font-weight:900;letter-spacing:2px}
          .hero h1{font:800 34px/1.12 Georgia;color:white;margin:14px 0}
          .hero p{font:19px/1.55 Georgia;color:white}
          .action{display:inline-block;background:#e31837;color:white;padding:12px 14px;border-radius:9px;margin:5px 6px 5px 0;font-weight:800}
          .section{background:white;border:1px solid #dce3ec;border-radius:15px;padding:18px;margin:14px 0}
          .section h2{color:#0d315e}
          .note{font-size:13px;color:#69768b}
        </style>
        <div class="brand"><div class="brand-mark">✝</div><div><strong>METHODIST CHURCH NIGERIA</strong><b>DELTA SOUTH DIOCESE</b><small>WORSHIP · WITNESS · SERVICE · DISCIPLESHIP</small></div></div>
        <nav class="menu"><strong style="font-size:20px">☰ Menu</strong><div style="margin-top:8px"><a href="#home">Home</a><a href="#about">About Us</a><a href="#diocese">Our Diocese</a><a href="#churches">Find Churches</a><a href="#devotional">Devotional Centre</a><a href="#contact">Contact</a></div></nav>
        <section class="hero" id="home"><div class="eyebrow">WELCOME TO</div><h1>METHODIST CHURCH NIGERIA<br><span style="color:#f6cf45">DELTA SOUTH DIOCESE</span></h1><p>“Go into all the world and preach the Gospel to every creature.” — Mark 16:15</p><a class="action" href="#watch">▶ Watch Live Service</a><a class="action" href="#giving">♥ Give Online</a><a class="action" href="#churches" style="background:transparent;border:2px solid white">⌖ Find a Church Near You</a></section>
        <section class="section" id="watch"><h2>Worship with Us</h2><p>Methodist Church Nigeria · Delta South Diocese</p><p class="note">Live streaming requires internet. Your homepage and saved resources remain available offline.</p></section>
        <section class="section" id="about"><h2>About Our Diocese</h2><p>Worship · Witness · Service · Discipleship. Serving communities across Delta South Diocese through the Gospel of Jesus Christ.</p></section>
        <section class="section" id="diocese"><h2>Our Diocese</h2><p>Delta South Diocese — Methodist Church Nigeria.</p></section>
        <section class="section" id="churches"><h2>Find a Methodist Church Near You</h2><p>Effurun Circuit · Warri Circuit · Sapele Circuit · Steel Town Circuit</p><p class="note">The online directory and live map can be refreshed when you deliberately update the app.</p></section>
        <section class="section" id="giving"><h2>Give Online</h2><p>Online giving requires an internet connection.</p></section>
        <section class="section" id="devotional"><h2>Devotional & Worship Centre</h2><p>Access downloaded hymns, Bible modules, communion materials, canticles and yearly lectionary on this phone.</p><a class="btn" href="/devotional-centre">Open Offline Devotional Centre →</a></section>
        <section class="section" id="contact"><h2>Connect With the Diocese</h2><p>Methodist Church Nigeria · Delta South Diocese</p></section>
        <p class="note">OFFLINE MODE · This homepage is stored on this phone. Tap Refresh / Update only when you choose to download the latest version.</p>
        """.trimIndent()
        return page("Methodist Church Nigeria · Delta South Diocese", b)
    }
    private fun communionDocument(c:Context,key:String,title:String):String {
        val rows=a(c,key)
        val b=StringBuilder("<article class='paper' style='font:18px/1.85 Georgia,serif;white-space:normal'><h2 style='text-align:center'>${e(title)}</h2>")
        if(rows.length()==0)b.append("<p>This Communion document has not been saved on this phone yet. Download it from this card while connected.</p>")
        val ordered=sortedRows(rows)
        for(i in ordered.indices){
            val r=ordered[i]
            val p=r.optJSONObject("payload")?:JSONObject()
            val heading=r.optString("title").ifBlank{r.optString("item_number")}
            if(heading.isNotBlank())b.append("<h3>${e(heading)}</h3>")
            val st=p.optJSONArray("stanzas")
            if(st!=null){for(j in 0 until st.length()){val line=st.optString(j);if(line.isNotBlank())b.append("<p>${e(line)}</p>")}}
            val sections=p.optJSONArray("sections")
            if(sections!=null){for(j in 0 until sections.length()){val sec=sections.optJSONObject(j);if(sec!=null){val h=sec.optString("title");if(h.isNotBlank())b.append("<h3>${e(h)}</h3>");val tx=sec.optString("content",sec.optString("text"));if(tx.isNotBlank())b.append("<p>${e(tx)}</p>")}else{val tx=sections.optString(j);if(tx.isNotBlank())b.append("<p>${e(tx)}</p>")}}}
            val body=listOf("content","text","body","description").firstNotNullOfOrNull{field->p.optString(field).takeIf{it.isNotBlank()}}
            if(body!=null)b.append("<p>${e(body)}</p>")
            if(p.has("chorus"))b.append("<p><strong>Chorus:</strong> ${e(p.optString("chorus"))}</p>")
            if(i<rows.length()-1)b.append("<hr style='border:0;border-top:1px solid #d9dee7;margin:22px 0'>")
        }
        b.append("</article>")
        return page(title,b.toString())
    }
    private fun collection(c:Context,slug:String,q:String):String {
        val x=cs.firstOrNull{it.slug==slug||it.key==slug}?:return home(c);val rows=a(c,x.key);val b=StringBuilder("""<form method="get" action="/devotional-centre/collection/${Uri.encode(x.slug)}"><input name="q" placeholder="Search this collection" value="${e(q)}"><button type="submit">Search</button></form><p class="muted">${rows.length()} resources saved in this library</p>""")
        var count=0
        for(r in sortedRows(rows)){val p=r.optJSONObject("payload")?:JSONObject();val title=r.optString("title","Resource");val num=r.optString("item_number");val first=p.optString("firstline",p.optString("reference",p.optString("heading",p.optString("content",""))));if(q.isNotBlank()&&!("$title $num $first".contains(q,true)))continue
            val id=r.optString("resource_id","${x.key}:$num");val localHref="/devotional-centre/item/${Uri.encode(id)}";b.append("""<article class="item"><div class="muted">${e(x.title)} · ${e(num)}</div><h2>${e(title)}</h2><p class="muted">${e(first.take(200))}</p><a class="btn" href="$localHref">Open Saved Resource →</a></article>""");count++}
        if(count==0)b.append("<div class='paper'>No matching downloaded resources in this library card.</div>")
        return page(x.title,b.toString())
    }
    private fun item(c:Context,id:String):String {
        for(x in cs){val rows=a(c,x.key);for(i in 0 until rows.length()){val r=rows.optJSONObject(i)?:continue;val num=r.optString("item_number");if(r.optString("resource_id")!=id&&"${x.key}:$num"!=id&&"${x.slug}:$num"!=id)continue
            val p=r.optJSONObject("payload")?:JSONObject();val b=StringBuilder("<article class='paper'>")
            if(p.has("reference"))b.append("<h2>${e(p.optString("reference"))}</h2>${e(p.optString("verse"))}") else if(p.has("stanzas")){val st=p.optJSONArray("stanzas")?:JSONArray();for(j in 0 until st.length())b.append("<p>${e(st.optString(j))}</p>");if(p.has("chorus"))b.append("<h3>Chorus</h3><p>${e(p.optString("chorus"))}</p>")}else b.append(e(p.optString("content",p.optString("text",p.optString("body",p.optString("description",p.toString(2)))))))
            b.append("</article>")
            b.append("""<nav style="margin:16px 0"><a class="btn" href="/devotional-centre/collection/${Uri.encode(x.slug)}">⌂ Hymn Home / Search</a></nav>""")
            val audio=r.optString("audio_file");if(audio.isNotBlank())b.append("""<div class="item"><strong>Hymn tune</strong><audio controls src="/__mcn_offline/file/${Uri.encode(audio)}"></audio></div>""")
            val tunes=p.optJSONArray("otherTunes");if(tunes!=null)for(j in 0 until tunes.length()){val t=tunes.optJSONObject(j)?:continue;val f=t.optString("offline_file");if(f.isNotBlank())b.append("""<div class="item"><strong>${e(t.optString("title","Additional tune"))}</strong><audio controls src="/__mcn_offline/file/${Uri.encode(f)}"></audio></div>""")}
            return page(r.optString("title","Worship resource"),b.toString())}}
        return page("Resource unavailable offline","<div class='paper'>This resource is not in the downloaded collection. Re-download this collection from its original card while connected.</div>")
    }
    private fun bible(c:Context):String {val a=runCatching{JSONArray(File(d(c),"Bible/index.json").readText())}.getOrDefault(JSONArray());val b=StringBuilder("<div class='grid'>");for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;val id=x.optString("id");if(id.isBlank()||id.equals("web",true))continue;b.append("""<article class="card"><div class="icon">📖</div><h2>${e(x.optString("title",id.uppercase(Locale.ROOT)))}</h2><span class="pill">Downloaded Bible module</span><p class="muted">Bible database saved locally on this phone.</p><a class="btn" href="/devotional-centre/offline-bible?translation=${Uri.encode(id)}">Open Bible →</a></article>""")};b.append("</div>");if(a.length()==0)b.append("<div class='paper'>No uploaded Bible modules saved yet.</div>");return page("Uploaded Bible Library",b.toString())}
    private fun bibleReader(c:Context,translation:String):String {
        val safe=translation.lowercase(Locale.ROOT).filter{it.isLetterOrDigit()||it=='_'||it=='-'}
        if(safe.isBlank()||safe=="web")return bible(c)
        val html="""<div class="item"><p class="muted">Uploaded Bible module: ${e(safe.uppercase(Locale.ROOT))}</p>
<select id="book" style="width:100%;padding:12px;margin:8px 0"></select>
<div style="display:flex;gap:8px"><input id="chapter" type="number" min="1" value="1" style="width:35%"><button onclick="loadChapter()">Read Chapter</button></div>
<div id="status" class="muted">Loading books from the downloaded Bible…</div><article id="verses" class="paper"></article></div>
<script>
const translation="$safe";
const names=["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"];
const book=document.getElementById("book"),status=document.getElementById("status"),verses=document.getElementById("verses");
async function loadChapter(){const b=book.value,c=document.getElementById("chapter").value;status.textContent="Opening chapter…";try{const r=await fetch("/__mcn_offline/bible?kind=chapter&translation="+encodeURIComponent(translation)+"&book="+b+"&chapter="+c);if(!r.ok)throw new Error("Chapter not available in local Bible");const data=await r.json();verses.textContent="";data.verses.forEach(v=>{const p=document.createElement("p");p.textContent=v.verse+". "+v.text;verses.appendChild(p)});status.textContent=(names[Number(b)-1]||("Book "+b))+" "+c+" · "+data.verses.length+" verses"}catch(e){status.textContent=e.message}}
fetch("/__mcn_offline/bible?kind=books&translation="+encodeURIComponent(translation)).then(r=>{if(!r.ok)throw new Error("Books unavailable offline");return r.json()}).then(data=>{data.books.forEach(x=>{const o=document.createElement("option");o.value=x.id;o.textContent=(names[Number(x.id)-1]||("Book "+x.id))+" ("+x.chapters+" chapters)";book.appendChild(o)});status.textContent="Bible loaded from this phone. Choose a book and chapter.";loadChapter()}).catch(e=>status.textContent=e.message);
</script>"""
        return page("Offline Bible Reader",html)
    }
    private fun media(c:Context):String {val a=runCatching{JSONArray(File(d(c),"Church_Media/index.json").readText())}.getOrDefault(JSONArray());val b=StringBuilder();for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;val f=x.optString("file");val url="/__mcn_offline/file/${Uri.encode(f)}";b.append("""<article class="item"><h2>${e(x.optString("title","Media"))}</h2><p class="muted">${e(x.optString("description"))}</p>""");when(x.optString("media_type")){"audio"->b.append("""<audio controls src="$url"></audio>""");"video"->b.append("""<video controls playsinline src="$url"></video>""");else->if(x.optString("mime_type").startsWith("image/"))b.append("""<img src="$url" style="max-width:100%">""")else b.append("""<a class="btn" href="$url" download>Open downloaded file</a>""")};b.append("</article>")};if(a.length()==0)b.append("<div class='paper'>No media files saved on this phone yet.</div>");return page("Church Media Library",b.toString())}
    private fun bibleJsonResponse(c:Context,u:Uri):WebResourceResponse?=runCatching {
        if(u.path!="/__mcn_offline/bible")return null
        val code=u.getQueryParameter("translation")?.lowercase(Locale.ROOT).orEmpty()
        val index=JSONArray(File(d(c),"Bible/index.json").readText())
        val module=(0 until index.length()).mapNotNull{index.optJSONObject(it)}.firstOrNull{it.optString("id").equals(code,true)} ?: return null
        val dbFile=File(File(d(c),"Bible"),module.optString("file")).takeIf{it.isFile&&it.length()>1024L} ?: return null
        val db=SQLiteDatabase.openDatabase(dbFile.absolutePath,null,SQLiteDatabase.OPEN_READONLY)
        val json=try {
            if(u.getQueryParameter("kind")=="books") {
                val books=JSONArray()
                db.rawQuery("SELECT Book, MAX(Chapter) FROM Bible GROUP BY Book ORDER BY Book",null).use{cur->while(cur.moveToNext())books.put(JSONObject().put("id",cur.getInt(0)).put("chapters",cur.getInt(1)))}
                JSONObject().put("translation",code).put("books",books).toString()
            } else {
                val book=u.getQueryParameter("book")?.toIntOrNull()?:return null
                val chapter=u.getQueryParameter("chapter")?.toIntOrNull()?:return null
                val verses=JSONArray()
                db.rawQuery("SELECT Verse, Scripture FROM Bible WHERE Book=? AND Chapter=? ORDER BY Verse",arrayOf(book.toString(),chapter.toString())).use{cur->while(cur.moveToNext()){
                    val body=cur.getString(1).orEmpty().replace(Regex("<RF>.*?<Rf>",RegexOption.IGNORE_CASE),"").replace(Regex("<[^>]*>"),"").replace(Regex("\\s+")," ").trim()
                    verses.put(JSONObject().put("verse",cur.getInt(0)).put("text",body))
                }}
                JSONObject().put("translation",code).put("book",book).put("chapter",chapter).put("verses",verses).toString()
            }
        } finally { db.close() }
        WebResourceResponse("application/json","UTF-8",200,"OK",mapOf("Access-Control-Allow-Origin" to "*"),json.byteInputStream())
    }.getOrNull()
    fun audioUrlResponse(c:Context,url:String):WebResourceResponse?=runCatching {
        val uri = Uri.parse(url)
        val indexFile = File(File(d(c), "audio_url_map"), "index.json")
        if (!indexFile.isFile) return null
        val map = JSONObject(indexFile.readText())
        val filename = map.optString(uri.encodedPath.orEmpty())
        if (filename.isBlank() || filename.contains("/") || filename.contains("..")) return null
        val roots = d(c).listFiles()?.filter { it.isDirectory } ?: emptyList()
        val file = roots.asSequence().map { File(it, filename) }.firstOrNull { it.isFile && it.length() > 0L } ?: return null
        val mime = when (file.extension.lowercase(Locale.ROOT)) {
            "mp3" -> "audio/mpeg"; "m4a" -> "audio/mp4"; "wav" -> "audio/wav"; "ogg" -> "audio/ogg"
            else -> "application/octet-stream"
        }
        WebResourceResponse(mime, null, 200, "OK", mapOf("Access-Control-Allow-Origin" to "*", "Accept-Ranges" to "bytes"), file.inputStream())
    }.getOrNull()

    fun fileResponse(c:Context,url:String):WebResourceResponse?=runCatching{
        val u=Uri.parse(url)
        bibleJsonResponse(c,u)?.let{return it}
        if(!u.path.orEmpty().startsWith("/__mcn_offline/file/"))return null
        val name=Uri.decode(u.path!!.substringAfterLast('/'))
        if(name.isBlank()||name.contains("/")||name.contains(".."))return null
        val f=(sequenceOf(d(c),File(d(c),"Church_Media"),File(d(c),"Bible")) + (d(c).listFiles()?.filter{it.isDirectory}?.asSequence()?:emptySequence())).map{File(it,name)}.firstOrNull{it.isFile&&it.length()>0} ?: File(c.filesDir,"offline_devotional/$name").takeIf{it.isFile&&it.length()>0} ?: return null
        val mime=when(f.extension.lowercase(Locale.ROOT)){"mp3"->"audio/mpeg";"m4a"->"audio/mp4";"wav"->"audio/wav";"ogg"->"audio/ogg";"mp4"->"video/mp4";"webm"->"video/webm";"jpg","jpeg"->"image/jpeg";"png"->"image/png";"gif"->"image/gif";"webp"->"image/webp";"pdf"->"application/pdf";else->"application/octet-stream"}
        WebResourceResponse(mime,null,f.inputStream())
    }.getOrNull()
}
