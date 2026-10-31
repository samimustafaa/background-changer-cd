"""CD Background Studio: offline 4K wallpaper editor; no game file changes."""
from __future__ import annotations
import json
import threading
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from compositor import load_image, cover, default_preserve_mask, composite, paint_mask

VERSION = '0.1.0'
RELEASES = 'https://github.com/samimustafaa/background-changer-cd/releases/latest'
DARK, PANEL, BTN, WHITE, MUTED, GOLD = '#101216', '#1d2129', '#303640', '#f4f6f9', '#a4adbb', '#e5a451'

class Studio:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('CD Background Studio | v' + VERSION)
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
        tk.Label(top, text='    v0.1.0  ·  OFFLINE PREVIEW', bg=DARK, fg=MUTED,
                 font=('Segoe UI', 9)).pack(side='left')
        tk.Button(top, text='Check updates ↗', command=self.check_updates, bg=BTN,
                  fg=WHITE, relief='flat', bd=0, cursor='hand2', padx=12, pady=8).pack(side='right')
        body = tk.Frame(self.root, bg=DARK)
        body.pack(fill='both', expand=True, padx=22)
        side = tk.Frame(body, bg=PANEL, width=290, padx=16, pady=8)
        side.pack(side='right', fill='y', padx=(12, 0))
        side.pack_propagate(False)
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
        self.shot_label = self.label(side, 'Optional: keep UI / player / platform', color=MUTED)
        self.label(side, '02   PRESERVE THE FOREGROUND', ('Segoe UI', 12, 'bold'))
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
        self.label(side, '03   EXPORT', ('Segoe UI', 12, 'bold'))
        self.button(side, '↓ Export 4K asset pack', self.export_pack, bright=True)
        self.button(side, 'Save lobby preview PNG', self.export_preview)
        self.label(side, 'Offline output only. No game files or anti-cheat modifications.',
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
        result = composite(self.wallpaper, self.screenshot, self.mask)
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
                composite(self.wallpaper, self.screenshot, self.mask).save(p/'lobby_preview.png')
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
                composite(self.wallpaper, self.screenshot, self.mask).save(path)
                self.status.set(f'Preview saved to {path}')
            except Exception as exc:
                messagebox.showerror('Save failed', str(exc))

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
