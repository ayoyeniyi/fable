// Turning imported text into Fable's book shape: chapters -> paragraphs -> sentences with stable ids, the same shape
// and id scheme tools/ingest_book.py gives the four bundled books (<slug>:c01.p004.s02). Ids depend only on the text
// and its order, so importing the same file again gives the same ids, and highlights, bookmarks, Search and the saved
// place all keep working across restarts. The sentence rule is the ingester's: a break needs terminal punctuation,
// optional closing quotes, whitespace, then a capital (or an opening quote before one).
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;

namespace Fable
{
    public static class BookText
    {
        /// One chapter before it becomes a Book.Chapter: a title and its paragraphs (style, text).
        public class Draft
        {
            public string Title;
            public int PdfPage;
            public readonly List<(string style, string text)> Paras = new();
        }

        const char Dot = '․';   // a full stop that does not end a sentence (abbreviations), restored afterwards
        static readonly string[] Abbreviations = { "Mr", "Mrs", "Messrs", "Ms", "Dr", "St", "Capt", "Col", "Gen", "Lieut", "Sir", "Rev", "Mt", "vol", "viz", "ch", "i.e", "e.g", "etc", "cf", "ibid", "Esq", "Prof", "Jr", "Sr", "vs", "fig", "Fig" };
        static readonly Regex AbbrRe = new(@"\b(" + string.Join("|", System.Array.ConvertAll(Abbreviations, Regex.Escape)) + @")\.(?=\s|$)", RegexOptions.Compiled);
        static readonly Regex InitialRe = new(@"\b([A-HJ-Z])\.(?=\s?[A-Z])", RegexOptions.Compiled);
        static readonly Regex NumberRe = new(@"\b(No|pp?)\.(?=\s?\d)", RegexOptions.Compiled);   // No. 7, p. 12; but "No. If..." is a sentence
        const string Openers = "“‘\"'([", Closers = "”’\"')]";
        static readonly Regex SplitRe = new(@"([.!?…]+[" + Cls(Closers) + @"]*)(\s+)(?=[" + Cls(Openers) + @"]*[\p{Lu}0-9])", RegexOptions.Compiled);
        /// Characters for a [...] class: Regex.Escape leaves "]" alone, which would close the class early.
        static string Cls(string chars) => Regex.Escape(chars).Replace("]", @"\]");
        static readonly Regex Spaces = new(@"[ \t\r\f\v    ]+", RegexOptions.Compiled);

        /// Whitespace normalised, invisible joiners removed, line breaks kept (verse), ends trimmed.
        public static string Clean(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            s = s.Replace("﻿", "").Replace("⁠", "").Replace("­", "").Replace("​", "");
            s = Spaces.Replace(s, " ");
            s = Regex.Replace(s, @" *\n *", "\n");
            s = Regex.Replace(s, @"\n{2,}", "\n");
            return s.Trim();
        }

        /// A paragraph's sentences, each with whether a line break came before it.
        public static List<(string text, bool lineBefore)> Sentences(string text)
        {
            var s = AbbrRe.Replace(text, m => m.Groups[1].Value + Dot);
            s = InitialRe.Replace(s, m => m.Groups[1].Value + Dot);
            s = NumberRe.Replace(s, m => m.Groups[1].Value + Dot);
            var parts = new List<(string, bool)>(); int last = 0; bool brk = false;
            foreach (Match m in SplitRe.Matches(s))
            {
                parts.Add((s.Substring(last, m.Groups[1].Index + m.Groups[1].Length - last), brk));
                brk = m.Groups[2].Value.Contains("\n");
                last = m.Groups[2].Index + m.Groups[2].Length;
            }
            parts.Add((s.Substring(last), brk));
            var outp = new List<(string, bool)>();
            foreach (var (p0, b) in parts)
            {
                var p = p0.Replace(Dot, '.').Trim();
                if (p.Length == 0) continue;
                if (outp.Count > 0 && p.Length < 3) { var (t, lb) = outp[^1]; outp[^1] = (t + p, lb); }   // stray punctuation joins the previous sentence
                else outp.Add((p, b));
            }
            return outp;
        }

        /// Build the Book from drafts. Chapters with no text are dropped; ids follow the bundled books' scheme.
        public static Book Build(string slug, string title, string author, IList<Draft> drafts, string format, int pdfPages = 0)
        {
            var book = new Book { Slug = slug, Title = title, Author = author, Format = format, PdfPages = pdfPages };
            int nc = 0;
            foreach (var d in drafts)
            {
                var paras = new List<Book.Paragraph>();
                string cid = $"c{nc + 1:00}";
                foreach (var (style, raw) in d.Paras)
                {
                    var text = Clean(raw); if (text.Length == 0) continue;
                    var pid = $"{slug}:{cid}.p{paras.Count + 1:000}";
                    var para = new Book.Paragraph { Id = pid, Style = style };
                    var sb = style == "heading" ? new List<(string, bool)> { (text.Replace('\n', ' '), false) } : Sentences(text);
                    for (int i = 0; i < sb.Count; i++)
                        para.Sentences.Add(new Book.Sentence { Id = $"{pid}.s{i + 1:00}", Text = sb[i].Item1, LineBefore = sb[i].Item2 && i > 0 });
                    if (para.Sentences.Count > 0) paras.Add(para);
                }
                if (paras.Count == 0) continue;
                nc++;
                book.Chapters.Add(new Book.Chapter { Id = $"{slug}:{cid}", Index = book.Chapters.Count, Kind = "chapter", Title = string.IsNullOrWhiteSpace(d.Title) ? $"Section {nc}" : Clean(d.Title).Replace('\n', ' '), Paragraphs = paras, PdfPage = d.PdfPage });
            }
            book.Index();
            return book;
        }

        /// A short readable title from a file name: "moby-dick_by_melville.epub" -> "Moby dick by melville".
        public static string TitleFromFileName(string name)
        {
            var t = System.IO.Path.GetFileNameWithoutExtension(name ?? "") ?? "";
            t = Regex.Replace(t, @"[_\-\.]+", " ").Trim();
            if (t.Length == 0) return "Untitled book";
            return char.ToUpperInvariant(t[0]) + t.Substring(1);
        }

        public static int Words(Book b) { int n = 0; foreach (var c in b.Chapters) foreach (var p in c.Paragraphs) foreach (var s in p.Sentences) n += s.Text.Split(' ').Length; return n; }

        public static string Sha256(string path)
        {
            using var f = System.IO.File.OpenRead(path); using var h = System.Security.Cryptography.SHA256.Create();
            var sb = new StringBuilder(); foreach (var b in h.ComputeHash(f)) sb.Append(b.ToString("x2")); return sb.ToString();
        }
    }
}
