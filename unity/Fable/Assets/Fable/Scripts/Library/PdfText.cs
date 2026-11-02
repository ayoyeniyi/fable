// A small PDF reader for Fable's imports: enough of the format to find the pages in order and pull their text out,
// with no outside libraries, on a background thread. Page images are not drawn here (PdfPages does that with the
// platform's own renderer); this only decides what text a page holds and whether that text can be trusted.
//
// Objects are found by scanning the file for "N G obj" (so a broken cross-reference table does not matter) and by
// unpacking object streams (PDF 1.5+). Streams are decoded for FlateDecode (with PNG predictors), ASCIIHex and
// ASCII85. Text comes from the content stream's text operators (Tj, TJ, ', ", with Td, TD, Tm, T*) through each font's
// ToUnicode map, or, for simple fonts without one, its WinAnsi / MacRoman / Standard encoding and Differences. Glyph
// widths place the words, so spaces and line breaks follow the layout. Form XObjects are followed one level deep.
//
// What is refused or reported, never guessed: an encrypted file (rejected), a page whose text cannot be decoded
// (CID fonts without a ToUnicode map; the page counts as having no text), and pages with no text at all (scans).
// There is no OCR.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;

namespace Fable
{
    public class PdfText
    {
        // ---------------------------------------------------------------- object model

        public class PdfName { public readonly string V; public PdfName(string v) { V = v; } public override string ToString() => "/" + V; }
        public class PdfRef { public readonly int N; public PdfRef(int n) { N = n; } }
        public class PdfString { public readonly byte[] B; public PdfString(byte[] b) { B = b; } }
        public class PdfDict : Dictionary<string, object> { public byte[] Stream; }
        public class PdfOp { public readonly string V; public PdfOp(string v) { V = v; } }

        readonly byte[] data;
        readonly Dictionary<int, int> offsets = new();             // object number -> offset of its body (after "obj")
        readonly Dictionary<int, object> cache = new();
        readonly Dictionary<int, (int stm, int index)> compressed = new();
        readonly Dictionary<int, byte[]> objStms = new();   // decoded object streams
        PdfDict trailer;

        public int PageCount => pages.Count;
        readonly List<PdfDict> pages = new();
        public bool Encrypted { get; private set; }
        public string Title, Author;

        public PdfText(byte[] bytes) { data = bytes; }

        public static bool LooksLikePdf(string path)
        {
            try { using var f = File.OpenRead(path); var b = new byte[1024]; int n = f.Read(b, 0, b.Length); return Encoding.ASCII.GetString(b, 0, n).Contains("%PDF-"); }
            catch { return false; }
        }

        /// Scan the file, find the catalogue, list the pages. Throws ImportException on what cannot be read.
        public void Open()
        {
            ScanObjects();
            if (trailer == null || !trailer.ContainsKey("Root"))
            {
                // no trailer found (a damaged tail): fall back to any catalogue object
                foreach (var n in offsets.Keys.ToList()) if (Get(n) is PdfDict d && Name(d, "Type") == "Catalog") { trailer = new PdfDict { ["Root"] = new PdfRef(n) }; break; }
            }
            if (trailer == null) throw new ImportException("This PDF has no readable structure (no catalogue found).", "The file may be damaged or cut short. Send it again, or try a different copy.");
            if (trailer.ContainsKey("Encrypt")) { Encrypted = true; throw new ImportException("This PDF is encrypted or password-protected, so Fable can't open it.", "Open it on a computer, remove the protection (for example by printing it to a new PDF), and send that file."); }
            var root = Resolve(trailer["Root"]) as PdfDict ?? throw new ImportException("This PDF's catalogue is missing.", "The file may be damaged. Try a different copy.");
            var tree = Resolve(root.GetValueOrDefault("Pages")) as PdfDict ?? throw new ImportException("This PDF has no page list.", "The file may be damaged. Try a different copy.");
            Walk(tree, null, 0);
            if (Resolve(trailer.GetValueOrDefault("Info")) is PdfDict info) { Title = Str(info, "Title"); Author = Str(info, "Author"); }
        }

        void Walk(PdfDict node, PdfDict inheritedRes, int depth)
        {
            if (depth > 40 || pages.Count > 20000) return;
            var res = Resolve(node.GetValueOrDefault("Resources")) as PdfDict ?? inheritedRes;
            if (Name(node, "Type") == "Page" || !node.ContainsKey("Kids"))
            {
                if (!node.ContainsKey("Resources") && res != null) node["Resources"] = res;
                pages.Add(node); return;
            }
            if (Resolve(node["Kids"]) is List<object> kids) foreach (var k in kids) if (Resolve(k) is PdfDict kid) Walk(kid, res, depth + 1);
        }

        // ---------------------------------------------------------------- scanning

        void ScanObjects()
        {
            int i = 0, n = data.Length;
            while (i < n - 3)
            {
                // the next "obj" keyword
                int at = IndexOf(data, "obj", i); if (at < 0) break;
                i = at + 3;
                if (at + 3 < n && !IsDelimOrSpace(data[at + 3])) continue;   // "object", "objstm"...
                // walk back: generation, object number
                int p = at - 1; while (p >= 0 && IsSpace(data[p])) p--;
                int ge = p; while (p >= 0 && IsDigit(data[p])) p--; if (p == ge) continue;
                while (p >= 0 && IsSpace(data[p])) p--;
                int ne = p; while (p >= 0 && IsDigit(data[p])) p--; if (p == ne) continue;
                if (p >= 0 && !IsDelimOrSpace(data[p])) continue;
                int num = int.Parse(Encoding.ASCII.GetString(data, p + 1, ne - p), CultureInfo.InvariantCulture);
                offsets[num] = at + 3;   // later definitions (incremental updates) win
                // skip over a stream's bytes, so their contents are never mistaken for objects
                int dictEnd = Math.Min(n, at + 3 + 4096);
                int s = IndexOf(data, "stream", at + 3, dictEnd);
                int e = IndexOf(data, "endobj", at + 3, dictEnd);
                if (s >= 0 && (e < 0 || s < e))
                {
                    int es = IndexOf(data, "endstream", s + 6);
                    if (es > 0) i = es + 9;
                }
            }
            // trailers: the classic one(s) and cross-reference streams; the last one wins, merged with earlier ones
            int t = 0;
            while ((t = IndexOf(data, "trailer", t)) >= 0)
            {
                t += 7; var pos = t;
                try { if (ParseObject(ref pos) is PdfDict d) trailer = Merge(trailer, d); } catch { }
            }
            foreach (var num in offsets.Keys.ToList())
            {
                if (!(Get(num) is PdfDict d)) continue;
                var type = Name(d, "Type");
                if (type == "XRef") trailer = Merge(trailer, d);
                if (type == "ObjStm") IndexObjStm(num, d);
            }
        }

        static PdfDict Merge(PdfDict older, PdfDict newer)
        {
            if (older == null) return newer;
            foreach (var kv in older) if (!newer.ContainsKey(kv.Key)) newer[kv.Key] = kv.Value;
            return newer;
        }

        void IndexObjStm(int num, PdfDict d)
        {
            var bytes = Decode(d); if (bytes == null) return;
            int count = Int(d, "N"); var pos = 0;
            for (int k = 0; k < count; k++)
            {
                if (!(ParseObjectIn(bytes, ref pos) is double on)) break;
                ParseObjectIn(bytes, ref pos);
                if (!offsets.ContainsKey((int)on)) compressed[(int)on] = (num, k);
            }
        }

        object Get(int num)
        {
            if (cache.TryGetValue(num, out var o)) return o;
            cache[num] = null;   // guards against reference loops
            if (offsets.TryGetValue(num, out var off))
            {
                var pos = off;
                try
                {
                    o = ParseObject(ref pos);
                    if (o is PdfDict d) { SkipSpace(data, ref pos); if (Match(data, pos, "stream")) d.Stream = ReadStream(d, pos + 6); }
                }
                catch { o = null; }
            }
            else if (compressed.TryGetValue(num, out var c) && Get(c.stm) is PdfDict stm)
            {
                if (!objStms.TryGetValue(c.stm, out var bytes)) objStms[c.stm] = bytes = Decode(stm);
                if (bytes != null)
                {
                    int first = Int(stm, "First"), count = Int(stm, "N"); var pos = 0; int objOff = -1;
                    for (int k = 0; k < count; k++)
                    {
                        var on = ParseObjectIn(bytes, ref pos); var oo = ParseObjectIn(bytes, ref pos);
                        if (k == c.index && oo is double dd) { objOff = (int)dd; break; }
                    }
                    if (objOff >= 0) { pos = first + objOff; try { o = ParseObjectIn(bytes, ref pos); } catch { o = null; } }
                }
            }
            cache[num] = o;
            return o;
        }

        byte[] ReadStream(PdfDict d, int pos)
        {
            if (pos < data.Length && data[pos] == '\r') pos++;
            if (pos < data.Length && data[pos] == '\n') pos++;
            int len = -1;
            var l = d.GetValueOrDefault("Length");
            if (l is double ld) len = (int)ld; else if (l is PdfRef lr && offsets.ContainsKey(lr.N) && Get(lr.N) is double rd) len = (int)rd;
            if (len < 0 || pos + len > data.Length || !Match(data, SkipSpaceAt(data, pos + len), "endstream"))
            {
                int es = IndexOf(data, "endstream", pos); if (es < 0) return null;
                len = es - pos; while (len > 0 && (data[pos + len - 1] == '\n' || data[pos + len - 1] == '\r')) len--;
            }
            var b = new byte[len]; Buffer.BlockCopy(data, pos, b, 0, len); return b;
        }

        // ---------------------------------------------------------------- decoding streams

        public byte[] Decode(PdfDict d)
        {
            var b = d.Stream; if (b == null) return null;
            var filters = new List<string>(); var parms = new List<PdfDict>();
            var f = Resolve(d.GetValueOrDefault("Filter"));
            if (f is PdfName fn) filters.Add(fn.V); else if (f is List<object> fl) foreach (var x in fl) if (Resolve(x) is PdfName xn) filters.Add(xn.V);
            var dp = Resolve(d.GetValueOrDefault("DecodeParms"));
            if (dp is PdfDict dpd) parms.Add(dpd); else if (dp is List<object> dpl) foreach (var x in dpl) parms.Add(Resolve(x) as PdfDict);
            for (int i = 0; i < filters.Count; i++)
            {
                var p = i < parms.Count ? parms[i] : null;
                switch (filters[i])
                {
                    case "FlateDecode": case "Fl": b = Inflate(b); if (b != null && p != null && Int(p, "Predictor") >= 10) b = UnPredict(b, Math.Max(1, Int(p, "Columns", 1)), Math.Max(1, Int(p, "Colors", 1))); break;
                    case "ASCIIHexDecode": case "AHx": b = AsciiHex(b); break;
                    case "ASCII85Decode": case "A85": b = Ascii85(b); break;
                    default: return null;   // images (DCT, JBIG2, CCITT) and LZW: not text
                }
                if (b == null) return null;
            }
            return b;
        }

        static byte[] Inflate(byte[] b)
        {
            if (b.Length < 2) return null;
            try
            {
                // zlib: skip the two-byte header; DeflateStream reads raw deflate. A truncated stream yields what it can.
                using var ms = new MemoryStream(b, 2, b.Length - 2); using var z = new DeflateStream(ms, CompressionMode.Decompress); using var outp = new MemoryStream();
                var buf = new byte[16384]; int n;
                try { while ((n = z.Read(buf, 0, buf.Length)) > 0) { outp.Write(buf, 0, n); if (outp.Length > (64 << 20)) break; } } catch (InvalidDataException) { }
                return outp.ToArray();
            }
            catch { return null; }
        }

        static byte[] UnPredict(byte[] b, int cols, int colors)
        {
            int row = cols * colors; var outp = new List<byte>(b.Length); var prev = new byte[row];
            for (int i = 0; i + row < b.Length + 1 && i < b.Length; i += row + 1)
            {
                int type = b[i]; var cur = new byte[row];
                for (int k = 0; k < row && i + 1 + k < b.Length; k++)
                {
                    int raw = b[i + 1 + k], left = k >= colors ? cur[k - colors] : 0, up = prev[k], ul = k >= colors ? prev[k - colors] : 0;
                    cur[k] = (byte)(type switch { 1 => raw + left, 2 => raw + up, 3 => raw + ((left + up) >> 1), 4 => raw + Paeth(left, up, ul), _ => raw });
                }
                outp.AddRange(cur); prev = cur;
            }
            return outp.ToArray();
        }
        static int Paeth(int a, int b, int c) { int p = a + b - c, pa = Math.Abs(p - a), pb = Math.Abs(p - b), pc = Math.Abs(p - c); return pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }

        static byte[] AsciiHex(byte[] b)
        {
            var outp = new List<byte>(); int hi = -1;
            foreach (var c in b) { if (c == '>') break; int v = Hex(c); if (v < 0) continue; if (hi < 0) hi = v; else { outp.Add((byte)(hi * 16 + v)); hi = -1; } }
            if (hi >= 0) outp.Add((byte)(hi * 16));
            return outp.ToArray();
        }

        static byte[] Ascii85(byte[] b)
        {
            var outp = new List<byte>(); var grp = new int[5]; int n = 0;
            for (int i = 0; i < b.Length; i++)
            {
                int c = b[i]; if (c == '~') break; if (IsSpace((byte)c)) continue;
                if (c == 'z' && n == 0) { outp.AddRange(new byte[4]); continue; }
                if (c < '!' || c > 'u') return null;
                grp[n++] = c - '!';
                if (n == 5) { uint v = 0; foreach (var g in grp) v = v * 85 + (uint)g; outp.Add((byte)(v >> 24)); outp.Add((byte)(v >> 16)); outp.Add((byte)(v >> 8)); outp.Add((byte)v); n = 0; }
            }
            if (n > 1) { for (int k = n; k < 5; k++) grp[k] = 84; uint v = 0; foreach (var g in grp) v = v * 85 + (uint)g; for (int k = 0; k < n - 1; k++) outp.Add((byte)(v >> (24 - 8 * k))); }
            return outp.ToArray();
        }

        // ---------------------------------------------------------------- the object parser

        object ParseObject(ref int pos) => ParseObjectIn(data, ref pos);

        object ParseObjectIn(byte[] b, ref int pos)
        {
            SkipSpace(b, ref pos); if (pos >= b.Length) return null;
            byte c = b[pos];
            if (c == '/') { pos++; return new PdfName(ReadName(b, ref pos)); }
            if (c == '(') return new PdfString(ReadLiteral(b, ref pos));
            if (c == '<')
            {
                if (pos + 1 < b.Length && b[pos + 1] == '<')
                {
                    pos += 2; var d = new PdfDict();
                    while (true)
                    {
                        SkipSpace(b, ref pos); if (pos >= b.Length) break;
                        if (b[pos] == '>' && pos + 1 < b.Length && b[pos + 1] == '>') { pos += 2; break; }
                        if (b[pos] != '/') { pos++; continue; }
                        pos++; var key = ReadName(b, ref pos);
                        d[key] = ParseObjectIn(b, ref pos);
                    }
                    return d;
                }
                pos++; var hex = new List<byte>(); int hi = -1;
                while (pos < b.Length && b[pos] != '>') { int v = Hex(b[pos++]); if (v < 0) continue; if (hi < 0) hi = v; else { hex.Add((byte)(hi * 16 + v)); hi = -1; } }
                if (hi >= 0) hex.Add((byte)(hi * 16));
                pos++; return new PdfString(hex.ToArray());
            }
            if (c == '[')
            {
                pos++; var list = new List<object>();
                while (true) { SkipSpace(b, ref pos); if (pos >= b.Length || b[pos] == ']') { pos++; break; } list.Add(ParseObjectIn(b, ref pos)); }
                return list;
            }
            if (IsDigit(c) || c == '-' || c == '+' || c == '.')
            {
                var num = ReadNumber(b, ref pos);
                // "N G R": a reference
                int save = pos; SkipSpace(b, ref pos);
                if (num == Math.Floor(num) && pos < b.Length && IsDigit(b[pos]))
                {
                    int p2 = pos; var gen = ReadNumber(b, ref p2); SkipSpace(b, ref p2);
                    if (p2 < b.Length && b[p2] == 'R' && (p2 + 1 >= b.Length || IsDelimOrSpace(b[p2 + 1]))) { pos = p2 + 1; return new PdfRef((int)num); }
                }
                pos = save; return num;
            }
            // keyword: true, false, null, or (in content streams) an operator
            int st = pos; while (pos < b.Length && !IsDelimOrSpace(b[pos])) pos++;
            if (pos == st) { pos++; return null; }
            var kw = Encoding.ASCII.GetString(b, st, pos - st);
            return kw == "true" ? true : kw == "false" ? false : kw == "null" ? null : new PdfOp(kw);
        }

        static string ReadName(byte[] b, ref int pos)
        {
            var sb = new StringBuilder();
            while (pos < b.Length && !IsDelimOrSpace(b[pos]))
            {
                if (b[pos] == '#' && pos + 2 < b.Length && Hex(b[pos + 1]) >= 0 && Hex(b[pos + 2]) >= 0) { sb.Append((char)(Hex(b[pos + 1]) * 16 + Hex(b[pos + 2]))); pos += 3; }
                else sb.Append((char)b[pos++]);
            }
            return sb.ToString();
        }

        static byte[] ReadLiteral(byte[] b, ref int pos)
        {
            pos++; int depth = 1; var outp = new List<byte>();
            while (pos < b.Length)
            {
                byte c = b[pos++];
                if (c == '\\' && pos < b.Length)
                {
                    byte e = b[pos++];
                    switch (e)
                    {
                        case (byte)'n': outp.Add(10); break; case (byte)'r': outp.Add(13); break; case (byte)'t': outp.Add(9); break;
                        case (byte)'b': outp.Add(8); break; case (byte)'f': outp.Add(12); break;
                        case (byte)'\r': if (pos < b.Length && b[pos] == '\n') pos++; break;
                        case (byte)'\n': break;
                        default:
                            if (e >= '0' && e <= '7') { int v = e - '0'; for (int k = 0; k < 2 && pos < b.Length && b[pos] >= '0' && b[pos] <= '7'; k++) v = v * 8 + (b[pos++] - '0'); outp.Add((byte)v); }
                            else outp.Add(e);
                            break;
                    }
                    continue;
                }
                if (c == '(') depth++;
                else if (c == ')') { if (--depth == 0) break; }
                outp.Add(c);
            }
            return outp.ToArray();
        }

        static double ReadNumber(byte[] b, ref int pos)
        {
            int st = pos; if (b[pos] == '-' || b[pos] == '+') pos++;
            while (pos < b.Length && (IsDigit(b[pos]) || b[pos] == '.')) pos++;
            double.TryParse(Encoding.ASCII.GetString(b, st, pos - st), NumberStyles.Float, CultureInfo.InvariantCulture, out var v);
            return v;
        }

        // ---------------------------------------------------------------- small helpers

        public object Resolve(object o) { int guard = 0; while (o is PdfRef r && guard++ < 16) o = Get(r.N); return o; }
        string Name(PdfDict d, string key) => Resolve(d?.GetValueOrDefault(key)) is PdfName n ? n.V : null;
        int Int(PdfDict d, string key, int dflt = 0) => Resolve(d?.GetValueOrDefault(key)) is double v ? (int)v : dflt;
        string Str(PdfDict d, string key) => Resolve(d?.GetValueOrDefault(key)) is PdfString s ? TextString(s.B) : null;

        /// A PDF "text string": UTF-16BE with a byte-order mark, else PDFDocEncoding (close to Latin-1).
        static string TextString(byte[] b)
        {
            if (b.Length >= 2 && b[0] == 0xFE && b[1] == 0xFF) return Encoding.BigEndianUnicode.GetString(b, 2, b.Length - 2).Trim('\0', ' ');
            if (b.Length >= 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF) return Encoding.UTF8.GetString(b, 3, b.Length - 3).Trim();
            var sb = new StringBuilder(); foreach (var c in b) sb.Append(c >= 128 && c < 160 ? ' ' : (char)c); return sb.ToString().Trim('\0', ' ');
        }

        static bool IsSpace(byte c) => c == 32 || c == 9 || c == 10 || c == 13 || c == 12 || c == 0;
        static bool IsDigit(byte c) => c >= '0' && c <= '9';
        static bool IsDelimOrSpace(byte c) => IsSpace(c) || c == '(' || c == ')' || c == '<' || c == '>' || c == '[' || c == ']' || c == '{' || c == '}' || c == '/' || c == '%';
        static int Hex(byte c) => c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
        static void SkipSpace(byte[] b, ref int pos)
        {
            while (pos < b.Length)
            {
                if (IsSpace(b[pos])) { pos++; continue; }
                if (b[pos] == '%') { while (pos < b.Length && b[pos] != '\n' && b[pos] != '\r') pos++; continue; }
                break;
            }
        }
        static int SkipSpaceAt(byte[] b, int pos) { SkipSpace(b, ref pos); return pos; }
        static bool Match(byte[] b, int pos, string s) { if (pos < 0 || pos + s.Length > b.Length) return false; for (int i = 0; i < s.Length; i++) if (b[pos + i] != s[i]) return false; return true; }
        static int IndexOf(byte[] b, string s, int from, int to = -1)
        {
            if (to < 0 || to > b.Length) to = b.Length; byte f = (byte)s[0];
            for (int i = Math.Max(0, from); i <= to - s.Length; i++) { if (b[i] != f) continue; int k = 1; while (k < s.Length && b[i + k] == s[k]) k++; if (k == s.Length) return i; }
            return -1;
        }

        // ---------------------------------------------------------------- fonts

        class Font
        {
            public bool TwoByte;                               // CID fonts (Type0): two-byte codes
            public Dictionary<int, string> Map;                // code -> text (ToUnicode, or the simple font's encoding)
            public Dictionary<int, float> Widths = new();      // code -> width in 1/1000 em
            public float DefaultWidth = 500;
            public bool Reliable = true;                       // false: codes cannot be turned into text
        }
        readonly Dictionary<PdfDict, Font> fonts = new();

        Font LoadFont(PdfDict fd)
        {
            if (fd == null) return null;
            if (fonts.TryGetValue(fd, out var f)) return f;
            f = new Font(); fonts[fd] = f;
            var subtype = Name(fd, "Subtype");
            f.TwoByte = subtype == "Type0";
            if (Resolve(fd.GetValueOrDefault("ToUnicode")) is PdfDict tu && Decode(tu) is byte[] cmap) f.Map = ParseCMap(cmap, f);
            if (f.TwoByte)
            {
                if (Resolve(fd.GetValueOrDefault("DescendantFonts")) is List<object> desc && desc.Count > 0 && Resolve(desc[0]) is PdfDict cid)
                {
                    f.DefaultWidth = Int(cid, "DW", 1000);
                    if (Resolve(cid.GetValueOrDefault("W")) is List<object> w)
                        for (int i = 0; i < w.Count;)
                        {
                            if (!(Resolve(w[i]) is double c0)) break;
                            if (i + 1 < w.Count && Resolve(w[i + 1]) is List<object> arr) { for (int k = 0; k < arr.Count; k++) if (Resolve(arr[k]) is double wv) f.Widths[(int)c0 + k] = (float)wv; i += 2; }
                            else if (i + 2 < w.Count && Resolve(w[i + 1]) is double c1 && Resolve(w[i + 2]) is double wv2) { for (int c = (int)c0; c <= (int)c1 && c - (int)c0 < 65536; c++) f.Widths[c] = (float)wv2; i += 3; }
                            else break;
                        }
                }
                if (f.Map == null) f.Reliable = false;   // Identity-H with no ToUnicode: glyph ids, not characters
            }
            else
            {
                int first = Int(fd, "FirstChar");
                if (Resolve(fd.GetValueOrDefault("Widths")) is List<object> ws) for (int k = 0; k < ws.Count; k++) if (Resolve(ws[k]) is double wv) f.Widths[first + k] = (float)wv;
                if (f.Widths.Count > 0) f.DefaultWidth = f.Widths.Values.Where(v => v > 0).DefaultIfEmpty(500).Average();
                if (f.Map == null || f.Map.Count == 0)
                {
                    f.Map = new Dictionary<int, string>();
                    var enc = Resolve(fd.GetValueOrDefault("Encoding"));
                    string baseEnc = enc is PdfName en ? en.V : enc is PdfDict ed ? Name(ed, "BaseEncoding") : null;
                    for (int c = 0; c < 256; c++) { var ch = SimpleEncoding(baseEnc, c); if (ch != null) f.Map[c] = ch; }
                    if (enc is PdfDict ed2 && Resolve(ed2.GetValueOrDefault("Differences")) is List<object> diffs)
                    {
                        int code = 0;
                        foreach (var x in diffs)
                        {
                            var v = Resolve(x);
                            if (v is double dv) code = (int)dv;
                            else if (v is PdfName gn) { var t = Glyph(gn.V); if (t != null) f.Map[code] = t; else f.Map.Remove(code); code++; }
                        }
                    }
                    if (subtype == "Type3") f.Reliable = f.Map.Count > 0;
                }
            }
            return f;
        }

        static Dictionary<int, string> ParseCMap(byte[] cmap, Font f)
        {
            var map = new Dictionary<int, string>();
            var s = Encoding.ASCII.GetString(cmap);
            // code length from the codespace range (<00> one byte, <0000> two)
            var cs = System.Text.RegularExpressions.Regex.Match(s, @"begincodespacerange\s*<([0-9A-Fa-f]+)>");
            if (cs.Success) f.TwoByte = cs.Groups[1].Value.Length >= 4;
            foreach (System.Text.RegularExpressions.Match blk in System.Text.RegularExpressions.Regex.Matches(s, @"beginbfchar(.*?)endbfchar", System.Text.RegularExpressions.RegexOptions.Singleline))
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(blk.Groups[1].Value, @"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>"))
                    map[Convert.ToInt32(m.Groups[1].Value, 16)] = Utf16Hex(m.Groups[2].Value);
            foreach (System.Text.RegularExpressions.Match blk in System.Text.RegularExpressions.Regex.Matches(s, @"beginbfrange(.*?)endbfrange", System.Text.RegularExpressions.RegexOptions.Singleline))
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(blk.Groups[1].Value, @"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<([0-9A-Fa-f]*)>|\[([^\]]*)\])"))
                {
                    int lo = Convert.ToInt32(m.Groups[1].Value, 16), hi = Convert.ToInt32(m.Groups[2].Value, 16);
                    if (hi - lo > 65535 || hi < lo) continue;
                    if (m.Groups[4].Success && m.Groups[3].Value.StartsWith("<"))
                    {
                        var dst = m.Groups[4].Value; if (dst.Length < 4) dst = dst.PadLeft(4, '0');
                        int baseCp = Convert.ToInt32(dst.Substring(dst.Length - 4), 16); var prefix = dst.Length > 4 ? Utf16Hex(dst.Substring(0, dst.Length - 4)) : "";
                        for (int c = lo; c <= hi; c++) map[c] = prefix + (char)(baseCp + c - lo);
                    }
                    else
                    {
                        var items = System.Text.RegularExpressions.Regex.Matches(m.Groups[5].Value, @"<([0-9A-Fa-f]*)>");
                        for (int k = 0; k < items.Count && lo + k <= hi; k++) map[lo + k] = Utf16Hex(items[k].Groups[1].Value);
                    }
                }
            return map;
        }

        static string Utf16Hex(string hex)
        {
            if (hex.Length % 4 != 0) hex = hex.PadLeft((hex.Length + 3) / 4 * 4, '0');
            var sb = new StringBuilder();
            for (int i = 0; i + 4 <= hex.Length; i += 4) sb.Append((char)Convert.ToInt32(hex.Substring(i, 4), 16));
            return sb.ToString();
        }

        static readonly Encoding MacRoman = CodePage(10000);
        const string Cp1252High = "\u20ac\0\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\0\u017d\0\0\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\0\u017e\u0178";
        static Encoding CodePage(int cp) { try { return Encoding.GetEncoding(cp); } catch { return null; } }

        static string SimpleEncoding(string enc, int c)
        {
            if (c < 32) return null;
            if (c < 127) return c == 96 && enc == null ? "‘" : c == 39 && enc == null ? "’" : ((char)c).ToString();   // StandardEncoding's curly quotes
            if (enc == "MacRomanEncoding" && MacRoman != null) return MacRoman.GetString(new[] { (byte)c });
            if (c >= 128 && c < 160) return Cp1252High[c - 128] == '\0' ? null : Cp1252High[c - 128].ToString();   // no code pages needed (IL2CPP may lack them)
            return ((char)c).ToString();
        }

        static readonly Dictionary<string, string> GlyphNames = new()
        {
            ["space"] = " ", ["quoteright"] = "’", ["quoteleft"] = "‘", ["quotedblleft"] = "“", ["quotedblright"] = "”", ["quotesingle"] = "'", ["quotedbl"] = "\"",
            ["hyphen"] = "-", ["endash"] = "–", ["emdash"] = "—", ["period"] = ".", ["comma"] = ",", ["colon"] = ":", ["semicolon"] = ";", ["exclam"] = "!", ["question"] = "?",
            ["parenleft"] = "(", ["parenright"] = ")", ["bracketleft"] = "[", ["bracketright"] = "]", ["slash"] = "/", ["ampersand"] = "&", ["percent"] = "%", ["dollar"] = "$", ["asterisk"] = "*",
            ["fi"] = "fi", ["fl"] = "fl", ["ff"] = "ff", ["ffi"] = "ffi", ["ffl"] = "ffl", ["ellipsis"] = "…", ["bullet"] = "•", ["dagger"] = "†", ["section"] = "§",
            ["zero"] = "0", ["one"] = "1", ["two"] = "2", ["three"] = "3", ["four"] = "4", ["five"] = "5", ["six"] = "6", ["seven"] = "7", ["eight"] = "8", ["nine"] = "9",
            ["eacute"] = "é", ["egrave"] = "è", ["agrave"] = "à", ["ccedilla"] = "ç", ["udieresis"] = "ü", ["odieresis"] = "ö", ["adieresis"] = "ä", ["germandbls"] = "ß", ["nbspace"] = " ",
        };

        static string Glyph(string name)
        {
            if (GlyphNames.TryGetValue(name, out var t)) return t;
            if (name.Length == 1) return name;
            if (name.StartsWith("uni") && name.Length == 7 && int.TryParse(name.Substring(3), NumberStyles.HexNumber, null, out var u)) return ((char)u).ToString();
            var dot = name.IndexOf('.'); if (dot > 0) return Glyph(name.Substring(0, dot));   // "a.sc", "one.oldstyle"
            return null;
        }

        // ---------------------------------------------------------------- page text

        public class PageText { public string Text = ""; public bool Reliable; public int Letters; public List<(string style, string text)> Paras = new(); }

        struct Line { public float Y, X0, X1, Size; public StringBuilder Text; }

        /// The text of page i (0-based), as paragraphs, with a verdict on whether it can be trusted.
        public PageText Page(int i)
        {
            var res = new PageText();
            var page = pages[i];
            var lines = new List<Line>(); bool unreliable = false;
            try { RunContent(page, Resolve(page.GetValueOrDefault("Resources")) as PdfDict, lines, ref unreliable, 0); }
            catch (Exception) { unreliable = true; }
            // drop running heads' page numbers: a line that is only a number
            lines.RemoveAll(l => System.Text.RegularExpressions.Regex.IsMatch(l.Text.ToString().Trim(), @"^[\divxlcIVXLC\-– ]{1,8}$"));
            var all = string.Join("\n", lines.Select(l => l.Text.ToString()));
            int letters = all.Count(char.IsLetter), visible = all.Count(c => !char.IsWhiteSpace(c)), bad = all.Count(c => c == '�' || char.IsControl(c) && c != '\n' || (c >= '' && c <= ''));
            res.Letters = letters; res.Text = all;
            res.Reliable = !unreliable && letters >= 12 && visible > 0 && letters >= visible * 0.55f && bad <= visible * 0.03f;
            if (res.Reliable) res.Paras = Paragraphs(lines);
            return res;
        }

        /// Lines into paragraphs: a paragraph ends at a wider gap than the usual line spacing, or after a line that ends a
        /// sentence well short of the column's right edge. A hyphen at a line's end joins the word.
        static List<(string, string)> Paragraphs(List<Line> lines)
        {
            var outp = new List<(string, string)>(); if (lines.Count == 0) return outp;
            var gaps = new List<float>(); for (int k = 1; k < lines.Count; k++) { float g = lines[k - 1].Y - lines[k].Y; if (g > 0) gaps.Add(g); }
            gaps.Sort(); float usual = gaps.Count > 0 ? gaps[gaps.Count / 2] : 12f;
            float right = lines.Max(l => l.X1), left = lines.Min(l => l.X0), width = Math.Max(1, right - left);
            var sb = new StringBuilder();
            for (int k = 0; k < lines.Count; k++)
            {
                var t = lines[k].Text.ToString().Trim(); if (t.Length == 0) continue;
                if (sb.Length > 0)
                {
                    var prev = lines[k - 1]; float gap = prev.Y - lines[k].Y; var pt = sb.ToString();
                    bool shortEnd = prev.X1 < right - width * 0.18f && ".!?:”\"'’".IndexOf(pt[pt.Length - 1]) >= 0;
                    bool indent = lines[k].X0 > left + Math.Max(8, lines[k].Size * 0.9f) && shortEnd;
                    if (gap > usual * 1.45f || gap < -usual || shortEnd || indent) { outp.Add(("prose", pt)); sb.Clear(); }
                    else if (pt.EndsWith("-") && t.Length > 0 && char.IsLower(t[0])) sb.Length--;   // re-
                    else sb.Append(' ');                                                              // joined
                }
                sb.Append(t);
            }
            if (sb.Length > 0) outp.Add(("prose", sb.ToString()));
            return outp;
        }

        void RunContent(PdfDict owner, PdfDict res, List<Line> lines, ref bool unreliable, int depth)
        {
            var c = Resolve(owner.GetValueOrDefault("Contents"));
            var chunks = new List<byte[]>();
            if (owner.Stream != null && depth > 0) chunks.Add(Decode(owner));           // a form XObject is its own content
            else if (c is PdfDict cd) chunks.Add(Decode(cd));
            else if (c is List<object> cl) foreach (var x in cl) if (Resolve(x) is PdfDict xd) chunks.Add(Decode(xd));
            if (chunks.Any(x => x == null)) unreliable = true;
            var bytes = chunks.Where(x => x != null).SelectMany(x => x.Concat(new byte[] { 10 })).ToArray();
            Interpret(bytes, res, lines, ref unreliable, depth);
        }

        void Interpret(byte[] b, PdfDict res, List<Line> lines, ref bool unreliableOut, int depth)
        {
            bool unreliable = unreliableOut;   // local functions cannot capture a ref parameter
            var fontsRes = Resolve(res?.GetValueOrDefault("Font")) as PdfDict;
            var xobjs = Resolve(res?.GetValueOrDefault("XObject")) as PdfDict;
            var ops = new List<object>(); int pos = 0;
            Font font = null; float size = 10, leading = 0, charSp = 0, wordSp = 0, hScale = 1;
            float[] tm = { 1, 0, 0, 1, 0, 0 }, tlm = { 1, 0, 0, 1, 0, 0 };
            // the graphics transform: producers that draw in a flipped or scaled space (Chrome's Skia, for one) place their
            // text through it, so positions are taken in page space (text matrix x transform)
            float[] ctm = { 1, 0, 0, 1, 0, 0 }; var stack = new Stack<float[]>();
            Line cur = default; bool have = false; float curX = 0;
            (float x, float y, float scale) Here() { var m = Mul(tm, ctm); return (m[4], m[5], (float)Math.Sqrt(m[0] * m[0] + m[1] * m[1])); }
            void NewLineIfMoved(float x, float y, float fs)
            {
                if (have && Math.Abs(cur.Y - y) <= Math.Max(1.5f, fs * 0.45f)) return;
                if (have) lines.Add(cur);
                cur = new Line { Y = y, X0 = x, X1 = x, Size = fs, Text = new StringBuilder() }; have = true; curX = x;
            }
            void Show(byte[] s)
            {
                if (font == null) { unreliable = true; return; }
                if (!font.Reliable) unreliable = true;
                var (x, y, scale) = Here(); float fs = size * (scale > 0 ? scale : 1);
                NewLineIfMoved(x, y, fs);
                if (x > curX + fs * 0.22f && cur.Text.Length > 0 && cur.Text[^1] != ' ') cur.Text.Append(' ');   // a gap on the line: a space
                int step = font.TwoByte ? 2 : 1;
                for (int k = 0; k + step - 1 < s.Length; k += step)
                {
                    int code = step == 2 ? (s[k] << 8) | s[k + 1] : s[k];
                    if (font.Map != null && font.Map.TryGetValue(code, out var t)) cur.Text.Append(t);
                    else if (!font.TwoByte && code >= 32 && code < 127) cur.Text.Append((char)code);
                    else if (font.Map != null && font.Map.Count > 0) cur.Text.Append('�');
                    float w = font.Widths.TryGetValue(code, out var ww) ? ww : font.DefaultWidth;
                    float adv = (w / 1000f * size + charSp + (code == 32 && step == 1 ? wordSp : 0)) * hScale;
                    tm[4] += adv * tm[0]; tm[5] += adv * tm[1];
                }
                curX = Here().x; cur.X1 = Math.Max(cur.X1, curX);
            }
            void Td(float tx, float ty) { tlm = Mul(new float[] { 1, 0, 0, 1, tx, ty }, tlm); tm = (float[])tlm.Clone(); }
            float F(int k) => ops.Count > k && ops[k] is double d ? (float)d : 0f;

            while (pos < b.Length)
            {
                object o;
                try { o = ParseObjectIn(b, ref pos); } catch { break; }
                if (!(o is PdfOp op)) { if (o != null || pos < b.Length) ops.Add(o); continue; }
                switch (op.V)
                {
                    case "BT": tm = new float[] { 1, 0, 0, 1, 0, 0 }; tlm = (float[])tm.Clone(); break;
                    case "q": stack.Push((float[])ctm.Clone()); break;
                    case "Q": if (stack.Count > 0) ctm = stack.Pop(); break;
                    case "cm": if (ops.Count >= 6) ctm = Mul(new[] { F(0), F(1), F(2), F(3), F(4), F(5) }, ctm); break;
                    case "Tf": if (ops.Count >= 2 && ops[0] is PdfName fn) { font = LoadFont(Resolve(fontsRes?.GetValueOrDefault(fn.V)) as PdfDict); size = F(1); } break;
                    case "Tc": charSp = F(0); break;
                    case "Tw": wordSp = F(0); break;
                    case "Tz": hScale = F(0) / 100f; break;
                    case "TL": leading = F(0); break;
                    case "Td": Td(F(0), F(1)); break;
                    case "TD": leading = -F(1); Td(F(0), F(1)); break;
                    case "Tm": if (ops.Count >= 6) { tlm = new[] { F(0), F(1), F(2), F(3), F(4), F(5) }; tm = (float[])tlm.Clone(); } break;
                    case "T*": Td(0, -leading); break;
                    case "Tj": if (ops.Count > 0 && ops[^1] is PdfString s1) Show(s1.B); break;
                    case "'": Td(0, -leading); if (ops.Count > 0 && ops[^1] is PdfString s2) Show(s2.B); break;
                    case "\"": wordSp = F(0); charSp = F(1); Td(0, -leading); if (ops.Count > 0 && ops[^1] is PdfString s3) Show(s3.B); break;
                    case "TJ":
                        if (ops.Count > 0 && ops[^1] is List<object> arr)
                            foreach (var e in arr)
                            {
                                if (e is PdfString es) Show(es.B);
                                else if (e is double kern)
                                {
                                    float adv = (float)(-kern / 1000f * size * hScale);
                                    tm[4] += adv * tm[0]; tm[5] += adv * tm[1];
                                    if (kern < -180 && have && cur.Text.Length > 0 && cur.Text[^1] != ' ') cur.Text.Append(' ');
                                    curX = Here().x;
                                }
                            }
                        break;
                    case "Do":
                        if (depth < 2 && ops.Count > 0 && ops[0] is PdfName xn && Resolve(xobjs?.GetValueOrDefault(xn.V)) is PdfDict xo && Name(xo, "Subtype") == "Form")
                        {
                            var xres = Resolve(xo.GetValueOrDefault("Resources")) as PdfDict ?? res;
                            var inner = Decode(xo); if (inner != null) { if (have) { lines.Add(cur); have = false; } Interpret(inner, xres, lines, ref unreliable, depth + 1); }
                        }
                        break;
                    case "BI":   // inline image: skip its bytes up to "EI"
                        { int ei = IndexOf(b, "EI", pos); while (ei > 0 && ei + 2 < b.Length && !IsDelimOrSpace(b[ei + 2])) ei = IndexOf(b, "EI", ei + 2); pos = ei < 0 ? b.Length : ei + 2; }
                        break;
                }
                ops.Clear();
            }
            if (have) lines.Add(cur);
            unreliableOut = unreliable;
        }

        static float[] Mul(float[] a, float[] m) => new[]
        {
            a[0] * m[0] + a[1] * m[2], a[0] * m[1] + a[1] * m[3],
            a[2] * m[0] + a[3] * m[2], a[2] * m[1] + a[3] * m[3],
            a[4] * m[0] + a[5] * m[2] + m[4], a[4] * m[1] + a[5] * m[3] + m[5],
        };
    }
}
