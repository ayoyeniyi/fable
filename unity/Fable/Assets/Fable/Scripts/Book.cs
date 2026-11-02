// A whole book as tools/ingest_book.py writes it (content/books/<slug>/book.json, copied to
// StreamingAssets/books/<slug>/book.json): chapters -> paragraphs -> sentences with stable ids.
using System.Collections.Generic;
using Newtonsoft.Json;

namespace Fable
{
    public class Book
    {
        public class Sentence
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("text")] public string Text;
            [JsonProperty("lineBefore")] public bool LineBefore;   // verse: starts a new line rather than following on
        }
        public class Paragraph
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("style")] public string Style;          // prose | verse | heading
            [JsonProperty("sentences")] public List<Sentence> Sentences = new();
        }
        public class Chapter
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("index")] public int Index;
            [JsonProperty("kind")] public string Kind;            // front | chapter
            [JsonProperty("label")] public string Label;          // I, II... (null for front matter)
            [JsonProperty("title")] public string Title;
            [JsonProperty("subtitle")] public string Subtitle;
            [JsonProperty("part")] public string Part;
            [JsonProperty("paragraphs")] public List<Paragraph> Paragraphs = new();
            /// A PDF's page this chapter's text comes from (1-based); 0 for books that are not PDFs.
            [JsonProperty("pdfPage")] public int PdfPage;

            /// "Chapter I", "Book IV", or the front matter's own title.
            public string Heading => Kind == "front" || string.IsNullOrEmpty(Label) ? Title : (Title != null && Title.EndsWith(" " + Label) ? Title : "Chapter " + Label);
            /// The chapter's name when it has one beyond its number ("Down the Rabbit-Hole").
            public string Name => Title != null && Title != Heading && !Title.EndsWith(" " + Label) ? Title : null;
        }

        [JsonProperty("slug")] public string Slug;
        [JsonProperty("title")] public string Title;
        [JsonProperty("author")] public string Author;
        [JsonProperty("translator")] public string Translator;
        [JsonProperty("year")] public int Year;
        [JsonProperty("chapters")] public List<Chapter> Chapters = new();
        /// "epub" for flowing text (the four bundled books and imported EPUBs), "pdf" for an imported PDF.
        [JsonProperty("format")] public string Format = "epub";
        /// PDF: how many pages the file has (pages with no extractable text have no chapter).
        [JsonProperty("pdfPages")] public int PdfPages;
        public bool IsPdf => Format == "pdf";

        // ---- lookups built once after loading

        /// Where a sentence sits: chapter, paragraph, sentence index, and its order in the whole book.
        public struct Locus { public int Chapter, Paragraph, Sentence, Ordinal; }
        readonly Dictionary<string, Locus> where = new();
        public int SentenceCount { get; private set; }

        public void Index()
        {
            where.Clear(); int n = 0;
            for (int c = 0; c < Chapters.Count; c++)
                for (int p = 0; p < Chapters[c].Paragraphs.Count; p++)
                    for (int s = 0; s < Chapters[c].Paragraphs[p].Sentences.Count; s++)
                        where[Chapters[c].Paragraphs[p].Sentences[s].Id] = new Locus { Chapter = c, Paragraph = p, Sentence = s, Ordinal = n++ };
            SentenceCount = n;
        }

        public bool TryFind(string sentenceId, out Locus l) { l = default; return sentenceId != null && where.TryGetValue(sentenceId, out l); }
        public int Ordinal(string sentenceId) => TryFind(sentenceId, out var l) ? l.Ordinal : -1;

        public static Book Parse(string json) { var b = JsonConvert.DeserializeObject<Book>(json); b.Index(); return b; }
    }
}
