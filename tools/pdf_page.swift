// Fable editor helper: draw one page of a PDF to a PNG with PDFKit (macOS only), or count its pages.
// Used by unity/.../Library/PdfPages.cs in the editor so desktop previews show real PDF pages; on the headset
// Android's own PdfRenderer does this. Compiled on first use to out/pdfpage.
//   pdfpage <file.pdf> count
//   pdfpage <file.pdf> <page, 1-based> <width px> <out.png>
import AppKit
import Foundation
import PDFKit

let a = CommandLine.arguments
guard a.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])) else {
    FileHandle.standardError.write("the PDF could not be opened\n".data(using: .utf8)!); exit(2)
}
if doc.isLocked { FileHandle.standardError.write("the PDF is password-protected\n".data(using: .utf8)!); exit(4) }
if a[2] == "count" { print(doc.pageCount); exit(0) }
guard a.count >= 5, let n = Int(a[2]), let width = Double(a[3]), let page = doc.page(at: n - 1) else { exit(3) }
let box = page.bounds(for: .cropBox)
let rotated = page.rotation % 180 != 0
let pw = rotated ? box.height : box.width, ph = rotated ? box.width : box.height
let size = NSSize(width: width, height: (width * ph / pw).rounded())
let w = Int(size.width), h = Int(size.height)
guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                                 hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0),
      let ctx = NSGraphicsContext(bitmapImageRep: rep) else { exit(5) }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = ctx
let cg = ctx.cgContext
cg.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
cg.fill(CGRect(x: 0, y: 0, width: w, height: h))
cg.scaleBy(x: size.width / pw, y: size.height / ph)
page.draw(with: .cropBox, to: cg)   // applies the page's own rotation
NSGraphicsContext.restoreGraphicsState()
guard let png = rep.representation(using: .png, properties: [:]) else { exit(6) }
try png.write(to: URL(fileURLWithPath: a[4]))
