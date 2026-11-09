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
    private fun page(t:String,b:String)= """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${e(t)}</title><style>*{box-sizing:border-box}body{margin:0;background:#f2f5f9;color:#172b4d;font:16px/1.55 system-ui}header{background:linear-gradient(125deg,#071b48,#153c78 62%,#0d684c);color:white;padding:26px 18px}header small{color:#f4d36e;font-weight:800}h1{font:800 30px Georgia;margin:8px 0}main{max-width:1000px;margin:auto;padding:16px 13px 45px}nav{display:flex;gap:16px;margin-bottom:18px;flex-wrap:wrap}a{color:#12664b;text-decoration:none;font-weight:700}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.card,.item,.paper{background:white;border:1px solid #dfe6ee;border-radius:15px;padding:15px;margin-bottom:12px}.icon{font-size:32px}.card h2,.item h2{font-size:18px;margin:7px 0}.muted{color:#69768b}.pill{display:inline-block;background:#edf4f0;color:#176247;border-radius:24px;padding:6px 11px;font-weight:800;font-size:12px;margin-top:8px}.btn,button{display:inline-block;background:#123363;color:white;padding:10px 14px;border:0;border-radius:9px;font-weight:800}input{font:inherit;padding:11px;border:1px solid #cbd5e1;border-radius:8px;width:70%}.paper{font:17px/1.8 Georgia;white-space:pre-wrap}audio,video{width:100%;margin-top:10px}@media(max-width:520px){.card{padding:12px}.card h2{font-size:16px}}</style></head><body><header><small>METHODIST CHURCH NIGERIA · DELTA SOUTH DIOCESE · OFFLINE</small><h1>${e(t)}</h1><div>Downloaded resources saved on this phone. No internet required.</div></header><main><nav><a href="mcn-app://home">← Main home</a><a href="/devotional-centre">All library cards</a></nav>$b</main></body></html>"""
    fun render(c:Context,path:String,q:String="",translation:String=""):String {
        val p=if(path=="/") "/" else path.trimEnd('/').ifBlank{"/devotional-centre"}
        if(p=="/")return homepage(c)
        if(p=="/fellowships")return fellowshipDirectory(c)
        if(p.startsWith("/fellowship/"))return fellowshipPage(c,p.substringAfterLast('/'))
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
    private fun homepage(c:Context):String {
        val english=sortedRows(a(c,"english_hymns"))
        val today=java.util.Calendar.getInstance(java.util.Locale("en","NG")).get(java.util.Calendar.DAY_OF_YEAR)
        val hymn=english.getOrNull(if(english.isEmpty()) 0 else (today-1)%english.size)
        val hymnPayload=hymn?.optJSONObject("payload")?:JSONObject()
        val hymnTitle=hymn?.optString("title").orEmpty().ifBlank{"Methodist Hymn for Today"}
        val hymnNumber=hymn?.optString("item_number").orEmpty()
        val lyrics=when {
            hymnPayload.has("stanzas") -> (0 until hymnPayload.optJSONArray("stanzas").length()).joinToString("\\n\\n"){hymnPayload.optJSONArray("stanzas").optString(it)}
            else -> hymnPayload.optString("content",hymnPayload.optString("text",hymnPayload.optString("body","Open the Methodist Hymn Library to read the saved hymns.")))
        }
        val audio=hymn?.optString("audio_file").orEmpty()
        val b=StringBuilder()
        b.append("""<section class="item"><div class="muted">✝ SCRIPTURE FOR TODAY · OFFLINE</div><h2>Read your downloaded Bible</h2><p>The Scripture reader uses the Bible module saved on this phone.</p><a class="btn" href="/devotional-centre/holy-bible">Open Saved Bible →</a></section>""")
        b.append("""<section class="item"><div class="muted">♫ METHODIST HYMN FOR TODAY · OFFLINE</div><h2>${e(hymnNumber)} ${e(hymnTitle)}</h2><div class="paper">${e(lyrics)}</div>""")
        if(audio.isNotBlank())b.append("""<p><strong>Hymn tune</strong><audio controls preload="none" playsinline src="/__mcn_offline/file/${Uri.encode(audio)}"></audio></p>""")
        val tunes=hymnPayload.optJSONArray("otherTunes")
        if(tunes!=null)for(i in 0 until tunes.length()){val tune=tunes.optJSONObject(i)?:continue;val file=tune.optString("offline_file");if(file.isNotBlank())b.append("""<p><strong>${e(tune.optString("musicTitle",tune.optString("tuneName","Alternative tune")))}</strong><audio controls preload="none" playsinline src="/__mcn_offline/file/${Uri.encode(file)}"></audio></p>""")}
        b.append("""<a class="btn" href="/devotional-centre/collection/english-hymns">All Saved Hymns →</a></section>""")
        b.append("""<h2>Explore the Diocese</h2><div class="grid">
<a class="card" href="/fellowships"><div class="icon">🤝</div><h2>Fellowships</h2><p class="muted">Open saved fellowship information</p></a>
<a class="card" href="/devotional-centre"><div class="icon">📖</div><h2>Devotional Centre</h2><p class="muted">Hymns, Scripture and worship books</p></a>
<a class="card" href="/media-library"><div class="icon">🎧</div><h2>Church Media</h2><p class="muted">Downloaded audio, video and documents</p></a>
<a class="card" href="/devotional-centre/lectionary"><div class="icon">📅</div><h2>Lectionary</h2><p class="muted">Saved appointed readings</p></a>
<a class="card" href="/login"><div class="icon">♙</div><h2>Member Login</h2><p class="muted">Internet required for secure sign-in</p></a>
<a class="card" href="/giving"><div class="icon">♥</div><h2>Online Giving</h2><p class="muted">Internet required for payment</p></a>
</div>""")
        return page("Methodist Church Nigeria · Delta South Diocese",b.toString())
    }
    private fun fellowshipDirectory(c:Context):String {
        val file=File(d(c),"fellowships.json")
        val rows=runCatching{JSONArray(file.readText())}.getOrDefault(JSONArray())
        val body=StringBuilder("<div class='grid'>")
        if(rows.length()>0) {
            for(i in 0 until rows.length()) {
                val row=rows.optJSONObject(i)?:continue
                val slug=row.optString("slug")
                val name=row.optString("name",row.optString("short_name","Fellowship"))
                if(slug.isBlank())continue
                body.append("""<a class="card" href="/fellowship/${Uri.encode(slug)}"><div class="icon">🤝</div><h2>${e(name)}</h2><p class="muted">${e(row.optString("short_name"))}</p><span class="pill">Saved on this phone</span></a>""")
            }
        } else {
            listOf("methodist-mens-fellowship" to "Methodist Men's Fellowship","methodist-womens-fellowship" to "Methodist Women's Fellowship","methodist-youth-fellowship" to "Methodist Youth Fellowship","methodist-campus-fellowship" to "Methodist Campus Fellowship").forEach{(slug,name)->body.append("""<a class="card" href="/fellowship/${slug}"><div class="icon">🤝</div><h2>${e(name)}</h2><span class="pill">Connect and update to save details</span></a>""")}
        }
        body.append("</div><p class='muted'>Fellowship information is read from the last offline update. No live connection is used to open this page.</p>")
        return page("Diocesan Fellowships",body.toString())
    }
    private fun fellowshipPage(c:Context,slug:String):String {
        val safe=slug.replace(Regex("[^A-Za-z0-9_-]"),"")
        val file=File(d(c),"fellowship_${safe}.json")
        val root=runCatching{JSONObject(file.readText())}.getOrNull()
            ?: return page("Fellowship not downloaded", "<article class='paper'><p>This fellowship profile is not saved on this phone yet. Connect and use Update Offline Content.</p><a class='btn' href='/fellowships'>← All Fellowships</a></article>")
        val f=root.optJSONObject("fellowship")?:JSONObject()
        val name=f.optString("name","Fellowship")
        val body=StringBuilder("<article class='paper'>")
        listOf("short_name" to "Name","introduction" to "Introduction","history" to "History","vision" to "Vision","mission" to "Mission","objectives" to "Objectives").forEach{(key,label)->
            val value=f.optString(key).trim()
            if(value.isNotBlank())body.append("<h3>${e(label)}</h3><p>${e(value)}</p>")
        }
        body.append("</article>")
        fun section(key:String,title:String,fields:List<String>) {
            val items=root.optJSONArray(key)?:return
            if(items.length()==0)return
            body.append("<h2>${e(title)}</h2>")
            for(i in 0 until items.length()) {
                val item=items.optJSONObject(i)?:continue
                body.append("<article class='item'>")
                fields.forEach{field->val value=item.optString(field).trim();if(value.isNotBlank())body.append("<p>${e(value)}</p>")}
                body.append("</article>")
            }
        }
        section("leaders","Fellowship Leadership",listOf("full_name","position_title","biography"))
        section("announcements","Announcements",listOf("title","body","created_at"))
        section("events","Events",listOf("title","description","starts_at","venue"))
        section("studies","Bible Studies",listOf("title","scripture_reference","preacher_or_teacher","summary","content","event_date"))
        body.append("<nav><a class='btn' href='/fellowships'>← All Fellowships</a></nav>")
        return page(name,body.toString())
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
        val b=StringBuilder("<div class='grid'>")
        cs.forEach{x->
            val target=when(x.key){"communion_english"->"/devotional-centre/communion-document/english";"communion_yoruba"->"/devotional-centre/communion-document/yoruba";else->"/devotional-centre/collection/${x.slug}"}
            b.append("""<a class="card" href="$target"><div class="icon">${x.icon}</div><h2>${e(x.title)}</h2><p class="muted">Browse downloaded resources in this original library.</p><span class="pill">${a(c,x.key).length()} downloaded</span></a>""")
        }
        val n=runCatching{JSONArray(File(d(c),"Bible/index.json").readText()).length()}.getOrDefault(0)
        val m=runCatching{JSONArray(File(d(c),"Church_Media/index.json").readText()).length()}.getOrDefault(0)
        b.append("""<a class="card" href="/devotional-centre/holy-bible"><div class="icon">📖</div><h2>Uploaded Bible Library</h2><span class="pill">$n modules saved</span></a><a class="card" href="/media-library"><div class="icon">🎧</div><h2>Church Media Library</h2><span class="pill">$m files saved</span></a></div>""")
        val lectionaryFile = File(File(d(c), "Lectionary"), "lectionary_2027.txt")
        val lectionarySaved = lectionaryFile.isFile && lectionaryFile.length() > 0L
        val lectionaryLabel = if (lectionarySaved) "YEAR B · 2027 / YEAR C · 2028 · Offline" else "Download required"
        b.append("""<a class="card" href="/devotional-centre/lectionary"><div class="icon">📅</div><h2>Yearly Lectionary</h2><p class="muted">Read appointed Scripture readings for Sundays, feast days and special services. Available without internet after saving.</p><span class="pill">$lectionaryLabel</span></a>""")
        return page("Devotional & Worship Centre",b.toString())
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
