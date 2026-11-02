// A small web server on the headset, so a book can be sent from a phone or computer on the same Wi-Fi: no cable, no
// account, no cloud. The reader opens "Add a book" in the library; the headset shows an address (http://<its Wi-Fi
// address>:8642) and a four-digit code. The page at that address lists what Fable can read, takes the code and the
// file, shows the transfer as it goes and then the import's named stages, and says plainly what happened.
//
//   GET  /                 the upload page
//   GET  /info             { accepting, maxBytes, formats }
//   POST /upload?name=&code=   the file as the request body (Content-Length required); answers { id } once received
//   GET  /status?id=&code=     a job's stage, measured progress, and outcome
//
// Safety: uploads need the code on the headset and are accepted only while the "Add a book" card is open; five
// wrong codes change the code. Files are size-checked before a byte is stored, written to a temporary file, and
// only become a book after the import has read them fully (Library.cs). Plain HTTP on the local network only.
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public class UploadServer
    {
        readonly Library lib;
        TcpListener listener; Thread thread;
        volatile bool running; int wrongCodes;
        public bool Running => running;
        public int Port { get; private set; }
        public string Address { get; private set; }
        public string Url => Address != null ? $"http://{Address}:{Port}" : null;
        public string Error { get; private set; }
        /// The last device that opened the page (for "connected" on the headset), and when.
        public string LastVisitor { get; private set; }
        public DateTime LastVisit { get; private set; }

        public UploadServer(Library library) { lib = library; }

        public void Start(int port)
        {
            Port = port; Error = null;
            Address = LocalAddress();
            if (Address == null) { Error = "The headset is not on Wi-Fi. Connect it to the same Wi-Fi as your phone or computer."; return; }
            try
            {
                listener = new TcpListener(IPAddress.Any, port);
                listener.Start();
                running = true;
                thread = new Thread(Loop) { IsBackground = true, Name = "Fable upload server" }; thread.Start();
                Debug.Log($"[Fable] upload server listening at {Url}");
            }
            catch (Exception e) { Error = $"The upload page could not start ({e.Message})."; running = false; }
        }

        public void Stop()
        {
            running = false;
            try { listener?.Stop(); } catch { }
        }

        /// The headset's own address on the local network: the interface a packet to the outside would leave by
        /// (a UDP "connect" sends nothing).
        static string LocalAddress()
        {
            try
            {
                using var s = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
                s.Connect("10.254.254.254", 1);
                var ip = ((IPEndPoint)s.LocalEndPoint).Address;
                if (!IPAddress.IsLoopback(ip) && !ip.Equals(IPAddress.Any)) return ip.ToString();
            }
            catch { }
            try
            {
                foreach (var a in Dns.GetHostEntry(Dns.GetHostName()).AddressList)
                    if (a.AddressFamily == AddressFamily.InterNetwork && !IPAddress.IsLoopback(a)) return a.ToString();
            }
            catch { }
#if UNITY_EDITOR
            return "127.0.0.1";
#else
            return null;
#endif
        }

        void Loop()
        {
            while (running)
            {
                TcpClient c;
                try { c = listener.AcceptTcpClient(); }
                catch { if (!running) break; Thread.Sleep(100); continue; }
                ThreadPool.QueueUserWorkItem(_ => { try { Handle(c); } catch (Exception e) { Debug.LogWarning($"[Fable] upload server: {e.Message}"); } finally { try { c.Close(); } catch { } } });
            }
        }

        // ---------------------------------------------------------------- one request

        void Handle(TcpClient client)
        {
            client.ReceiveTimeout = 30000; client.SendTimeout = 30000; client.NoDelay = true;
            var stream = client.GetStream();
            // the request head, up to the blank line (16 KB at most)
            var head = new MemoryStream(); int matched = 0; var one = new byte[1];
            while (head.Length < 16384)
            {
                int n = stream.Read(one, 0, 1); if (n <= 0) return;
                head.WriteByte(one[0]);
                matched = one[0] == (matched % 2 == 0 ? '\r' : '\n') ? matched + 1 : (one[0] == '\r' ? 1 : 0);
                if (matched == 4) break;
            }
            var lines = Encoding.ASCII.GetString(head.ToArray()).Split(new[] { "\r\n" }, StringSplitOptions.None);
            var first = lines[0].Split(' '); if (first.Length < 2) return;
            string method = first[0], target = first[1];
            var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 1; i < lines.Length; i++) { int k = lines[i].IndexOf(':'); if (k > 0) headers[lines[i].Substring(0, k).Trim()] = lines[i].Substring(k + 1).Trim(); }
            string path = target, query = "";
            int q = target.IndexOf('?'); if (q >= 0) { path = target.Substring(0, q); query = target.Substring(q + 1); }
            var args = Query(query);
            var who = (client.Client.RemoteEndPoint as IPEndPoint)?.Address.ToString();

            if (method == "GET" && (path == "/" || path == "/index.html"))
            {
                LastVisitor = Device(headers.TryGetValue("User-Agent", out var ua) ? ua : "") + (who != null ? $" ({who})" : ""); LastVisit = DateTime.UtcNow;
                Debug.Log($"[Fable] upload page opened by {LastVisitor}");
                Send(stream, 200, "text/html; charset=utf-8", Page); return;
            }
            if (method == "GET" && path == "/info")
            {
                Json(stream, 200, new { accepting = lib.Accepting, maxBytes = Library.MaxFileBytes, formats = Library.Formats }); return;
            }
            if (method == "GET" && path == "/status")
            {
                if (!CodeOk(args)) { Json(stream, 401, new { error = "That code doesn't match the one shown in the headset." }); return; }
                var job = args.TryGetValue("id", out var id) ? lib.FindJob(id) : null;
                if (job == null) { Json(stream, 404, new { error = "No such upload." }); return; }
                Json(stream, 200, new { status = job.Status, stage = job.Stage, progress = job.Progress, received = job.Received, expected = job.Expected, title = job.Title, message = job.Message, recovery = job.Recovery });
                return;
            }
            if (method == "POST" && path == "/upload") { Upload(stream, headers, args); return; }
            if (method == "GET" && path == "/favicon.ico") { Send(stream, 204, "text/plain", ""); return; }
            Json(stream, 404, new { error = "Not found." });
        }

        void Upload(NetworkStream stream, Dictionary<string, string> headers, Dictionary<string, string> args)
        {
            if (!CodeOk(args))
            {
                if (Interlocked.Increment(ref wrongCodes) >= 5) { wrongCodes = 0; lib.RotateCode(); }
                Json(stream, 401, new { error = "That code doesn't match the one shown in the headset.", recovery = "Look at the “Add a book” card in the headset and type the four digits shown there." });
                return;
            }
            if (!lib.Accepting) { Json(stream, 409, new { error = "The headset isn't ready for a book.", recovery = "In Fable's library, point at “+ add a book” and pinch, then try again." }); return; }
            var name = args.TryGetValue("name", out var nm) && nm.Length > 0 ? Path.GetFileName(nm) : "book";
            if (!headers.TryGetValue("Content-Length", out var cl) || !long.TryParse(cl, out var length)) { Json(stream, 411, new { error = "The browser didn't say how big the file is.", recovery = "Try another browser." }); return; }
            var refuse = lib.CanAccept(name, length, out var recovery);
            if (refuse != null) { Json(stream, refuse.Contains("nearly full") ? 507 : refuse.Contains("limit") || refuse.Contains("full") || refuse.Contains("GB") ? 413 : 415, new { error = refuse, recovery }); return; }
            if (headers.TryGetValue("Expect", out var ex) && ex.Equals("100-continue", StringComparison.OrdinalIgnoreCase)) { var go = Encoding.ASCII.GetBytes("HTTP/1.1 100 Continue\r\n\r\n"); stream.Write(go, 0, go.Length); }

            var job = lib.BeginTransfer(name, length);
            var temp = lib.IncomingPath(job);
            long got = 0; var buf = new byte[256 * 1024]; float lastReport = 0; var sw = System.Diagnostics.Stopwatch.StartNew();
            string failure = null;
            try
            {
                using var f = File.Create(temp);
                while (got < length)
                {
                    int n;
                    try { n = stream.Read(buf, 0, (int)Math.Min(buf.Length, length - got)); }
                    catch (IOException) { failure = "the connection went quiet for 30 seconds"; break; }
                    if (n <= 0) { failure = "the connection closed"; break; }
                    f.Write(buf, 0, n); got += n;
                    if (sw.ElapsedMilliseconds / 1000f - lastReport > 0.2f) { lastReport = sw.ElapsedMilliseconds / 1000f; lib.TransferProgress(job, got); }
                }
            }
            catch (IOException e) { failure = e.Message.Contains("space") || e.Message.Contains("ENOSPC") ? "the headset ran out of space" : "the file could not be written: " + e.Message; }
            if (failure != null) { lib.TransferProgress(job, got); lib.TransferFailed(job, failure); try { Json(stream, 400, new { error = job.Message, recovery = job.Recovery }); } catch { } return; }
            Debug.Log($"[Fable] upload: {name} {length / 1048576f:F1} MB in {sw.ElapsedMilliseconds / 1000f:F1} s ({length / 1048576f / Mathf.Max(0.01f, sw.ElapsedMilliseconds / 1000f):F1} MB/s)");
            lib.TransferDone(job);
            Json(stream, 200, new { id = job.Id });
        }

        bool CodeOk(Dictionary<string, string> args)
        {
            var want = lib.Code ?? ""; var got = args.TryGetValue("code", out var c) ? c.Trim() : "";
            if (got.Length != want.Length) return false;
            int diff = 0; for (int i = 0; i < want.Length; i++) diff |= want[i] ^ got[i];   // same time whichever digit is wrong
            return diff == 0;
        }

        static Dictionary<string, string> Query(string q)
        {
            var d = new Dictionary<string, string>();
            foreach (var part in q.Split('&')) { if (part.Length == 0) continue; int i = part.IndexOf('='); var k = Uri.UnescapeDataString((i < 0 ? part : part.Substring(0, i)).Replace('+', ' ')); var v = i < 0 ? "" : Uri.UnescapeDataString(part.Substring(i + 1).Replace('+', ' ')); d[k] = v; }
            return d;
        }

        static string Device(string ua) =>
            ua.Contains("iPhone") ? "an iPhone" : ua.Contains("iPad") ? "an iPad" : ua.Contains("Android") ? "an Android phone" :
            ua.Contains("Macintosh") ? "a Mac" : ua.Contains("Windows") ? "a Windows computer" : ua.Contains("CrOS") ? "a Chromebook" : ua.Contains("Linux") ? "a Linux computer" : "a browser";

        static void Json(NetworkStream s, int code, object body) => Send(s, code, "application/json", JsonConvert.SerializeObject(body));

        static void Send(NetworkStream s, int code, string type, string body)
        {
            var b = Encoding.UTF8.GetBytes(body);
            var reason = code switch { 200 => "OK", 204 => "No Content", 400 => "Bad Request", 401 => "Unauthorized", 404 => "Not Found", 409 => "Conflict", 411 => "Length Required", 413 => "Payload Too Large", 415 => "Unsupported Media Type", 507 => "Insufficient Storage", _ => "Error" };
            var h = Encoding.ASCII.GetBytes($"HTTP/1.1 {code} {reason}\r\nContent-Type: {type}\r\nContent-Length: {b.Length}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n");
            s.Write(h, 0, h.Length); s.Write(b, 0, b.Length); s.Flush();
        }

        // ---------------------------------------------------------------- the page

        const string Page = @"<!doctype html>
<html lang=""en""><head><meta charset=""utf-8""><meta name=""viewport"" content=""width=device-width, initial-scale=1"">
<title>Send a book to Fable</title>
<style>
:root{--paper:#f6efe0;--ink:#2a2118;--soft:#6b5a45;--edge:#c9b48f;--accent:#9a5c12;--bad:#9b2d1e;--good:#2f6b2f}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.5 Georgia,'Iowan Old Style',serif}
main{max-width:560px;margin:0 auto;padding:24px 16px 48px}h1{font-size:26px;margin:0 0 4px}p{margin:8px 0}
.small{font-size:14px;color:var(--soft)}.box{border:1px solid var(--edge);border-radius:10px;padding:14px 16px;margin:16px 0;background:#fbf7ee}
ol{padding-left:22px;margin:8px 0}li{margin:4px 0}label{display:block;font-weight:bold;margin:14px 0 6px}
input[type=text]{font:inherit;font-size:24px;letter-spacing:6px;width:8ch;padding:6px 10px;border:1px solid var(--edge);border-radius:8px;background:#fff}
input[type=file]{font:inherit;width:100%}button{font:inherit;font-weight:bold;background:var(--accent);color:#fff;border:0;border-radius:8px;padding:12px 18px;margin-top:16px;width:100%}
button:disabled{opacity:.45}.bar{height:12px;background:#e8dcc4;border-radius:6px;overflow:hidden;margin:10px 0}.bar i{display:block;height:100%;width:0;background:var(--accent);transition:width .2s}
.bar.unknown i{width:30%;animation:slide 1.4s infinite ease-in-out}@keyframes slide{0%{margin-left:-30%}100%{margin-left:100%}}
#msg{min-height:1.5em}.bad{color:var(--bad)}.good{color:var(--good)}.stages{list-style:none;padding:0}.stages li:before{content:'\25CB  ';color:var(--soft)}.stages li.done:before{content:'\25CF  ';color:var(--good)}.stages li.now:before{content:'\25D0  ';color:var(--accent)}
</style></head><body><main>
<h1>Send a book to Fable</h1>
<p class=""small"">This page comes from your headset over your Wi-Fi. Nothing is sent anywhere else.</p>
<div class=""box"">
<p><b>Fable can read</b></p>
<ul><li><b>EPUB</b> books without DRM (from Standard Ebooks, Project Gutenberg, and many shops that sell DRM-free books)</li>
<li><b>PDF</b> files. Pages keep their layout. Highlighting and search work where the PDF has real text; scanned pages are shown as pictures.</li></ul>
<p class=""small"">Up to 150 MB a file. Not yet: Kindle files (MOBI, AZW, KFX), DRM-protected books, Word documents, plain text.</p>
</div>
<ol><li>In the headset, open <b>+ add a book</b> in your library.</li><li>Type the four-digit code it shows.</li><li>Choose the book and press <b>Send to headset</b>.</li></ol>
<label for=""code"">Code from the headset</label><input id=""code"" type=""text"" inputmode=""numeric"" maxlength=""4"" autocomplete=""off"">
<label for=""file"">Book</label><input id=""file"" type=""file"" accept="".epub,.pdf,application/epub+zip,application/pdf"">
<button id=""send"" disabled>Send to headset</button>
<div class=""bar"" id=""bar"" hidden><i></i></div><p id=""msg""></p>
<ul class=""stages"" id=""stages"" hidden><li data-s=""receiving"">Sending to the headset</li><li data-s=""checking the file"">Checking the file</li><li data-s=""reading"">Reading chapters or pages</li><li data-s=""splitting sentences"">Preparing the text</li><li data-s=""saving"">Saving to your library</li><li data-s=""ready"">On your shelf</li></ul>
<button id=""again"" hidden>Send another book</button>
</main><script>
const $=id=>document.getElementById(id), MAX=150*1048576, order=['receiving','checking the file','reading','splitting sentences','saving','ready'];
const okExt=n=>/\.(epub|pdf)$/i.test(n);
function check(){const f=$('file').files[0],c=$('code').value.trim();let why='';
 if(f&&!okExt(f.name))why=/\.(mobi|azw3?|kfx|prc)$/i.test(f.name)?'That is a Kindle file. Fable reads EPUB and PDF; a DRM-free Kindle book can be converted to EPUB (for example with Calibre).':'Fable reads EPUB and PDF files; this is neither.';
 else if(f&&f.size>MAX)why='This file is '+(f.size/1048576).toFixed(0)+' MB; the limit is 150 MB.';
 say(why,'bad');$('send').disabled=!(f&&!why&&/^\d{4}$/.test(c));}
function say(t,cls){$('msg').textContent=t||'';$('msg').className=cls||'';}
function bar(p){const b=$('bar');b.hidden=false;b.classList.toggle('unknown',p<0);b.firstElementChild.style.width=p<0?'':(p*100).toFixed(1)+'%';}
function stage(s,status){$('stages').hidden=false;let k=order.indexOf(s);if(k<0&&/reading/.test(s))k=2;if(k<0&&s==='drawing the first page')k=4;
 [...$('stages').children].forEach((li,i)=>li.className=status==='ready'?'done':i<k?'done':i===k?'now':'');}
$('file').onchange=check;$('code').oninput=check;
$('again').onclick=()=>{$('again').hidden=true;$('stages').hidden=true;$('bar').hidden=true;$('file').value='';say('');check();};
$('send').onclick=()=>{const f=$('file').files[0],code=$('code').value.trim();$('send').disabled=true;
 const x=new XMLHttpRequest();x.open('POST','/upload?code='+code+'&name='+encodeURIComponent(f.name));
 x.upload.onprogress=e=>{if(e.lengthComputable){bar(e.loaded/e.total);say('Sending '+f.name+': '+(e.loaded/1048576).toFixed(1)+' of '+(e.total/1048576).toFixed(1)+' MB');}};
 stage('receiving');
 x.onload=()=>{let r={};try{r=JSON.parse(x.responseText)}catch(e){}
  if(x.status!==200){say((r.error||'The headset refused the file.')+' '+(r.recovery||''),'bad');$('send').disabled=false;$('stages').hidden=true;return;}
  poll(r.id,code);};
 x.onerror=()=>{say('The connection to the headset was lost before the file arrived. Nothing was added. Check both are on the same Wi-Fi and try again.','bad');$('send').disabled=false;};
 x.send(f);};
function poll(id,code){fetch('/status?id='+id+'&code='+code).then(r=>r.json()).then(s=>{
  if(s.error){say(s.error,'bad');return;}
  stage(s.stage,s.status);bar(s.status==='ready'?1:s.progress);
  if(s.status==='ready'){say('“'+(s.title||'Your book')+'” is on your shelf in the headset.','good');$('again').hidden=false;return;}
  if(s.status==='duplicate'){say(s.message,'good');$('stages').hidden=true;$('again').hidden=false;return;}
  if(s.status==='failed'){say(s.message+' '+(s.recovery||''),'bad');$('stages').hidden=true;$('again').hidden=false;return;}
  say('Importing: '+s.stage+(s.progress>=0?' ('+Math.round(s.progress*100)+'%)':'')+'. You can keep reading in the headset meanwhile.');
  setTimeout(()=>poll(id,code),700);}).catch(()=>setTimeout(()=>poll(id,code),1500));}
</script></body></html>";
    }
}
