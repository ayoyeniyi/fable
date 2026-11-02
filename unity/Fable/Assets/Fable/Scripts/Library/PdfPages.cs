// Drawing a PDF's pages as they were laid out, for the page view. On the headset this is Android's own PDF renderer
// (android.graphics.pdf.PdfRenderer, part of the OS), reached through JNI; in the macOS editor it is PDFKit, through
// a tiny helper (tools/pdf_page.swift, compiled to out/pdfpage on first use) so desktop previews show real pages.
// Pages come back as textures with mipmaps (text stays clean when the page is seen at a distance). Main thread only.
using System;
using System.IO;
using UnityEngine;

namespace Fable
{
    public class PdfPages : IDisposable
    {
        public int Count { get; private set; }
        public string Error { get; private set; }
        readonly string path;
#if UNITY_ANDROID && !UNITY_EDITOR
        AndroidJavaObject renderer, pfd;
#endif

        PdfPages(string p) { path = p; }

        /// A page drawn with a CPU copy kept, so it can be saved as an image (the cover).
        public Texture2D RenderReadable(int i, int width) => Render(i, width, true);

        /// Open a PDF for drawing. Check Error (null when it opened).
        public static PdfPages Open(string path)
        {
            var pp = new PdfPages(path);
            try { pp.OpenNative(); }
            catch (Exception e) { pp.Error = e.Message; pp.Count = 0; }
            if (pp.Error == null && pp.Count <= 0) pp.Error = "no pages";
            return pp;
        }

#if UNITY_ANDROID && !UNITY_EDITOR
        void OpenNative()
        {
            using var file = new AndroidJavaObject("java.io.File", path);
            using var pfdClass = new AndroidJavaClass("android.os.ParcelFileDescriptor");
            pfd = pfdClass.CallStatic<AndroidJavaObject>("open", file, 0x10000000);   // MODE_READ_ONLY
            renderer = new AndroidJavaObject("android.graphics.pdf.PdfRenderer", pfd);  // throws on a protected or broken file
            Count = renderer.Call<int>("getPageCount");
        }

        /// Draw page i (0-based) at the given pixel width. Readable: keep a CPU copy (to save it as an image).
        public Texture2D Render(int i, int width, bool readable = false)
        {
            if (renderer == null || i < 0 || i >= Count) return null;
            using var page = renderer.Call<AndroidJavaObject>("openPage", i);
            int pw = page.Call<int>("getWidth"), ph = page.Call<int>("getHeight");
            int w = Mathf.Clamp(width, 64, 2048), h = Mathf.Clamp(Mathf.RoundToInt(w * ph / (float)Mathf.Max(1, pw)), 64, 2900);
            using var cfgClass = new AndroidJavaClass("android.graphics.Bitmap$Config");
            using var cfg = cfgClass.GetStatic<AndroidJavaObject>("ARGB_8888");
            using var bmpClass = new AndroidJavaClass("android.graphics.Bitmap");
            using var bmp = bmpClass.CallStatic<AndroidJavaObject>("createBitmap", w, h, cfg);
            bmp.Call("eraseColor", unchecked((int)0xFFFFFFFF));   // paper white under the page
            // render(Bitmap, Rect, Matrix, int) with null rect and matrix: through raw JNI, as nulls cannot pick an overload
            var cls = AndroidJNI.GetObjectClass(page.GetRawObject());
            var mid = AndroidJNI.GetMethodID(cls, "render", "(Landroid/graphics/Bitmap;Landroid/graphics/Rect;Landroid/graphics/Matrix;I)V");
            var args = new jvalue[4]; args[0].l = bmp.GetRawObject(); args[1].l = IntPtr.Zero; args[2].l = IntPtr.Zero; args[3].i = 1;   // RENDER_MODE_FOR_DISPLAY
            AndroidJNI.CallVoidMethod(page.GetRawObject(), mid, args);
            AndroidJNI.DeleteLocalRef(cls);
            page.Call("close");
            using var bufClass = new AndroidJavaClass("java.nio.ByteBuffer");
            using var buf = bufClass.CallStatic<AndroidJavaObject>("allocate", w * h * 4);
            bmp.Call("copyPixelsToBuffer", buf);
            var px = buf.Call<sbyte[]>("array");
            bmp.Call("recycle");
            // Android rows run top-down, Unity's bottom-up: copy them over in reverse order
            var bytes = new byte[px.Length]; int row = w * 4;
            for (int y = 0; y < h; y++) Buffer.BlockCopy(px, y * row, bytes, (h - 1 - y) * row, row);
            var tex = new Texture2D(w, h, TextureFormat.RGBA32, true) { name = "pdf page " + (i + 1), wrapMode = TextureWrapMode.Clamp, anisoLevel = 4 };
            tex.LoadRawTextureData(bytes); tex.Apply(true, !readable);
            return tex;
        }

        public void Dispose()
        {
            try { renderer?.Call("close"); } catch { }
            try { pfd?.Call("close"); } catch { }
            renderer?.Dispose(); pfd?.Dispose(); renderer = null; pfd = null;
        }
#else
        // The editor (macOS): PDFKit through out/pdfpage. Other desktops: no page images (the text view still works).
        static string Helper => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../out/pdfpage"));
        static string Source => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../tools/pdf_page.swift"));

        static string Run(params string[] args)
        {
            if (Application.platform != RuntimePlatform.OSXEditor) throw new Exception("page images need the headset (or the macOS editor)");
            if (!File.Exists(Helper) || File.GetLastWriteTimeUtc(Helper) < File.GetLastWriteTimeUtc(Source))
            {
                var c = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("/usr/bin/swiftc", $"-O \"{Source}\" -o \"{Helper}\"") { UseShellExecute = false, RedirectStandardError = true, CreateNoWindow = true });
                var err = c.StandardError.ReadToEnd(); c.WaitForExit();
                if (c.ExitCode != 0) throw new Exception("pdfpage helper did not compile: " + err);
            }
            var psi = new System.Diagnostics.ProcessStartInfo(Helper, string.Join(" ", Array.ConvertAll(args, a => "\"" + a.Replace("\"", "\\\"") + "\""))) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true };
            var p = System.Diagnostics.Process.Start(psi); var outp = p.StandardOutput.ReadToEnd(); var e2 = p.StandardError.ReadToEnd(); p.WaitForExit();
            if (p.ExitCode != 0) throw new Exception(string.IsNullOrWhiteSpace(e2) ? "the PDF could not be opened" : e2.Trim());
            return outp.Trim();
        }

        void OpenNative() { Count = int.Parse(Run(path, "count")); }

        public Texture2D Render(int i, int width, bool readable = false)
        {
            if (i < 0 || i >= Count) return null;
            var png = Path.Combine(Application.temporaryCachePath, $"pdfpage-{Guid.NewGuid():N}.png");
            try
            {
                Run(path, (i + 1).ToString(), Mathf.Clamp(width, 64, 2048).ToString(), png);
                var tex = new Texture2D(2, 2, TextureFormat.RGBA32, true) { name = "pdf page " + (i + 1), wrapMode = TextureWrapMode.Clamp, anisoLevel = 4 };
                tex.LoadImage(File.ReadAllBytes(png), false); tex.Apply(true, !readable);
                return tex;
            }
            catch (Exception e) { Error = e.Message; return null; }
            finally { try { File.Delete(png); } catch { } }
        }
        public void Dispose() { }
#endif
    }
}
