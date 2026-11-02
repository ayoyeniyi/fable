// Reading a DRM-free EPUB (2 or 3) into Fable's book shape, on a background thread, with no outside libraries.
//
//   META-INF/container.xml  -> the package (OPF): title, author, the reading order (spine), the cover image
//   the table of contents   -> chapter titles (EPUB 3 nav document, else the EPUB 2 NCX)
//   each spine document     -> paragraphs: block elements (p, div, h1-h6, li, blockquote...) become paragraphs,
//                              headings keep a "heading" style, <br> is a line break; scripts, styles, footnote and
//                              endnote asides, and note-reference marks are dropped
//
// A spine document that the table of contents names (or that opens with a heading) starts a chapter; one that does
// not continues the chapter before it, since publishers often split a chapter across files. Protected books are
// refused: an encryption.xml that encrypts anything but fonts, or Adobe (rights.xml) or Apple (sinf.xml) DRM files.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

namespace Fable
{
    public class ImportException : Exception
    {
        /// What the reader can do about it, in plain words.
        public readonly string Recovery;
        public ImportException(string message, string recovery) : base(message) { Recovery = recovery; }
    }

    public static class EpubImport
    {
        public class Result { public Book Book; public byte[] Cover; public string CoverExt; public string Note; }

        const long MaxEntryBytes = 24L << 20, MaxTextBytes = 96L << 20, MaxCoverBytes = 10L << 20;

        public static bool LooksLikeEpub(string path)
        {
            try
            {
                using var z = ZipFile.OpenRead(path);
                var mt = z.GetEntry("mimetype");
                if (mt != null) { using var r = new StreamReader(mt.Open()); if (r.ReadToEnd().Trim() == "application/epub+zip") return true; }
                return z.GetEntry("META-INF/container.xml") != null;
            }
            catch { return false; }
        }

        public static Result Read(string path, string slug, Action<string, float> progress)
        {
            ZipArchive zip;
            try { zip = ZipFile.OpenRead(path); }
            catch (Exception) { throw new ImportException("This file isn't a readable EPUB: it is not a complete zip archive. It may be damaged, or the transfer may have been cut short.", "Send the file again. If it still fails, try a different copy of the book."); }
            using (zip)
            {
                progress?.Invoke("checking the file", -1);
                CheckDrm(zip);
                var container = Entry(zip, "META-INF/container.xml") ?? throw new ImportException("This EPUB is missing its table of parts (META-INF/container.xml), so it can't be read.", "The file is probably damaged. Try a different copy of the book.");
                var cdoc = Xml(container);
                var opfPath = cdoc.GetElementsByTagName("rootfile").Cast<XmlElement>().Select(e => e.GetAttribute("full-path")).FirstOrDefault(p => !string.IsNullOrEmpty(p))
                    ?? throw new ImportException("This EPUB doesn't say where its contents are.", "The file is probably damaged. Try a different copy of the book.");
                var opfText = Entry(zip, opfPath) ?? throw new ImportException($"This EPUB's package file ({opfPath}) is missing.", "The file is probably damaged. Try a different copy of the book.");
                var opf = Xml(opfText);
                var baseDir = Dir(opfPath);

                string title = Clean(First(opf, "title")), author = Clean(First(opf, "creator"));
                var manifest = new Dictionary<string, (string href, string type, string props)>();
                foreach (var e in opf.GetElementsByTagName("*").Cast<XmlElement>().Where(e => e.LocalName == "item"))
                    manifest[e.GetAttribute("id")] = (Join(baseDir, Uri.UnescapeDataString(e.GetAttribute("href"))), e.GetAttribute("media-type"), e.GetAttribute("properties"));
                var spine = opf.GetElementsByTagName("*").Cast<XmlElement>().Where(e => e.LocalName == "itemref" && e.GetAttribute("linear") != "no")
                    .Select(e => e.GetAttribute("idref")).Where(manifest.ContainsKey).Select(id => manifest[id])
                    .Where(m => m.type.Contains("html") || m.href.EndsWith(".html") || m.href.EndsWith(".xhtml") || m.href.EndsWith(".htm")).ToList();
                if (spine.Count == 0) throw new ImportException("This EPUB has no readable chapters in its reading order.", "The file may be damaged or may not be a book. Try a different copy.");

                // chapter titles by document, and by anchor inside a document (one file often holds several chapters)
                var toc = new List<(string href, string frag, string title)>();
                var nav = manifest.Values.FirstOrDefault(m => (" " + m.props + " ").Contains(" nav "));
                if (nav.href != null) { var t = Entry(zip, nav.href); if (t != null) NavTitles(t, Dir(nav.href), toc); }
                if (toc.Count == 0)
                {
                    var ncx = manifest.Values.FirstOrDefault(m => m.type == "application/x-dtbncx+xml");
                    if (ncx.href != null) { var t = Entry(zip, ncx.href); if (t != null) NcxTitles(t, Dir(ncx.href), toc); }
                }

                var drafts = new List<BookText.Draft>(); long textBytes = 0;
                for (int i = 0; i < spine.Count; i++)
                {
                    progress?.Invoke("reading chapters", (float)i / spine.Count);
                    var doc = spine[i];
                    if ((" " + doc.props + " ").Contains(" nav ")) continue;   // the contents page itself
                    var html = Entry(zip, doc.href); if (html == null) continue;
                    textBytes += html.Length; if (textBytes > MaxTextBytes) throw new ImportException("This EPUB holds more text than Fable can import (over 96 MB of pages).", "Split the book into volumes, or choose a smaller edition.");
                    if (Furniture(html)) continue;   // title page, imprint, colophon, licence, list of illustrations
                    var here = toc.Where(t => t.href == doc.href).ToList();
                    var anchors = new HashSet<string>(here.Where(t => t.frag != null).Select(t => t.frag));
                    var items = Paragraphs(html, anchors);
                    // the file's start: a chapter if the contents names the file itself (or it opens with a heading)
                    // (an entry whose anchor never appears, say inside a skipped licence, names nothing: it is ignored)
                    var whole = here.FirstOrDefault(t => t.frag == null);
                    string heading = items.Count > 0 && items[0].style == "heading" ? items[0].text : null;
                    BookText.Draft cur = null;
                    if (whole.title != null || heading != null || drafts.Count == 0) { cur = new BookText.Draft { Title = whole.title ?? heading }; drafts.Add(cur); }
                    else cur = drafts[^1];   // no title of its own: the chapter before it goes on
                    foreach (var (style, text) in items)
                    {
                        if (style == "@")
                        {
                            var t = here.First(x => x.frag == text);
                            if (cur.Paras.Count == 0 && cur.Title == null) cur.Title = t.title;
                            else if (cur.Paras.Count == 0) cur.Title = t.title;
                            else { cur = new BookText.Draft { Title = t.title }; drafts.Add(cur); }
                            continue;
                        }
                        // a chapter's own heading (or its number and name) repeats its title: keep the title, drop the repeat
                        if (cur.Paras.Count < 3 && cur.Title != null && cur.Paras.TrueForAll(pp => Same(pp.text, cur.Title)) && Same(text, cur.Title)) { cur.Paras.Add(("@drop", text)); continue; }
                        cur.Paras.Add((style, text));
                    }
                }
                foreach (var d in drafts) d.Paras.RemoveAll(pp => pp.style == "@drop");
                if (drafts.Count > 0 && drafts[0].Title == null) drafts[0].Title = "Opening pages";
                progress?.Invoke("splitting sentences", -1);
                if (string.IsNullOrWhiteSpace(title)) title = BookText.TitleFromFileName(path);
                var book = BookText.Build(slug, title, string.IsNullOrWhiteSpace(author) ? null : author, drafts, "epub");
                if (book.SentenceCount == 0) throw new ImportException("This EPUB has no text Fable can read: its pages may be images only.", "Fable reads text EPUBs. A picture book or comic EPUB can't be shown yet.");

                var res = new Result { Book = book };
                var cover = CoverHref(opf, manifest, zip);
                if (cover != null)
                {
                    var e = zip.GetEntry(cover);
                    if (e != null && e.Length > 0 && e.Length < MaxCoverBytes)
                    {
                        using var s = e.Open(); using var ms = new MemoryStream(); s.CopyTo(ms); var bytes = ms.ToArray();
                        var ext = Sniff(bytes);
                        if (ext != null) { res.Cover = bytes; res.CoverExt = ext; }
                    }
                }
                if (res.Cover == null) res.Note = "no cover image in the file";
                return res;
            }
        }

        // ---------------------------------------------------------------- DRM

        static void CheckDrm(ZipArchive zip)
        {
            const string recovery = "Fable can only open DRM-free books. Many stores (and Standard Ebooks, Project Gutenberg) sell or give DRM-free EPUBs.";
            if (zip.GetEntry("META-INF/rights.xml") != null) throw new ImportException("This EPUB is protected by Adobe DRM, so Fable can't open it.", recovery);
            if (zip.GetEntry("META-INF/sinf.xml") != null) throw new ImportException("This EPUB is protected by Apple Books DRM, so Fable can't open it.", recovery);
            var enc = Entry(zip, "META-INF/encryption.xml");
            if (enc == null) return;
            // font obfuscation (IDPF and Adobe's) is allowed: it scrambles fonts, not text
            foreach (Match m in Regex.Matches(enc, @"Algorithm\s*=\s*[""']([^""']+)[""']"))
            {
                var alg = m.Groups[1].Value;
                if (alg.Contains("idpf.org/2008/embedding") || alg.Contains("ns.adobe.com/pdf/enc#RC")) continue;
                throw new ImportException("This EPUB is encrypted (DRM), so Fable can't open it.", recovery);
            }
        }

        // ---------------------------------------------------------------- zip and xml helpers

        static string Entry(ZipArchive zip, string path)
        {
            var e = zip.GetEntry(path) ?? zip.Entries.FirstOrDefault(x => string.Equals(x.FullName, path, StringComparison.OrdinalIgnoreCase));
            if (e == null) return null;
            if (e.Length > MaxEntryBytes) throw new ImportException($"A part of this EPUB ({Path.GetFileName(path)}) is too large to read.", "The file may be damaged. Try a different copy of the book.");
            try { using var s = e.Open(); using var r = new StreamReader(s, Encoding.UTF8, true); return r.ReadToEnd(); }
            catch (InvalidDataException) { throw new ImportException($"A part of this EPUB ({Path.GetFileName(path)}) is damaged.", "Send the file again. If it still fails, try a different copy of the book."); }
        }

        static XmlDocument Xml(string text)
        {
            var doc = new XmlDocument { XmlResolver = null };
            var settings = new XmlReaderSettings { DtdProcessing = DtdProcessing.Ignore, XmlResolver = null };
            try { using var r = XmlReader.Create(new StringReader(text), settings); doc.Load(r); }
            catch (XmlException e) { throw new ImportException($"This EPUB's package file is not well formed ({e.Message}).", "The file is probably damaged. Try a different copy of the book."); }
            return doc;
        }

        static string First(XmlDocument d, string local) => d.GetElementsByTagName("*").Cast<XmlElement>().FirstOrDefault(e => e.LocalName == local)?.InnerText;
        static string Clean(string s) => s == null ? null : Regex.Replace(s, @"\s+", " ").Trim();
        static string Dir(string p) { int i = p.LastIndexOf('/'); return i < 0 ? "" : p.Substring(0, i + 1); }

        static string Join(string dir, string rel)
        {
            rel = rel.Split('#')[0];
            var parts = new List<string>((dir + rel).Split('/'));
            for (int i = 0; i < parts.Count; i++)
            {
                if (parts[i] == "." || parts[i] == "") { parts.RemoveAt(i); i--; }
                else if (parts[i] == ".." ) { parts.RemoveAt(i); if (i > 0) { parts.RemoveAt(i - 1); i--; } i--; }
            }
            return string.Join("/", parts);
        }

        static bool Same(string a, string b)
        {
            if (a == null || b == null) return false;
            string N(string s) => Regex.Replace(s.ToLowerInvariant(), @"[^\p{L}\p{N}]+", " ").Trim();
            var x = N(a); var y = N(b);
            return x.Length > 0 && y.Length > 0 && (x == y || x.Contains(y) || y.Contains(x));
        }

        static string Sniff(byte[] b)
        {
            if (b.Length > 3 && b[0] == 0xFF && b[1] == 0xD8) return ".jpg";
            if (b.Length > 8 && b[0] == 0x89 && b[1] == 0x50 && b[2] == 0x4E && b[3] == 0x47) return ".png";
            return null;   // GIF, WebP, SVG: Fable draws a cover of its own instead
        }

        // ---------------------------------------------------------------- table of contents

        static (string href, string frag) Split(string dir, string href)
        {
            href = Uri.UnescapeDataString(href); int h = href.IndexOf('#');
            return (Join(dir, h < 0 ? href : href.Substring(0, h)), h < 0 || h == href.Length - 1 ? null : href.Substring(h + 1));
        }

        static void AddToc(List<(string href, string frag, string title)> into, string dir, string href, string title)
        {
            title = Clean(WebUtility.HtmlDecode(Regex.Replace(title, "<[^>]+>", " ")));
            if (string.IsNullOrEmpty(title)) return;
            var (h, f) = Split(dir, href);
            if (!into.Any(t => t.href == h && t.frag == f)) into.Add((h, f, title));
        }

        static void NavTitles(string html, string dir, List<(string href, string frag, string title)> into)
        {
            // the <nav epub:type="toc"> block, else the first <nav>
            var m = Regex.Match(html, @"<nav[^>]*epub:type\s*=\s*[""'][^""']*\btoc\b[^""']*[""'][^>]*>(.*?)</nav>", RegexOptions.Singleline | RegexOptions.IgnoreCase);
            if (!m.Success) m = Regex.Match(html, @"<nav[^>]*>(.*?)</nav>", RegexOptions.Singleline | RegexOptions.IgnoreCase);
            if (!m.Success) return;
            foreach (Match a in Regex.Matches(m.Groups[1].Value, @"<a[^>]*href\s*=\s*[""']([^""']+)[""'][^>]*>(.*?)</a>", RegexOptions.Singleline | RegexOptions.IgnoreCase))
                AddToc(into, dir, a.Groups[1].Value, a.Groups[2].Value);
        }

        static void NcxTitles(string xml, string dir, List<(string href, string frag, string title)> into)
        {
            foreach (Match p in Regex.Matches(xml, @"<navLabel>\s*<text>(.*?)</text>\s*</navLabel>\s*<content[^>]*src\s*=\s*[""']([^""']+)[""']", RegexOptions.Singleline | RegexOptions.IgnoreCase))
                AddToc(into, dir, p.Groups[2].Value, p.Groups[1].Value);
        }

        /// Book furniture rather than the author's text (Standard Ebooks and EPUB 3 mark it with epub:type).
        static bool Furniture(string html)
        {
            // the types of the first few sectioning elements (Standard Ebooks: <body epub:type="frontmatter"><section epub:type="imprint">)
            var t = " ";
            foreach (Match m in Regex.Matches(html, @"<(?:section|body|div|article)[^>]*epub:type\s*=\s*[""']([^""']+)[""']", RegexOptions.IgnoreCase))
            { t += m.Groups[1].Value.ToLowerInvariant() + " "; if (m.Index > 4000) break; }
            if (t.Trim().Length == 0) return false;
            if (t.Contains(" chapter ") || t.Contains(" bodymatter ") && !t.Contains(" imprint ")) return false;
            foreach (var k in new[] { " imprint ", " colophon ", " copyright-page ", " titlepage ", " halftitlepage ", " loi ", " toc ", " endnotes ", " landmarks " }) if (t.Contains(k)) return true;
            return t.Contains("uncopyright");
        }

        static string CoverHref(XmlDocument opf, Dictionary<string, (string href, string type, string props)> manifest, ZipArchive zip)
        {
            foreach (var m in manifest.Values) if ((" " + m.props + " ").Contains(" cover-image ")) return m.href;   // EPUB 3
            var meta = opf.GetElementsByTagName("*").Cast<XmlElement>().FirstOrDefault(e => e.LocalName == "meta" && e.GetAttribute("name") == "cover");
            if (meta != null && manifest.TryGetValue(meta.GetAttribute("content"), out var c) && c.type.StartsWith("image/")) return c.href;   // EPUB 2
            foreach (var kv in manifest) if (kv.Key.ToLowerInvariant().Contains("cover") && kv.Value.type.StartsWith("image/")) return kv.Value.href;
            return null;
        }

        // ---------------------------------------------------------------- XHTML to paragraphs

        static readonly HashSet<string> Blocks = new() { "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre", "section", "article", "header", "footer", "figure", "figcaption", "tr", "dt", "dd", "table", "ul", "ol", "dl", "hr", "body", "main", "aside", "address", "center" };
        static readonly HashSet<string> Skip = new() { "head", "script", "style", "title", "svg", "math", "nav", "rt", "rp" };
        static readonly Regex Tag = new(@"<(/?)([a-zA-Z][a-zA-Z0-9:\-]*)([^>]*?)(/?)>", RegexOptions.Compiled);

        /// The document's paragraphs, in order: ("heading" | "prose", text), with ("@", id) where an element carrying one of
        /// `anchors` opens (a chapter the table of contents points into the middle of the file).
        public static List<(string style, string text)> Paragraphs(string html, HashSet<string> anchors = null)
        {
            html = Regex.Replace(html, @"<!--.*?-->", "", RegexOptions.Singleline);
            html = Regex.Replace(html, @"<!\[CDATA\[(.*?)\]\]>", "$1", RegexOptions.Singleline);
            html = Regex.Replace(html, @"<\?.*?\?>|<!DOCTYPE[^>]*>", "", RegexOptions.Singleline | RegexOptions.IgnoreCase);
            var outp = new List<(string, string)>(); var buf = new StringBuilder();
            string style = "prose"; int skipDepth = 0; string skipTag = null; int pos = 0;
            void Flush()
            {
                var t = BookText.Clean(WebUtility.HtmlDecode(buf.ToString()));
                if (t.Length > 0 && Regex.IsMatch(t, @"[\p{L}\p{N}]")) outp.Add((style, t));
                buf.Clear(); style = "prose";
            }
            foreach (Match m in Tag.Matches(html))
            {
                if (skipDepth == 0 && m.Index > pos) buf.Append(Regex.Replace(html.Substring(pos, m.Index - pos), @"\s+", " "));
                pos = m.Index + m.Length;
                bool close = m.Groups[1].Value == "/", selfClose = m.Groups[4].Value == "/";
                var name = m.Groups[2].Value.ToLowerInvariant(); if (name.Contains(":")) name = name.Substring(name.IndexOf(':') + 1);
                var attrs = m.Groups[3].Value;
                if (skipDepth > 0)
                {
                    if (name == skipTag) { if (close) skipDepth--; else if (!selfClose) skipDepth++; }
                    continue;
                }
                if (!close && anchors != null && anchors.Count > 0)
                {
                    var idm = Regex.Match(attrs, @"\b(?:id|name)\s*=\s*[""']([^""']+)[""']");
                    if (idm.Success && anchors.Remove(idm.Groups[1].Value)) { Flush(); outp.Add(("@", idm.Groups[1].Value)); }
                }
                if (!close && !selfClose && (Skip.Contains(name) || IsNote(name, attrs))) { skipTag = name; skipDepth = 1; continue; }
                if (name == "br") { buf.Append('\n'); continue; }
                if (Blocks.Contains(name))
                {
                    Flush();
                    if (!close && name.Length == 2 && name[0] == 'h' && char.IsDigit(name[1])) style = "heading";
                }
            }
            if (skipDepth == 0 && pos < html.Length) buf.Append(Regex.Replace(html.Substring(pos), @"\s+", " "));
            Flush();
            return outp;
        }

        /// Footnotes, endnotes and the little reference marks that point at them; illustrations and their captions.
        static bool IsNote(string name, string attrs)
        {
            if (name == "figure") return true;
            // Project Gutenberg's header and licence (the eBook's machine-readable boilerplate, not the author's text)
            if (Regex.IsMatch(attrs, @"\bid\s*=\s*[""']pg-(header|footer|machine-header|start-separator|end-separator)[""']") || attrs.Contains("pg-boilerplate")) return true;
            if (!attrs.Contains("type") && !attrs.Contains("role") && !attrs.Contains("class")) return false;
            var a = attrs.ToLowerInvariant();
            if (Regex.IsMatch(a, @"class\s*=\s*[""'][^""']*\b(caption|figcenter|figleft|figright|illus\w*|pagenum|page-?num)\b")) return true;
            if (name == "aside" && (a.Contains("footnote") || a.Contains("endnote") || a.Contains("rearnote"))) return true;
            if ((name == "a" || name == "sup") && (a.Contains("noteref") || a.Contains("doc-noteref") || a.Contains("footnote-ref"))) return true;
            return false;
        }
    }
}
