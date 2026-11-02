// An imported PDF becomes two things: the file itself, kept as it is so its pages can be shown with their own
// layout (PdfPages renders them), and, where the text can be read reliably, a Fable book whose chapters are the
// PDF's pages ("Page 12"), so highlighting, Define, Search and bookmarks work in the text view. A scanned or
// image-only PDF has no text chapters at all: it is read as pages, and the reader is told why the text features
// are missing. Nothing here pretends to OCR.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace Fable
{
    public static class PdfImport
    {
        public class Result { public Book Book; public int Pages, TextPages; public string Note; }

        public const long MaxPdfBytes = 150L << 20;

        public static Result Read(string path, string slug, string fileName, Action<string, float> progress)
        {
            progress?.Invoke("checking the file", -1);
            var len = new FileInfo(path).Length;
            if (len > MaxPdfBytes) throw new ImportException($"This PDF is {len / 1048576} MB; Fable imports PDFs up to {MaxPdfBytes / 1048576} MB.", "Split the PDF into parts, or reduce its image quality, and send it again.");
            var pdf = new PdfText(File.ReadAllBytes(path));
            try { pdf.Open(); }
            catch (ImportException) { throw; }
            catch (Exception e) { throw new ImportException($"This PDF could not be read ({e.GetType().Name}).", "The file may be damaged or cut short. Send it again, or try a different copy."); }
            int n = pdf.PageCount;
            if (n == 0) throw new ImportException("This PDF has no pages Fable can find.", "The file may be damaged. Try a different copy.");
            var drafts = new List<BookText.Draft>(); int text = 0;
            for (int i = 0; i < n; i++)
            {
                progress?.Invoke("reading pages", (float)i / n);
                PdfText.PageText pt;
                try { pt = pdf.Page(i); } catch { continue; }
                if (!pt.Reliable) continue;
                text++;
                var d = new BookText.Draft { Title = $"Page {i + 1}", PdfPage = i + 1 };
                foreach (var p in pt.Paras) d.Paras.Add(p);
                drafts.Add(d);
            }
            progress?.Invoke("splitting sentences", -1);
            var title = GoodTitle(pdf.Title) ?? BookText.TitleFromFileName(fileName);
            var author = string.IsNullOrWhiteSpace(pdf.Author) ? null : pdf.Author.Trim();
            var book = BookText.Build(slug, title, author, drafts, "pdf", n);
            string note = text == 0 ? "no text in this PDF (scanned or image pages): page view only"
                        : text < n ? $"text on {text} of {n} pages; the others are pages only"
                        : null;
            return new Result { Book = book, Pages = n, TextPages = book.Chapters.Count, Note = note };
        }

        /// The document's own title, unless it is a word processor's leftover ("Microsoft Word - draft3.docx", "untitled").
        static string GoodTitle(string t)
        {
            if (string.IsNullOrWhiteSpace(t)) return null;
            t = t.Trim();
            if (t.Length < 2 || Regex.IsMatch(t, @"^(untitled|microsoft word|document\d*$)|\.(docx?|pdf|indd|tex|odt|html?|txt|rtf)$", RegexOptions.IgnoreCase)) return null;
            return t;
        }
    }
}
