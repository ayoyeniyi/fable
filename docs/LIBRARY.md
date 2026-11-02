# The personal library and book uploads

The lobby is the reader's personal library. The four bundled books are always on it. Readers can add their own
books from a phone or computer without a cable, an account or any cloud service, and start reading while a book
imports.

## The library board

- **Where it is:** a lectern-height board in front of the reader in the lobby (`Scripts/Library/LibraryPanel.cs`).
- **What it shows:** every book, six to a page. Each tile has:
  - the cover, or a plain cloth cover drawn with the title when the book has none
  - the title and author
  - where the book came from: *Fable edition · own room*, *your EPUB*, *your PDF · 230 pages*, or *your PDF · pages only*
  - how far the reader has got
- **Controls:**
  - "continue: <book read last> ›" reopens the last book.
  - "‹ previous / next ›" turn through the shelf pages for a larger collection.
  - "+ add a book" opens the upload card.
  - Imported books have **remove**, which asks once ("sure?") before deleting.
- **Arriving books:** a book that is still arriving shows its stage and measured progress. A failed one says why, and
  pinching it gives the details.
- **Pointing:** the board claims its own pinches, so pointing at it never opens a book on the shelf behind it.
- **Recentre:** the view toolbar's *recentre* brings the board back in front of the reader. *face the shelf* turns
  them back to the bookcase.

## Sending a book

1. In the headset, point at **+ add a book** and pinch. The board shows the headset's address and a four-digit
   code, for example `http://192.168.1.23:8642` and `4831`.
2. On a phone or computer on the **same Wi-Fi**, open that address in a browser. The page is served by the headset
   itself (`Scripts/Library/UploadServer.cs`). It lists the formats Fable reads and the limits **before** you
   choose a file.
3. Type the code, choose the book, and press **Send to headset**.
4. The page shows two kinds of progress:
   - the transfer, as a real byte count and bar
   - the import's named stages: checking the file → reading chapters or pages → preparing the text → saving → on
     your shelf. Each stage shows a percentage where it can be measured (EPUB chapters, PDF pages).

   The headset board shows the same thing. Nothing invents a countdown or an estimated time.
5. The book appears on the board as soon as it is ready. A reader who has gone into another book sees a note on
   the view toolbar.

## Formats

| Format | What works | Limitations |
|---|---|---|
| **EPUB 2 and 3, DRM-free** | Full import: title, author, cover, chapters and their titles (from the nav document or the NCX, including several chapters in one file), paragraphs, headings, line breaks. Sentence ids are stable, so highlighting, Define, Search, bookmarks, text size and the saved place all work and survive restarts. | Footnotes, endnotes, illustrations and captions are left out, as are Standard Ebooks' imprint and colophon pages and Project Gutenberg's header and licence. Peek and Step In are greyed: there are no models or rooms for an imported book ("not for your books yet", "no room for this book"). Tables become plain paragraphs. |
| **PDF with real text** | **Page view:** the pages exactly as laid out, drawn by Android's own `PdfRenderer` on the headset (PDFKit in the macOS editor). **Text view** (the "text view ›" switch): the text of each page, reflowed, with highlighting, Define, Search and bookmarks. Switching views keeps the page. | Text sits one chapter per page, so a paragraph that runs over a page break is split. Multi-column layouts may interleave. You can't highlight on the page image itself; the page view says "highlight and search: text view". |
| **PDF with no text (scans, image-only)** | Page view, bookmarks, contents by tens of pages, the saved page. | No highlighting, Define or Search: the footer says "scanned pages: no text to highlight or search". **There is no OCR.** |
| Kindle (MOBI, AZW, AZW3, KFX), Word, RTF, plain text, comics, DjVu | Refused on the upload page before anything is sent, and again on the headset by content as well as name. Each refusal suggests what to do instead (for example "convert a DRM-free Kindle book to EPUB with Calibre", "export a Word document as PDF"). | Not supported in this build. |
| **DRM-protected EPUB or encrypted PDF** | Refused with an explanation. | Covers Adobe ADEPT (`rights.xml`), Apple (`sinf.xml`), and any `encryption.xml` that encrypts more than fonts. Encrypted PDFs (`/Encrypt`) are also refused. |

A PDF's text counts only when it can be trusted. A page needs:

- at least 12 letters
- at least 55% of its visible characters to be letters
- fewer than 3% replacement or private-use characters
- fonts that map to Unicode

Fonts that only carry glyph ids (CID fonts without a ToUnicode map) make that page "no text", and its words are
never guessed (`Scripts/Library/PdfText.cs`).

## Limits

| Limit | Value | Where |
|---|---|---|
| One file | 150 MB | `Library.MaxFileBytes` |
| All imported books | 2 GB | `Library.MaxLibraryBytes` |
| Imported books | 300 | `Library.MaxBooks` |
| Free space kept on the headset after an import | 300 MB (an import needs about 3x the file size while it works) | `Library.MinFreeBytes` |
| EPUB text | 96 MB of pages in all, 24 MB for any one part | `EpubImport` |

The upload page checks the size before sending. The headset checks every limit again from the request's
`Content-Length` before storing a single byte, and answers 413, 415 or 507 with a plain explanation and a fix.

## What can go wrong, and what happens

| Case | Behaviour |
|---|---|
| Duplicate | The same file, matched by SHA-256, is not added twice: "“Moby Dick” is already in your library". |
| Transfer interrupted (phone sleeps, Wi-Fi drops, tab closed) | "The transfer stopped after 12.3 of 40.0 MB (the connection closed). Nothing was added." The partial file is deleted. |
| Malformed or truncated file | For example: "This file isn't a readable EPUB: it is not a complete zip archive… send the file again". |
| Not enough storage | Refused before transfer, with the free and needed sizes. |
| Wrong code | Refused. Five wrong codes in a row change the code shown in the headset. |
| Board closed | Uploads are refused ("open + add a book in Fable's library first"). A transfer already under way finishes. |
| Fable closed mid-import | Leftovers in `.incoming/` and `.staging/` are deleted at the next start, and the board says an import was interrupted. |

**An unsuccessful import never damages the library.** Each import is assembled in `library/.staging/<slug>/` and
moved into place in one step only when it is complete. `library.json` is written beside the old one and swapped
in. If the index is ever unreadable, the complete book folders on disk are listed instead.

## Storage on the headset

Everything lives under `persistentDataPath/library/`:

| Path | Contents |
|---|---|
| `library.json` | the imported books' entries: title, author, format, size, SHA-256, pages, text pages, note |
| `<slug>/book.json` | the book in Fable's shape (chapters → paragraphs → sentences, ids `<slug>:c01.p004.s02`) |
| `<slug>/cover.jpg` or `<slug>/cover.png` | the cover |
| `<slug>/source.pdf` | a PDF, kept as sent, for the page view |

A slug is `u-` plus the first 12 hex digits of the file's SHA-256, so it is stable across reinstalls of the same
file.

Reading place, furthest point (the spoiler limit for Search), bookmarks, text size and the PDF view live in
`progress.json` alongside the bundled books'. The reader's preferences live there too: turn step, page size and the
hints already shown. Both files are written beside and swapped in.

## Where imported books are read

`LibraryRoom`: the lobby's panelled room, lit and sounding the same, built by `FableBuild` from the lobby model in
room mode (`SceneDef library-room`). It has no staged passages and no Step In. Reading never waits for generated
scenes or environments.

## Safety

- **Plain HTTP on the local network only:** no internet exposure, no accounts, no third-party service.
- **Gated uploads:** an upload needs the four-digit code shown in the headset, and is only accepted while
  "+ add a book" is open.
- **Checks before reading:**
  - Files are checked by size before transfer and by content after it.
  - EPUB parts and the total text are capped against zip bombs.
  - PDF streams decompress to at most 64 MB each.
- **Nothing is executed:** EPUB XHTML is tokenised as text. Scripts, styles and SVG are dropped, never run.
