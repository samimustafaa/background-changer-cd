"""CD Background Studio: optional Win32 live lobby overlay; no game-file changes."""
from __future__ import annotations
import json
import os
import threading
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from compositor import load_image, cover, default_preserve_mask, composite, paint_mask
from lobby_regions import live_wallpaper_mask
from live_overlay import request_dpi_awareness, LiveLobbyOverlay

VERSION = '0.2.0'
RELEASES = 'https://github.com/samimustafaa/background-changer-cd/releases/latest'
DARK, PANEL, BTN, WHITE, MUTED, GOLD = '#101216', '#1d2129', '#303640', '#f4f6f9', '#a4adbb', '#e5a451'

class Studio:
    def __init__(self):
        request_dpi_awareness()
        self.root = tk.Tk()
        self.root.title('CD Background Studio | v' + VERSION)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.configure(bg=DARK)
        self.root.geometry('1190x740')
        self.root.minsize(900, 620)
        self.wallpaper = self.screenshot = self.mask = None
        self.preview_image = None
        self.box = (0, 0, 0, 0)
        self.last_point = None
        self.history = []
        self.radius = 28
        self.preserve = True
        self.live = None
        self.game_exe = tk.StringVar(value='client.exe')
        self.lobby_guard = tk.BooleanVar(value=True)
        self.live_status = tk.StringVar(value='Live overlay: OFF')
        self.status = tk.StringVar(value='Import a wallpaper to begin. Nothing is changed in the game.')
        self._build()

    def label(self, parent, text, font=('Segoe UI', 10), color=WHITE, **kw):
        widget = tk.Label(parent, text=text, bg=parent['bg'], fg=color,
                          font=font, anchor='w', **kw)
        widget.pack(fill='x', pady=(5, 3))
        return widget

    def button(self, parent, title, action, bright=False):
        btn = tk.Button(parent, text=title, command=action, bg=GOLD if bright else BTN,
                        fg=DARK if bright else WHITE, activebackground='#ffcc7d' if bright else '#464e5e',
                        activeforeground=DARK if bright else WHITE, bd=0, relief='flat',
                        cursor='hand2', font=('Segoe UI', 10, 'bold'), pady=10)
        btn.pack(fill='x', pady=4)
        return btn

    def _build(self):
        top = tk.Frame(self.root, bg=DARK)
        top.pack(fill='x', padx=22, pady=16)
        tk.Label(top, text='CD / BACKGROUND STUDIO', bg=DARK, fg=GOLD,
                 font=('Segoe UI', 18, 'bold')).pack(side='left')
        tk.Label(top, text='    v0.2.0  ·  LIVE LOBBY OVERLAY', bg=DARK, fg=MUTED,
                 font=('Segoe UI', 9)).pack(side='left')
        tk.Button(top, text='Check updates ↗', command=self.check_updates, bg=BTN,
                  fg=WHITE, relief='flat', bd=0, cursor='hand2', padx=12, pady=8).pack(side='right')
        body = tk.Frame(self.root, bg=DARK)
        body.pack(fill='both', expand=True, padx=22)
        holder = tk.Frame(body, bg=PANEL, width=300)
        holder.pack(side='right', fill='y', padx=(12, 0))
        holder.pack_propagate(False)
        scroll = tk.Canvas(holder, bg=PANEL, highlightthickness=0, borderwidth=0)
        scroll.pack(side='left', fill='both', expand=True)
        scrollbar = tk.Scrollbar(holder, orient='vertical', command=scroll.yview)
        scrollbar.pack(side='right', fill='y')
        scroll.configure(yscrollcommand=scrollbar.set)
        side = tk.Frame(scroll, bg=PANEL, padx=16, pady=8)
        side_window = scroll.create_window((0, 0), anchor='nw', window=side)
        side.bind('<Configure>', lambda e: scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>', lambda e: scroll.itemconfigure(side_window, width=e.width))
        def scroll_panel(e):
            scroll.yview_scroll(int(-e.delta/120), 'units')
        side.bind('<Enter>', lambda _: scroll.bind_all('<MouseWheel>', scroll_panel))
        side.bind('<Leave>', lambda _: scroll.unbind_all('<MouseWheel>'))
        view = tk.Frame(body, bg=PANEL, padx=9, pady=9)
        view.pack(side='left', fill='both', expand=True)
        tk.Label(view, text='LIVE COMPOSITE PREVIEW  ·  NOT IN-GAME', bg=PANEL, fg=GOLD,
                 font=('Segoe UI', 9, 'bold'), anchor='w').pack(fill='x', pady=(2, 9))
        self.canvas = tk.Canvas(view, bg=DARK, highlightthickness=0, cursor='crosshair')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        self.canvas.bind('<ButtonPress-1>', self.start_paint)
        self.canvas.bind('<B1-Motion>', self.move_paint)
        self.canvas.bind('<ButtonRelease-1>', lambda e: setattr(self, 'last_point', None))
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.label(side, '01   WALLPAPER', ('Segoe UI', 12, 'bold'))
        self.button(side, '＋ Choose wallpaper', self.choose_wallpaper, bright=True)
        self.wall_label = self.label(side, 'PNG / JPG / WEBP • up to 4K+', color=MUTED)
        self.button(side, '▣ Choose lobby screenshot', self.choose_screenshot)
        self.shot_label = self.label(side, 'Optional: refine player/UI protection', color=MUTED)
        self.label(side, '02   APPLY TO GAME LOBBY', ('Segoe UI', 12, 'bold'))
        self.label(side, 'Game EXE (default: client.exe)', color=MUTED)
        tk.Entry(side, textvariable=self.game_exe, bg=BTN, fg=WHITE,
                 insertbackground=WHITE, relief='flat', font=('Segoe UI', 10)).pack(fill='x', ipady=6)
        tk.Checkbutton(side, text='Auto-hide outside lobby (Start button check)',
                       variable=self.lobby_guard, bg=PANEL, fg=WHITE,
                       selectcolor=BTN, activebackground=PANEL,
                       activeforeground=WHITE, wraplength=245, justify='left',
                       font=('Segoe UI', 9)).pack(anchor='w', pady=5)
        self.button(side, '▶ APPLY TO LOBBY (LIVE)', self.apply_to_lobby, bright=True)
        self.button(side, '✕ REMOVE LIVE BACKGROUND', self.remove_live)
        self.label(side, 'Click Apply, then switch to the game. Borderless/windowed only.',
                   ('Segoe UI', 9), MUTED, wraplength=255, justify='left')
        self.label(side, 'Uses a click-through overlay, not game asset replacement.',
                   ('Segoe UI', 9), MUTED, wraplength=255, justify='left')
        tk.Label(side, textvariable=self.live_status, bg=PANEL, fg=GOLD,
                 wraplength=245, justify='left', anchor='w',
                 font=('Segoe UI', 9, 'bold')).pack(fill='x', pady=5)
        self.label(side, '03   REFINE THE PROTECTION MASK', ('Segoe UI', 12, 'bold'))
        self.label(side, 'Paint over the player and widgets to keep those pixels.',
                   ('Segoe UI', 9), MUTED, wraplength=255, justify='left')
        self.button(side, 'Apply starter protection mask', self.apply_mask)
        self.button(side, 'Brush: keep original', lambda: self.set_brush(True))
        self.button(side, 'Brush: show wallpaper', lambda: self.set_brush(False))
        self.brush_label = self.label(side, 'Brush: KEEP ORIGINAL  ·  28px', color=GOLD)
        scale = tk.Scale(side, from_=3, to=130, orient='horizontal', command=self.brush_size,
                         bg=PANEL, fg=WHITE, highlightthickness=0, troughcolor=BTN,
                         showvalue=0, bd=0)
        scale.set(28)
        scale.pack(fill='x')
        self.button(side, 'Undo last brush stroke', self.undo)
        self.button(side, 'Clear protection mask', self.clear_mask)
        self.label(side, '04   OPTIONAL EXPORT', ('Segoe UI', 12, 'bold'))
        self.button(side, '↓ Export 4K asset pack', self.export_pack, bright=True)
        self.button(side, 'Save lobby preview PNG', self.export_preview)
        self.label(side, 'Live mode adds a screen overlay; no game files or anti-cheat modifications.',
                   ('Segoe UI', 9), MUTED, wraplength=255, justify='left')
        tk.Label(self.root, textvariable=self.status, bg=DARK, fg=MUTED,
                 anchor='w', font=('Segoe UI', 9)).pack(fill='x', padx=24, pady=12)

    def choose_wallpaper(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg *.webp *.bmp')])
        if path:
            try:
                self.wallpaper = load_image(path)
                self.wall_label.config(text=f'{Path(path).name} · {self.wallpaper.width}×{self.wallpaper.height}')
                self.status.set('Wallpaper loaded. Add screenshot to keep original foreground.')
                self.redraw()
            except Exception as exc:
                messagebox.showerror('Invalid image', str(exc))

    def choose_screenshot(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg *.webp *.bmp')])
        if path:
            try:
                self.screenshot = load_image(path)
                self.mask = default_preserve_mask(self.screenshot.size)
                self.history.clear()
                self.shot_label.config(text=f'{Path(path).name} · {self.screenshot.width}×{self.screenshot.height}')
                self.status.set('Starter mask is approximate; paint around player edges.')
                self.redraw()
            except Exception as exc:
                messagebox.showerror('Invalid image', str(exc))

    def remember(self):
        if self.mask is not None:
            self.history.append(self.mask.copy())
            self.history = self.history[-12:]

    def apply_mask(self):
        if self.screenshot is None:
            return messagebox.showinfo('Screenshot required', 'Choose a lobby screenshot first.')
        self.remember()
        self.mask = default_preserve_mask(self.screenshot.size)
        self.redraw()

    def set_brush(self, preserve):
        self.preserve = preserve
        self.brush_label.config(text=('Brush: KEEP ORIGINAL' if preserve else 'Brush: SHOW WALLPAPER') + f'  ·  {self.radius}px')

    def brush_size(self, value):
        self.radius = int(float(value))
        self.set_brush(self.preserve)

    def wheel(self, event):
        self.radius = min(130, max(3, self.radius + (4 if event.delta > 0 else -4)))
        self.set_brush(self.preserve)

    def undo(self):
        if self.history:
            self.mask = self.history.pop()
            self.redraw()

    def clear_mask(self):
        if self.mask is not None:
            self.remember()
            self.mask = Image.new('L', self.mask.size, 0)
            self.redraw()

    def map_point(self, x, y):
        left, top, width, height = self.box
        if self.mask is None or not (left <= x < left+width and top <= y < top+height):
            return None
        return (min(self.mask.width-1, int((x-left)*self.mask.width/width)),
                min(self.mask.height-1, int((y-top)*self.mask.height/height)))

    def start_paint(self, event):
        point = self.map_point(event.x, event.y)
        if point:
            self.remember()
            self.last_point = point
            self.paint(point)

    def move_paint(self, event):
        point = self.map_point(event.x, event.y)
        if point and self.last_point:
            self.paint(point)

    def paint(self, point):
        paint_mask(self.mask, *point, self.radius, self.preserve, self.last_point)
        self.last_point = point
        self.redraw()

    def redraw(self):
        self.canvas.delete('all')
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 25 or h < 25:
            return
        if self.wallpaper is None:
            self.canvas.create_text(w//2, h//2, text='IMPORT A 4K WALLPAPER TO START',
                                    font=('Segoe UI', 14, 'bold'), fill=MUTED)
            return
        result = self.make_preview()
        scale = min((w-20)/result.width, (h-20)/result.height)
        pw, ph = max(1, int(result.width*scale)), max(1, int(result.height*scale))
        self.preview_image = ImageTk.PhotoImage(result.resize((pw, ph), Image.Resampling.LANCZOS))
        left, top = (w-pw)//2, (h-ph)//2
        self.box = (left, top, pw, ph)
        self.canvas.create_image(left, top, image=self.preview_image, anchor='nw')

    def export_pack(self):
        if self.wallpaper is None:
            return messagebox.showinfo('Wallpaper required', 'Choose a wallpaper first.')
        folder = filedialog.askdirectory(title='Save offline wallpaper pack')
        if not folder:
            return
        try:
            p = Path(folder)
            cover(self.wallpaper, (3840, 2160)).save(p/'wallpaper_4k.png')
            if self.screenshot is not None:
                self.make_preview().save(p/'lobby_preview.png')
                self.mask.save(p/'protection_mask.png')
            (p/'pack_info.json').write_text(json.dumps({'version': VERSION,
                'game_installed': False, 'note': 'Offline preview only. No game files altered.'}, indent=2), encoding='utf-8')
            self.status.set(f'Exported 4K asset pack: {folder}')
            messagebox.showinfo('Exported', 'Saved offline assets. NOT installed in the game.')
        except Exception as exc:
            messagebox.showerror('Export failed', str(exc))

    def export_preview(self):
        if self.wallpaper is None:
            return messagebox.showinfo('Wallpaper required', 'Choose a wallpaper first.')
        path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png')])
        if path:
            try:
                self.make_preview().save(path)
                self.status.set(f'Preview saved to {path}')
            except Exception as exc:
                messagebox.showerror('Save failed', str(exc))

    def make_preview(self):
        if self.screenshot is None:
            return self.wallpaper.convert('RGB').copy()
        region = live_wallpaper_mask(self.screenshot.size, self.mask)
        image = cover(self.wallpaper, self.screenshot.size)
        return Image.composite(image, self.screenshot, region)

    def apply_to_lobby(self):
        if self.wallpaper is None:
            return messagebox.showinfo('Select a wallpaper', 'Upload your wallpaper first.')
        if os.name != 'nt':
            return messagebox.showinfo('Windows required', 'Live overlay works on Windows only.')
        try:
            if self.live is None:
                self.live = LiveLobbyOverlay(self.root, self.live_status.set)
            self.live.arm(self.wallpaper, self.mask, self.game_exe.get(),
                          self.lobby_guard.get())
            self.status.set('Apply armed. Switch to the Creative Destruction lobby.')
        except Exception as exc:
            messagebox.showerror('Could not start live overlay', str(exc))

    def remove_live(self):
        if self.live is not None:
            self.live.remove()
        self.status.set('Live lobby wallpaper removed.')

    def close(self):
        if self.live is not None:
            self.live.close()
        self.root.destroy()

    def check_updates(self):
        self.status.set('Checking GitHub Releases…')
        def fetch():
            try:
                url = 'https://api.github.com/repos/samimustafaa/background-changer-cd/releases/latest'
                request = urllib.request.Request(url, headers={'User-Agent': 'CD-Background-Studio'})
                with urllib.request.urlopen(request, timeout=7) as response:
                    tag = json.load(response).get('tag_name', '').removeprefix('v')
                def notify():
                    if tag and tag != VERSION and messagebox.askyesno('Update available', f'Version {tag} available. Open Releases?'):
                        webbrowser.open(RELEASES)
                    else:
                        self.status.set(f'Installed: {VERSION} · Latest: {tag}')
                self.root.after(0, notify)
            except Exception:
                self.root.after(0, lambda: self.status.set('Unable to check updates.'))
        threading.Thread(target=fetch, daemon=True).start()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    Studio().run()
