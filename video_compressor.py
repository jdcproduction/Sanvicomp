"""
VideoPress - Compresseur video moderne
Dependances : pip install tkinterdnd2
Police     : placer Nunito-Regular.ttf et Nunito-Bold.ttf dans un dossier fonts/
Packaging Windows :
  pyinstaller --onefile --windowed \
    --add-binary "ffmpeg.exe;." \
    --add-data "fonts;fonts" \
    --hidden-import tkinterdnd2 \
    --collect-data tkinterdnd2 \
    --name "VideoPress" video_compressor.py
"""

import os, re, sys, threading, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ── Police ────────────────────────────────────────────────────────────────────

def resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

def load_fonts():
    try:
        reg  = resource_path(os.path.join("fonts", "Nunito-Regular.ttf"))
        bold = resource_path(os.path.join("fonts", "Nunito-Bold.ttf"))
        loaded = []
        if sys.platform == "win32":
            import ctypes
            for path in [reg, bold]:
                if os.path.isfile(path):
                    ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0)
                    loaded.append(path)
        elif sys.platform == "darwin":
            try:
                import ctypes, ctypes.util
                ct = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreText"))
                cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
                cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
                cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
                    ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
                ct.CTFontManagerRegisterFontsForURL.argtypes = [
                    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
                for path in [reg, bold]:
                    if os.path.isfile(path):
                        url = cf.CFURLCreateFromFileSystemRepresentation(
                            None, path.encode(), len(path), False)
                        ct.CTFontManagerRegisterFontsForURL(url, 1, None)
                        loaded.append(path)
            except Exception:
                pass
        return len(loaded) > 0
    except Exception:
        return False

NUNITO_LOADED = False

def F(size, weight="normal"):
    family = "Nunito" if NUNITO_LOADED else (
        "Avenir" if sys.platform == "darwin" else "Segoe UI"
    )
    return (family, size, weight)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":         "#F7F8FA",
    "surface":    "#FFFFFF",
    "border":     "#E4E7EC",
    "accent":     "#4F6EF7",
    "accent_h":   "#3B57D6",
    "text":       "#1A1D23",
    "subtext":    "#6B7280",
    "success_bg": "#ECFDF5",
    "success_fg": "#059669",
    "error_bg":   "#FEF2F2",
    "error_fg":   "#DC2626",
    "active_bg":  "#EFF2FF",
    "active_fg":  "#4F6EF7",
    "btn_sec":    "#F3F4F6",
    "btn_sec_h":  "#E5E7EB",
}

# ── Données ───────────────────────────────────────────────────────────────────
QUALITY_CRF = {
    "Haute  — qualite maximale": "20",
    "Moyenne — equilibre":       "28",
    "Faible  — fichier leger":   "36",
}
FORMATS = ["MP4", "MKV", "AVI", "MOV", "WEBM"]
FORMAT_CODEC = {
    "MP4":  ("libx264", "aac"),
    "MKV":  ("libx264", "aac"),
    "AVI":  ("libxvid", "mp3"),
    "MOV":  ("libx264", "aac"),
    "WEBM": ("libvpx-vp9", "libopus"),
}
RESOLUTIONS = {
    "Originale (ne pas modifier)": None,
    "1080p  — 1920x1080":         "1920:1080",
    "720p   — 1280x720":          "1280:720",
    "480p   — 854x480":           "854:480",
}
VIDEO_EXT = (
    ("Fichiers video", "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.ts *.mpg *.mpeg"),
    ("Tous les fichiers", "*.*"),
)
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_ffmpeg():
    if sys.platform == "win32":
        p = resource_path("ffmpeg.exe")
        if os.path.isfile(p):
            return p
    return "ffmpeg"

def parse_duration(text):
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", text)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + mi * 60 + s
    return 0

def parse_drop_paths(data):
    paths = []
    for token in re.findall(r'\{([^}]+)\}|(\S+)', data):
        p = token[0] or token[1]
        if p:
            paths.append(p)
    return paths

# ── Bouton plat simple ────────────────────────────────────────────────────────
class FlatButton(tk.Label):
    def __init__(self, parent, text, command, bg, fg, hover_bg, font, padx=14, pady=8, **kw):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font,
                         padx=padx, pady=pady, relief="flat", **kw)
        self._bg     = bg
        self._hover  = hover_bg
        self._cmd    = command
        self._active = True
        self.bind("<Enter>",    lambda e: self.config(bg=self._hover) if self._active else None)
        self.bind("<Leave>",    lambda e: self.config(bg=self._bg)    if self._active else None)
        self.bind("<Button-1>", lambda e: self._cmd()                  if self._active else None)

    def set_state(self, enabled):
        self._active = enabled
        self.config(bg=self._bg if enabled else C["border"],
                    fg=self._fg if enabled else C["subtext"])

# ── Application ───────────────────────────────────────────────────────────────
BaseClass = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk

class VideoCompressor(BaseClass):
    def __init__(self):
        global NUNITO_LOADED
        super().__init__()
        NUNITO_LOADED = load_fonts()

        self.title("VideoPress")
        self.resizable(False, False)
        self.configure(bg=C["bg"])

        self._quality    = tk.StringVar(value=list(QUALITY_CRF.keys())[1])
        self._format     = tk.StringVar(value="MP4")
        self._same_fmt   = tk.BooleanVar(value=True)
        self._resolution = tk.StringVar(value=list(RESOLUTIONS.keys())[0])
        self._status     = tk.StringVar(value="Glissez des videos ou cliquez sur Ajouter")

        self._queue      = []
        self._processing = False

        self._style_ttk()
        self._build_ui()
        self._refresh_fmt_state()

    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TProgressbar",
                    troughcolor=C["border"], background=C["accent"],
                    bordercolor=C["border"], lightcolor=C["accent"],
                    darkcolor=C["accent"], thickness=6)
        s.configure("TCombobox",
                    fieldbackground=C["surface"], background=C["surface"],
                    foreground=C["text"], selectbackground=C["accent"],
                    bordercolor=C["border"], arrowcolor=C["subtext"])
        s.map("TCombobox", fieldbackground=[("readonly", C["surface"])])

    def _build_ui(self):

        # ── Header ──
        header = tk.Frame(self, bg=C["surface"], padx=24, pady=20)
        header.pack(fill="x")
        tk.Label(header, text="VideoPress", font=F(26, "bold"),
                 bg=C["surface"], fg=C["text"]).pack(anchor="w")
        hint = "Glissez vos videos ici ou utilisez le bouton Ajouter" if DND_AVAILABLE \
               else "Utilisez le bouton Ajouter pour selectionner vos videos"
        tk.Label(header, text=hint, font=F(10),
                 bg=C["surface"], fg=C["subtext"]).pack(anchor="w", pady=(4, 0))

        self._div(self)

        # ── Zone fichiers ──
        ff = tk.Frame(self, bg=C["bg"], padx=20, pady=14)
        ff.pack(fill="x")

        wrap = tk.Frame(ff, bg=C["border"])
        wrap.pack(fill="x")
        inner = tk.Frame(wrap, bg=C["surface"], padx=1, pady=1)
        inner.pack(fill="x", padx=1, pady=1)

        self._listbox = tk.Listbox(
            inner, height=8, font=F(10),
            selectmode=tk.EXTENDED,
            bg=C["surface"], fg=C["text"],
            selectbackground=C["active_bg"], selectforeground=C["active_fg"],
            relief="flat", bd=0, highlightthickness=0, activestyle="none"
        )
        sb = tk.Scrollbar(inner, orient="vertical", command=self._listbox.yview,
                          relief="flat", bd=0)
        self._listbox.config(yscrollcommand=sb.set)
        self._listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        if DND_AVAILABLE:
            self._listbox.drop_target_register(DND_FILES)
            self._listbox.dnd_bind("<<Drop>>", self._on_drop)

        # Boutons fichiers
        br = tk.Frame(ff, bg=C["bg"])
        br.pack(fill="x", pady=(10, 0))
        for label, cmd in [("+ Ajouter", self._browse),
                            ("− Retirer", self._remove_selected),
                            ("✕ Effacer", self._clear_queue)]:
            FlatButton(br, text=label, command=cmd,
                       bg=C["btn_sec"], fg=C["text"], hover_bg=C["btn_sec_h"],
                       font=F(10), padx=12, pady=6
                       ).pack(side="left", padx=(0, 8))

        self._div(self)

        # ── Options ──
        opt = tk.Frame(self, bg=C["bg"], padx=20, pady=14)
        opt.pack(fill="x")
        opt.columnconfigure(1, weight=1)

        self._opt_row(opt, 0, "Qualite",
            ttk.Combobox(opt, textvariable=self._quality,
                         values=list(QUALITY_CRF.keys()), state="readonly", width=28))
        self._opt_row(opt, 1, "Resolution",
            ttk.Combobox(opt, textvariable=self._resolution,
                         values=list(RESOLUTIONS.keys()), state="readonly", width=28))

        fmt_f = tk.Frame(opt, bg=C["bg"])
        fmt_f.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        tk.Checkbutton(fmt_f, text="Conserver le format original",
                       variable=self._same_fmt, command=self._refresh_fmt_state,
                       bg=C["bg"], fg=C["text"], font=F(11),
                       activebackground=C["bg"], selectcolor=C["surface"],
                       relief="flat", bd=0).pack(side="left")
        self._fmt_label = tk.Label(fmt_f, text="  →  Format :",
                                   bg=C["bg"], fg=C["subtext"], font=F(11))
        self._fmt_label.pack(side="left")
        self._fmt_combo = ttk.Combobox(fmt_f, textvariable=self._format,
                                        values=FORMATS, state="readonly", width=8)
        self._fmt_combo.pack(side="left", padx=(4, 0))

        self._div(self)

        # ── Footer ──
        footer = tk.Frame(self, bg=C["surface"], padx=20, pady=18)
        footer.pack(fill="x")

        self._btn_compress = FlatButton(
            footer, text="Compresser tout",
            command=self._start_queue,
            bg=C["accent"], fg="white", hover_bg=C["accent_h"],
            font=F(13, "bold"), padx=22, pady=11
        )
        self._btn_compress.pack(side="left")

        prog = tk.Frame(footer, bg=C["surface"])
        prog.pack(side="left", fill="x", expand=True, padx=(18, 0))

        tk.Label(prog, textvariable=self._status,
                 bg=C["surface"], fg=C["subtext"],
                 font=F(10), anchor="w").pack(fill="x")

        bars = tk.Frame(prog, bg=C["surface"])
        bars.pack(fill="x", pady=(6, 0))

        self._pbar_current = ttk.Progressbar(bars, maximum=100,
                                              length=180, mode="determinate")
        self._pbar_current.pack(side="left")
        tk.Label(bars, text="  ", bg=C["surface"]).pack(side="left")
        self._pbar_total = ttk.Progressbar(bars, maximum=100,
                                            length=70, mode="determinate")
        self._pbar_total.pack(side="left")

        tk.Label(prog, text="video en cours  ·  total",
                 bg=C["surface"], fg=C["border"], font=F(8)).pack(anchor="w")

        # ── Credit ──
        self._div(self)
        tk.Label(self, text="Un outil fait par Jonathan Di Carlo",
                 bg=C["bg"], fg=C["border"], font=F(8)).pack(pady=(6, 8))

    def _div(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

    def _opt_row(self, parent, row, label, widget):
        tk.Label(parent, text=label, bg=C["bg"], fg=C["text"],
                 font=F(11)).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=6)
        widget.grid(row=row, column=1, sticky="w", pady=6)

    def _refresh_fmt_state(self):
        if self._same_fmt.get():
            self._fmt_combo.config(state="disabled")
            self._fmt_label.config(fg=C["border"])
        else:
            self._fmt_combo.config(state="readonly")
            self._fmt_label.config(fg=C["subtext"])

    # ── Gestion fichiers ──────────────────────────────────────────────────────
    def _add_files(self, paths):
        added = 0
        for p in paths:
            p = p.strip()
            if p and os.path.isfile(p) and p not in self._queue:
                self._queue.append(p)
                self._listbox.insert(tk.END, f"   ·  {os.path.basename(p)}")
                self._listbox.itemconfig(tk.END, fg=C["subtext"])
                added += 1
        if added:
            self._status.set(f"{len(self._queue)} video(s) en file d'attente")

    def _browse(self):
        paths = filedialog.askopenfilenames(filetypes=VIDEO_EXT)
        if paths:
            self._add_files(list(paths))

    def _on_drop(self, event):
        self._add_files(parse_drop_paths(event.data))

    def _remove_selected(self):
        for i in reversed(self._listbox.curselection()):
            self._listbox.delete(i)
            self._queue.pop(i)
        self._status.set(f"{len(self._queue)} video(s) en file d'attente")

    def _clear_queue(self):
        if self._processing:
            return
        self._queue.clear()
        self._listbox.delete(0, tk.END)
        self._pbar_total["value"] = 0
        self._pbar_current["value"] = 0
        self._status.set("File videe.")

    def _update_item(self, index, status, extra=""):
        icons  = {"En cours": "▶", "Termine": "✓", "Erreur": "✕", "En attente": "·"}
        fg_map = {"En cours": C["active_fg"], "Termine": C["success_fg"],
                  "Erreur": C["error_fg"], "En attente": C["subtext"]}
        bg_map = {"En cours": C["active_bg"], "Termine": C["success_bg"],
                  "Erreur": C["error_bg"]}
        name  = os.path.basename(self._queue[index])
        label = f"   {icons.get(status, '·')}  {name}"
        if extra:
            label += f"   {extra}"
        self._listbox.delete(index)
        self._listbox.insert(index, label)
        self._listbox.itemconfig(index, fg=fg_map.get(status, C["text"]))
        if status in bg_map:
            self._listbox.itemconfig(index, bg=bg_map[status])

    # ── Compression ───────────────────────────────────────────────────────────
    def _start_queue(self):
        if not self._queue:
            messagebox.showwarning("File vide", "Ajoutez au moins une video.")
            return
        if self._processing:
            return
        self._processing = True
        self._btn_compress.set_state(False)
        self._pbar_total["value"] = 0
        self._pbar_current["value"] = 0
        threading.Thread(target=self._process_queue, daemon=True).start()

    def _process_queue(self):
        total = len(self._queue)
        errors = 0
        for idx, src in enumerate(self._queue):
            self.after(0, lambda i=idx: self._update_item(i, "En cours"))
            self.after(0, lambda i=idx: self._status.set(
                f"({i+1}/{total})  {os.path.basename(self._queue[i])}"))

            ok, info = self._compress_one(src)
            st = "Termine" if ok else "Erreur"
            self.after(0, lambda i=idx, s=st, x=info: self._update_item(i, s, x))
            if not ok:
                errors += 1

            pct = (idx + 1) / total * 100
            self.after(0, lambda v=pct: self._pbar_total.configure(value=v))

        self._processing = False
        self.after(0, lambda: self._btn_compress.set_state(True))
        self.after(0, lambda: self._pbar_current.configure(value=100))

        ok_count = total - errors
        if errors == 0:
            self.after(0, lambda: self._status.set(
                f"✓  {total} video(s) compressee(s) avec succes"))
            self.after(0, lambda: messagebox.showinfo(
                "Termine", f"{total} video(s) compressee(s) !\n"
                "Les fichiers sont dans le meme dossier que les originaux."))
        else:
            self.after(0, lambda: self._status.set(
                f"{ok_count} reussie(s)  ·  {errors} erreur(s)"))
            self.after(0, lambda: messagebox.showwarning(
                "Termine avec erreurs",
                f"{ok_count} reussie(s), {errors} erreur(s).\n"
                "Les lignes en rouge indiquent les fichiers problematiques."))

    def _compress_one(self, src):
        try:
            if self._same_fmt.get():
                ext = os.path.splitext(src)[1].lstrip(".").upper()
                fmt = ext if ext in FORMAT_CODEC else "MP4"
            else:
                fmt = self._format.get()

            vcodec, acodec = FORMAT_CODEC[fmt]
            crf = QUALITY_CRF[self._quality.get()]
            res = RESOLUTIONS[self._resolution.get()]
            base, _ = os.path.splitext(src)
            dst = f"{base}_compresse.{fmt.lower()}"
            ffmpeg = get_ffmpeg()

            probe = subprocess.run(
                [ffmpeg, "-i", src],
                stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                creationflags=WIN_FLAGS
            )
            duration = parse_duration(probe.stderr.decode(errors="ignore"))

            cmd = [ffmpeg, "-y", "-i", src,
                   "-vcodec", vcodec, "-acodec", acodec,
                   "-progress", "pipe:1", "-nostats"]

            if fmt in ("MP4", "MKV", "MOV"):
                cmd += ["-crf", crf, "-preset", "medium"]
            elif fmt == "WEBM":
                cmd += ["-crf", crf, "-b:v", "0"]
            elif fmt == "AVI":
                cmd += ["-qscale:v", str(int(int(crf) / 4))]

            if res:
                cmd += ["-vf", f"scale={res}:force_original_aspect_ratio=decrease,"
                               f"pad={res}:(ow-iw)/2:(oh-ih)/2"]

            cmd.append(dst)

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, creationflags=WIN_FLAGS)

            for line in proc.stdout:
                if line.startswith("out_time_ms="):
                    try:
                        ms = int(line.split("=")[1])
                        if duration > 0:
                            pct = min(100, ms / 1_000_000 / duration * 100)
                            self.after(0, lambda v=pct: self._pbar_current.configure(value=v))
                    except ValueError:
                        pass

            proc.wait()

            if proc.returncode == 0:
                size_mb = os.path.getsize(dst) / 1_048_576
                return True, f"{size_mb:.1f} Mo"
            return False, "Erreur ffmpeg"

        except FileNotFoundError:
            return False, "ffmpeg introuvable"
        except Exception as e:
            return False, str(e)[:40]


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = VideoCompressor()
    app.mainloop()
