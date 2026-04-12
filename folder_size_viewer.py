"""
Ordnergroessen-Viewer fuer Windows 10
======================================
Zeigt Ordnergroessen sofort beim Hovern und in der Baumansicht an.
Keine Installation noetig — nur Python 3.8+ mit tkinter (Standard).

Starten:
    python folder_size_viewer.py
"""

import tkinter as tk
from tkinter import ttk, filedialog
import fnmatch
import os
import threading
import time
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def format_size(size_bytes: int) -> str:
    """Gibt lesbare Groesse zurueck, z.B. '1,23 GB'."""
    if size_bytes < 0:
        return "—"
    if size_bytes < 1_024:
        return f"{size_bytes} B"
    if size_bytes < 1_024 ** 2:
        return f"{size_bytes / 1_024:.1f} KB"
    if size_bytes < 1_024 ** 3:
        return f"{size_bytes / 1_024 ** 2:.1f} MB"
    return f"{size_bytes / 1_024 ** 3:.2f} GB"


def format_bytes_exact(size_bytes: int) -> str:
    """Gibt exakte Byteanzahl mit Punkten als Tausendertrennzeichen zurueck."""
    return f"{size_bytes:,}".replace(",", ".") + " Bytes"


def format_size_full(size_bytes: int) -> str:
    """Gibt lesbare Groesse UND exakte Byteanzahl zurueck.

    Beispiel: '1,23 GB  (1.234.567.890 Bytes)'
    Fuer Dateien unter 1 KB wird nur die Byteanzahl angezeigt.
    """
    if size_bytes < 0:
        return "—"
    exact = f"{size_bytes:,}".replace(",", ".") + " Bytes"
    if size_bytes < 1_024:
        return exact
    readable = format_size(size_bytes)
    return f"{readable}  ({exact})"


def get_mtime_str(stat_result) -> str:
    """Gibt das Aenderungsdatum als deutschen String zurueck."""
    return time.strftime("%d.%m.%Y  %H:%M", time.localtime(stat_result.st_mtime))


# ---------------------------------------------------------------------------
# Groessen-Scanner (laeuft in eigenem Thread)
# ---------------------------------------------------------------------------

class SizeScanner:
    """
    Berechnet Ordnergroessen im Hintergrund.
    Haelt einen Cache, damit bereits berechnete Pfade nicht erneut gescannt werden.
    """

    def __init__(self, callback):
        # callback(path, size_bytes, item_count) wird im Hauptthread aufgerufen
        self._callback = callback
        self._cache: dict[str, tuple[int, int]] = {}   # path -> (size, items)
        self._in_progress: set[str] = set()
        self._lock = threading.Lock()

    def get_cached(self, path: str):
        """Gibt (size, items) aus Cache oder None zurueck."""
        return self._cache.get(path)

    def invalidate(self, path: str):
        """Loescht einen Pfad (und alle Unterpfade) aus dem Cache."""
        with self._lock:
            keys = [k for k in self._cache if k == path or k.startswith(path + os.sep)]
            for k in keys:
                self._cache.pop(k, None)
            self._in_progress.discard(path)

    def invalidate_all(self):
        with self._lock:
            self._cache.clear()
            self._in_progress.clear()

    def request(self, path: str, root_widget: tk.Misc):
        """Startet Hintergrundberechnung fuer path, falls nicht bereits im Cache/laufend."""
        with self._lock:
            if path in self._cache or path in self._in_progress:
                return
            self._in_progress.add(path)

        t = threading.Thread(target=self._scan, args=(path, root_widget), daemon=True)
        t.start()

    def _scan(self, path: str, root_widget: tk.Misc):
        total_size = 0
        total_items = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for fname in filenames:
                    try:
                        fp = os.path.join(dirpath, fname)
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass
                total_items += len(filenames) + len(dirnames)
        except (PermissionError, OSError):
            pass

        with self._lock:
            self._cache[path] = (total_size, total_items)
            self._in_progress.discard(path)

        # UI-Update muss im Hauptthread laufen
        root_widget.after(0, lambda: self._callback(path, total_size, total_items))


# ---------------------------------------------------------------------------
# Tooltip-Fenster
# ---------------------------------------------------------------------------

class Tooltip:
    """Schwebendes Hinweisfenster (kein Rahmen, gelber Hintergrund)."""

    def __init__(self, parent: tk.Misc):
        self._parent = parent
        self._win: tk.Toplevel | None = None
        self._after_id = None

    def show(self, x: int, y: int, text: str, delay_ms: int = 350):
        self.cancel()
        self._after_id = self._parent.after(delay_ms, lambda: self._create(x, y, text))

    def update_text(self, text: str):
        if self._win and self._win.winfo_exists():
            for widget in self._win.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(text=text)

    def _create(self, x: int, y: int, text: str):
        self.hide()
        self._win = tk.Toplevel(self._parent)
        self._win.wm_overrideredirect(True)
        self._win.attributes("-topmost", True)

        # Leicht versetzt unter dem Mauszeiger
        self._win.wm_geometry(f"+{x + 14}+{y + 18}")

        outer = tk.Frame(self._win, background="#1e1e2e", padx=1, pady=1)
        outer.pack()

        inner = tk.Frame(outer, background="#fffde7")
        inner.pack()

        lbl = tk.Label(
            inner,
            text=text,
            background="#fffde7",
            foreground="#1a1a1a",
            font=("Segoe UI", 9),
            justify="left",
            padx=10,
            pady=7,
        )
        lbl.pack()

    def hide(self):
        if self._win:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None

    def cancel(self):
        if self._after_id is not None:
            self._parent.after_cancel(self._after_id)
            self._after_id = None

    def cancel_and_hide(self):
        self.cancel()
        self.hide()


# ---------------------------------------------------------------------------
# Hauptanwendung
# ---------------------------------------------------------------------------

class FolderSizeViewer:

    FOLDER_ICON = "📁"
    FILE_ICON   = "📄"
    DRIVE_ICON  = "💾"

    # Grenzwerte fuer Farbkodierung der Groesse
    COLOR_HUGE   = "#d32f2f"   # > 1 GB  -> rot
    COLOR_LARGE  = "#f57c00"   # > 100 MB -> orange
    COLOR_MEDIUM = "#388e3c"   # > 10 MB  -> gruen
    COLOR_NORMAL = ""          # Rest     -> Standard

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Ordnergroessen-Viewer")
        self.root.geometry("980x640")
        self.root.minsize(640, 400)

        self.current_path: str = os.path.expanduser("~")
        self._scanner = SizeScanner(self._on_size_ready)
        self._tooltip = Tooltip(self.root)
        self._hovered_item: str | None = None
        self._all_folders: list = []
        self._all_files: list = []

        self._setup_style()
        self._build_ui()
        self._load_path(self.current_path)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def _setup_style(self):
        style = ttk.Style()
        # Bevorzuge das native Windows-Theme
        available = style.theme_names()
        for theme in ("vista", "winnative", "clam", "default"):
            if theme in available:
                style.theme_use(theme)
                break

        style.configure(
            "Treeview",
            rowheight=24,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
        )

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Toolbar ----
        toolbar = tk.Frame(self.root, bd=1, relief=tk.FLAT, pady=4, padx=6)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_cfg = dict(relief=tk.FLAT, padx=8, pady=3, font=("Segoe UI", 9), cursor="hand2")

        self._btn_up = tk.Button(
            toolbar, text="↑  Hoch", command=self._go_up, **btn_cfg
        )
        self._btn_up.pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            toolbar, text="📂  Ordner wählen…", command=self._choose_folder, **btn_cfg
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._path_var = tk.StringVar()
        path_entry = tk.Entry(
            toolbar, textvariable=self._path_var,
            font=("Segoe UI", 10), relief=tk.SOLID, bd=1
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        path_entry.bind("<Return>", lambda _e: self._load_path(self._path_var.get()))

        tk.Button(
            toolbar, text="↻  Aktualisieren", command=self._refresh, **btn_cfg
        ).pack(side=tk.LEFT)

        # ---- Suchleiste ----
        search_frame = tk.Frame(self.root, bd=0, relief=tk.FLAT, pady=3, padx=6)
        search_frame.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            search_frame, text="🔍  Suche:", font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 6))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_filter_change)
        self._search_entry = tk.Entry(
            search_frame, textvariable=self._search_var,
            font=("Segoe UI", 10), relief=tk.SOLID, bd=1
        )
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        tk.Label(
            search_frame, text="Mindestgröße:", font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 4))

        self._min_size_var = tk.StringVar(value="Alle")
        ttk.Combobox(
            search_frame, textvariable=self._min_size_var,
            values=["Alle", "> 1 KB", "> 100 KB", "> 1 MB", "> 10 MB", "> 100 MB", "> 1 GB"],
            state="readonly", width=11, font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._min_size_var.trace_add("write", self._on_filter_change)

        tk.Button(
            search_frame, text="✕  Löschen", command=self._clear_filter,
            relief=tk.FLAT, padx=6, pady=2, font=("Segoe UI", 9), cursor="hand2"
        ).pack(side=tk.LEFT)

        # ---- Baumansicht ----
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        cols = ("size", "size_bar", "items", "modified")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            selectmode="browse",
            show="tree headings",
        )
        self._tree.heading("#0",        text="Name",          anchor="w")
        self._tree.heading("size",      text="Größe",         anchor="e")
        self._tree.heading("size_bar",  text="",              anchor="w")
        self._tree.heading("items",     text="Elemente",      anchor="e")
        self._tree.heading("modified",  text="Geändert",      anchor="w")

        self._tree.column("#0",        width=300, minwidth=180, stretch=True)
        self._tree.column("size",      width=260, minwidth=160, stretch=False, anchor="e")
        self._tree.column("size_bar",  width=110, minwidth=60,  stretch=False, anchor="w")
        self._tree.column("items",     width=85,  minwidth=55,  stretch=False, anchor="e")
        self._tree.column("modified",  width=140, minwidth=100, stretch=False, anchor="w")

        # Farbkodierung
        self._tree.tag_configure("huge",   foreground=self.COLOR_HUGE)
        self._tree.tag_configure("large",  foreground=self.COLOR_LARGE)
        self._tree.tag_configure("medium", foreground=self.COLOR_MEDIUM)
        self._tree.tag_configure("file",   foreground="#555555")
        self._tree.tag_configure("scanning", foreground="#888888")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Events
        self._tree.bind("<Double-1>",  self._on_double_click)
        self._tree.bind("<Return>",    self._on_enter)
        self._tree.bind("<BackSpace>", lambda _e: self._go_up())
        self._tree.bind("<Motion>",    self._on_mouse_move)
        self._tree.bind("<Leave>",     self._on_mouse_leave)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self.root.bind("<Control-f>",  lambda _e: self._search_entry.focus_set())

        # Sortierung per Spaltenklick
        for col in ("#0", "size", "items", "modified"):
            self._tree.heading(col, command=lambda c=col: self._sort_by(c))

        self._sort_col = "name"
        self._sort_rev = False

        # ---- Statusleiste ----
        status_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._status_var = tk.StringVar(value="Bereit")
        tk.Label(
            status_frame, textvariable=self._status_var,
            anchor="w", font=("Segoe UI", 9), padx=6, pady=3
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._sel_var = tk.StringVar()
        tk.Label(
            status_frame, textvariable=self._sel_var,
            anchor="e", font=("Segoe UI", 9), padx=10, pady=3
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Pfad laden
    # ------------------------------------------------------------------

    def _load_path(self, path: str):
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            self._status_var.set(f"Kein gueltiger Ordner: {path}")
            return

        self.current_path = path
        self._path_var.set(path)
        self._btn_up.configure(state=tk.NORMAL if os.path.dirname(path) != path else tk.DISABLED)

        # Baum leeren
        for item in self._tree.get_children():
            self._tree.delete(item)

        self._status_var.set(f"Lade  {path}  …")
        threading.Thread(target=self._scan_directory, args=(path,), daemon=True).start()

    def _scan_directory(self, path: str):
        try:
            entries = list(os.scandir(path))
        except PermissionError:
            self.root.after(0, lambda: self._status_var.set("⛔  Kein Zugriff auf diesen Ordner."))
            return
        except OSError as exc:
            self.root.after(0, lambda: self._status_var.set(f"Fehler: {exc}"))
            return

        folders = sorted(
            [e for e in entries if e.is_dir(follow_symlinks=False)],
            key=lambda e: e.name.lower()
        )
        files = sorted(
            [e for e in entries if not e.is_dir(follow_symlinks=False)],
            key=lambda e: e.name.lower()
        )

        self.root.after(0, lambda: self._populate_tree(folders, files, path))

    def _populate_tree(self, folders, files, path: str):
        # Eintraege fuer spaetere Filterung merken
        self._all_folders = list(folders)
        self._all_files   = list(files)

        # Hintergrundscans fuer ALLE Ordner anfordern (unabhaengig vom Filter)
        for entry in folders:
            self._scanner.request(entry.path, self.root)

        # Baum gemaess aktivem Filter befuellen
        self._apply_filter()

    def _add_entry(self, entry: os.DirEntry, is_dir: bool):
        try:
            stat = entry.stat(follow_symlinks=False)
        except OSError:
            return

        mtime = get_mtime_str(stat)
        icon  = self.FOLDER_ICON if is_dir else self.FILE_ICON
        name  = f"{icon}  {entry.name}"

        if is_dir:
            cached = self._scanner.get_cached(entry.path)
            if cached:
                size_bytes, item_count = cached
                size_str  = format_size_full(size_bytes)
                items_str = str(item_count)
                bar       = self._make_bar(size_bytes)
                tag       = self._size_tag(size_bytes)
            else:
                size_str  = "wird berechnet…"
                items_str = ""
                bar       = ""
                tag       = "scanning"
        else:
            size_bytes = stat.st_size
            size_str   = format_size_full(size_bytes)
            items_str  = ""
            bar        = ""
            tag        = "file"

        self._tree.insert(
            "", "end",
            iid=entry.path,
            text=name,
            values=(size_str, bar, items_str, mtime),
            tags=(tag,),
        )

    # ------------------------------------------------------------------
    # Groesse fertig -> UI-Update
    # ------------------------------------------------------------------

    def _on_size_ready(self, path: str, size_bytes: int, item_count: int):
        if not self._tree.exists(path):
            return

        size_str  = format_size_full(size_bytes)
        bar       = self._make_bar(size_bytes)
        items_str = str(item_count)
        tag       = self._size_tag(size_bytes)

        current   = list(self._tree.item(path, "values"))
        if len(current) >= 4:
            current[0] = size_str
            current[1] = bar
            current[2] = items_str
            self._tree.item(path, values=current, tags=(tag,))

        # Tooltip aktualisieren, falls der Nutzer gerade darueber hovert
        if self._hovered_item == path:
            self._tooltip.update_text(self._tooltip_text(path, size_bytes, item_count))

        # Mindestgroessen-Filter nachtraeglich anwenden: Ordner ausblenden falls zu klein
        min_size = self._get_min_size_bytes()
        if min_size > 0 and size_bytes < min_size:
            self._tree.delete(path)
            self._update_filter_status()

    # ------------------------------------------------------------------
    # Tooltip
    # ------------------------------------------------------------------

    def _on_mouse_move(self, event: tk.Event):
        item = self._tree.identify_row(event.y)
        if item == self._hovered_item:
            return  # Gleiche Zeile -> nichts tun

        self._tooltip.cancel_and_hide()
        self._hovered_item = item

        if not item:
            return

        is_dir = os.path.isdir(item)
        cached = self._scanner.get_cached(item) if is_dir else None

        if is_dir:
            if cached:
                size_bytes, item_count = cached
                text = self._tooltip_text(item, size_bytes, item_count)
            else:
                text = f"{os.path.basename(item)}\n\nGröße wird berechnet…"
        else:
            try:
                sz = os.path.getsize(item)
                text = (
                    f"{os.path.basename(item)}\n\n"
                    f"Größe:  {format_size(sz)}\n"
                    f"Genau:  {format_bytes_exact(sz)}"
                )
            except OSError:
                text = os.path.basename(item)

        self._tooltip.show(event.x_root, event.y_root, text, delay_ms=300)

    def _on_mouse_leave(self, _event):
        self._tooltip.cancel_and_hide()
        self._hovered_item = None

    @staticmethod
    def _tooltip_text(path: str, size_bytes: int, item_count: int) -> str:
        return (
            f"{os.path.basename(path)}\n\n"
            f"Größe:     {format_size(size_bytes)}\n"
            f"Genau:     {format_bytes_exact(size_bytes)}\n"
            f"Elemente:  {item_count:,}".replace(",", ".")
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_double_click(self, event: tk.Event):
        item = self._tree.identify_row(event.y)
        if item and os.path.isdir(item):
            self._load_path(item)

    def _on_enter(self, _event):
        sel = self._tree.selection()
        if sel and os.path.isdir(sel[0]):
            self._load_path(sel[0])

    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self._load_path(parent)

    def _choose_folder(self):
        path = filedialog.askdirectory(
            title="Ordner auswählen",
            initialdir=self.current_path,
        )
        if path:
            self._load_path(path)

    def _refresh(self):
        # Cache fuer aktuellen Ordner und Unterordner leeren
        self._scanner.invalidate(self.current_path)
        self._load_path(self.current_path)

    # ------------------------------------------------------------------
    # Auswahl -> Statuszeile
    # ------------------------------------------------------------------

    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            self._sel_var.set("")
            return
        path = sel[0]
        if os.path.isdir(path):
            cached = self._scanner.get_cached(path)
            if cached:
                size_bytes, _ = cached
                self._sel_var.set(f"Ausgewählt:  {format_size_full(size_bytes)}")
            else:
                self._sel_var.set("Ausgewählt:  wird berechnet…")
        else:
            try:
                sz = os.path.getsize(path)
                self._sel_var.set(f"Ausgewählt:  {format_size_full(sz)}")
            except OSError:
                self._sel_var.set("")

    # ------------------------------------------------------------------
    # Sortierung
    # ------------------------------------------------------------------

    def _sort_by(self, col: str):
        items = [(self._tree.set(k, col) if col != "#0" else self._tree.item(k, "text"), k)
                 for k in self._tree.get_children("")]

        def sort_key(pair):
            val = pair[0].strip()
            # Groessen sortierbar machen
            if col == "size":
                return self._parse_size(val)
            if col == "items":
                try:
                    return int(val.replace(".", ""))
                except ValueError:
                    return -1
            return val.lower()

        reverse = (self._sort_col == col) and not self._sort_rev
        items.sort(key=sort_key, reverse=reverse)
        self._sort_col = col
        self._sort_rev = reverse

        for index, (_, k) in enumerate(items):
            self._tree.move(k, "", index)

    @staticmethod
    def _parse_size(text: str) -> float:
        """Wandelt '1.23 GB' in Bytes um fuer korrekte Sortierung."""
        units = {"B": 1, "KB": 1_024, "MB": 1_024**2, "GB": 1_024**3}
        parts = text.strip().split()
        if len(parts) == 2:
            try:
                return float(parts[0].replace(",", ".")) * units.get(parts[1], 1)
            except ValueError:
                pass
        return -1.0

    # ------------------------------------------------------------------
    # Suche & Filter
    # ------------------------------------------------------------------

    _MIN_SIZE_BYTES: dict = {
        "Alle":     0,
        "> 1 KB":   1_024,
        "> 100 KB": 100 * 1_024,
        "> 1 MB":   1_024 ** 2,
        "> 10 MB":  10 * 1_024 ** 2,
        "> 100 MB": 100 * 1_024 ** 2,
        "> 1 GB":   1_024 ** 3,
    }

    def _get_min_size_bytes(self) -> int:
        return self._MIN_SIZE_BYTES.get(self._min_size_var.get(), 0)

    def _on_filter_change(self, *_args):
        self._apply_filter()

    def _clear_filter(self):
        self._search_var.set("")
        self._min_size_var.set("Alle")

    def _matches_filter(self, entry: os.DirEntry, is_dir: bool) -> bool:
        """Gibt True zurueck wenn der Eintrag den aktuellen Filtern entspricht."""
        # Textfilter (unterstuetzt Wildcards wie *.log oder temp*)
        text = self._search_var.get().strip().lower()
        if text:
            name = entry.name.lower()
            if "*" in text or "?" in text:
                if not fnmatch.fnmatch(name, text):
                    return False
            else:
                if text not in name:
                    return False

        # Mindestgroessen-Filter
        min_size = self._get_min_size_bytes()
        if min_size > 0:
            if is_dir:
                cached = self._scanner.get_cached(entry.path)
                if cached is not None:
                    size_bytes, _ = cached
                    if size_bytes < min_size:
                        return False
                # Noch nicht gecacht -> anzeigen (Groesse unbekannt)
            else:
                try:
                    if entry.stat(follow_symlinks=False).st_size < min_size:
                        return False
                except OSError:
                    pass

        return True

    def _apply_filter(self):
        """Leert den Baum und befuellt ihn neu gemaess aktueller Suchkriterien."""
        if not self._all_folders and not self._all_files:
            return

        for item in self._tree.get_children():
            self._tree.delete(item)

        matched_folders = [e for e in self._all_folders if self._matches_filter(e, True)]
        matched_files   = [e for e in self._all_files   if self._matches_filter(e, False)]

        for entry in matched_folders:
            self._add_entry(entry, is_dir=True)
        for entry in matched_files:
            self._add_entry(entry, is_dir=False)

        self._update_filter_status(len(matched_folders), len(matched_files))

    def _update_filter_status(self, n_folders: int = -1, n_files: int = -1):
        """Aktualisiert die Statuszeile; zaehlt bei Bedarf selbst."""
        if n_folders < 0:
            children = self._tree.get_children()
            n_folders = sum(1 for iid in children if os.path.isdir(iid))
            n_files   = len(children) - n_folders

        total = len(self._all_folders) + len(self._all_files)
        shown = n_folders + n_files
        filter_info = f"  —  Filter: {shown} von {total} angezeigt" if shown < total else ""

        self._status_var.set(
            f"{self.current_path}     —     {n_folders} Ordner,  {n_files} Datei(en){filter_info}"
        )

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    @staticmethod
    def _size_tag(size_bytes: int) -> str:
        if size_bytes >= 1_073_741_824:      # >= 1 GB
            return "huge"
        if size_bytes >= 104_857_600:        # >= 100 MB
            return "large"
        if size_bytes >= 10_485_760:         # >= 10 MB
            return "medium"
        return ""

    @staticmethod
    def _make_bar(size_bytes: int, max_chars: int = 15) -> str:
        """Einfacher ASCII-Balken relativ zu 10 GB als Maximum."""
        max_bytes = 10 * 1_024 ** 3  # 10 GB = 100 %
        ratio = min(size_bytes / max_bytes, 1.0)
        filled = round(ratio * max_chars)
        return "█" * filled + "░" * (max_chars - filled)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()

    # App-Icon (ignoriert Fehler wenn nicht vorhanden)
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass

    app = FolderSizeViewer(root)

    # Startpfad aus Kommandozeile
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        app._load_path(sys.argv[1])

    root.mainloop()


if __name__ == "__main__":
    main()
