"""
UNEMI 2026 - Sistema de Comunicación de Datos
Simulador OSI (Encapsulamiento / Desencapsulamiento) - Python + Tkinter
"""

import tkinter as tk
from tkinter import ttk
import base64
import time

# ------------------------------------------------------------------
# PALETA DE COLORES (igual al mockup original)
# ------------------------------------------------------------------
BG        = "#050b1a"
PANEL     = "#0b1730"
PANEL2    = "#0e1e40"
BORDER    = "#1c3563"
TXT       = "#e8f0ff"
MUTED     = "#7b93c4"
ACCENT    = "#26e0c9"
BLUE      = "#2f7dff"
GREEN     = "#20c96a"
PURPLE    = "#9b6bff"
RED       = "#ff4d6d"
ORANGE    = "#ff9f43"

FONT_BASE   = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI Semibold", 14)
FONT_SMALL  = ("Segoe UI", 8)
FONT_MONO   = ("Cascadia Mono", 9)


def _shade(hex_color, factor):
    """Aclara (factor>0) u oscurece (factor<0) un color hex."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 0:
        r = r + (255 - r) * factor
        g = g + (255 - g) * factor
        b = b + (255 - b) * factor
    else:
        r = r * (1 + factor)
        g = g * (1 + factor)
        b = b * (1 + factor)
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(v))) for v in (r, g, b)))


def add_hover(widget, base_color, hover_color):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_color))
    widget.bind("<Leave>", lambda e: widget.config(bg=base_color))

# ------------------------------------------------------------------
# DATOS DE LAS 7 CAPAS OSI
# ------------------------------------------------------------------
LAYERS = [
    {"n": 7, "name": "Aplicación",     "pdu": "Datos",             "color": PURPLE,
     "fn": "Provee servicios de red directamente a las aplicaciones del usuario.",
     "add": "Datos generados por la aplicación"},
    {"n": 6, "name": "Presentación",   "pdu": "Datos (Base64)",    "color": "#7a5cff",
     "fn": "Traduce, cifra y comprime los datos para su transporte.",
     "add": "Codificación Base64"},
    {"n": 5, "name": "Sesión",         "pdu": "Datos",             "color": "#5a6bff",
     "fn": "Establece, gestiona y termina las sesiones de comunicación.",
     "add": "Establecimiento de sesión"},
    {"n": 4, "name": "Transporte",     "pdu": "Segmento (TCP)",    "color": BLUE,
     "fn": "Segmenta los datos y proporciona control de flujo y fiabilidad.",
     "add": "Header TCP (puertos, secuencia, etc.)"},
    {"n": 3, "name": "Red",            "pdu": "Paquete (IP)",      "color": GREEN,
     "fn": "Determina la mejor ruta y direcciona los paquetes entre redes.",
     "add": "Header IP agregado"},
    {"n": 2, "name": "Enlace de Datos","pdu": "Trama (MAC)",       "color": ORANGE,
     "fn": "Empaqueta los datos en tramas y controla el acceso al medio físico.",
     "add": "Header y Trailer (direcciones MAC)"},
    {"n": 1, "name": "Física",         "pdu": "Bits",              "color": RED,
     "fn": "Transmite el flujo de bits en forma de señales físicas por el medio.",
     "add": "Datos convertidos en bits"},
]
ENC_ORDER = LAYERS[:]          # 7 -> 1
DEC_ORDER = list(reversed(LAYERS))  # 1 -> 7
TOTAL_STEPS = 15  # 7 encaps + 1 transmisión + 7 decaps


NEXT_COLOR = "#ffd166"


class LayerRow(tk.Frame):
    """Una fila visual de capa (número + nombre + PDU + led de estado), clicable."""
    def __init__(self, master, layer, side, on_click):
        super().__init__(master, bg=PANEL2, highlightthickness=1,
                          highlightbackground=BORDER, padx=8, pady=6, cursor="hand2")
        self.layer = layer
        self.side = side
        self.state = "idle"

        num = tk.Label(self, text=str(layer["n"]), bg=layer["color"], fg="white",
                        font=FONT_BOLD, width=2, cursor="hand2")
        num.grid(row=0, column=0, rowspan=2, padx=(0, 8))

        name = tk.Label(self, text=layer["name"], bg=PANEL2, fg=TXT, font=FONT_BOLD,
                         anchor="w", cursor="hand2")
        name.grid(row=0, column=1, sticky="w")
        pdu = tk.Label(self, text=layer["pdu"], bg=PANEL2, fg=MUTED, font=FONT_SMALL,
                        anchor="w", cursor="hand2")
        pdu.grid(row=1, column=1, sticky="w")

        self.led = tk.Canvas(self, width=12, height=12, bg=PANEL2, highlightthickness=0,
                              cursor="hand2")
        self.led_id = self.led.create_oval(2, 2, 10, 10, fill="#2a3a5c", outline="")
        self.led.grid(row=0, column=2, rowspan=2, padx=(8, 0))
        self.columnconfigure(1, weight=1)

        for w in (self, num, name, pdu, self.led):
            w.bind("<Button-1>", lambda e: on_click(self.side, self.layer["n"]))
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, _e=None):
        if self.state in ("idle", "next"):
            self.config(highlightbackground=MUTED)

    def _on_leave(self, _e=None):
        self.set_state(self.state)

    def set_state(self, state):
        """state: 'idle' | 'active' | 'done' | 'next'"""
        self.state = state
        if state == "active":
            self.config(highlightbackground=ACCENT)
            self.led.itemconfig(self.led_id, fill=ACCENT)
        elif state == "done":
            self.config(highlightbackground=BORDER)
            self.led.itemconfig(self.led_id, fill=GREEN)
        elif state == "next":
            self.config(highlightbackground=NEXT_COLOR)
            self.led.itemconfig(self.led_id, fill=NEXT_COLOR)
        else:
            self.config(highlightbackground=BORDER)
            self.led.itemconfig(self.led_id, fill="#2a3a5c")


class SimuladorOSI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador OSI - UNEMI 2026")
        self.configure(bg=BG)
        self.geometry("1500x950")
        self.minsize(1150, 780)

        self.step_index = 0
        self.running = False
        self.step_mode = False
        self.start_time = None
        self.after_id = None
        self.prog_anim_id = None
        self.prog_current = 0
        self.msg = ""

        self._build_topbar()
        self._build_header()
        self._build_controls()
        self._build_main_grid()
        self._build_bottom()
        self.reset_all()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w, h = 1500, 950
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - w) // 2, max(0, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_topbar(self):
        bar = tk.Canvas(self, height=4, bg=BG, highlightthickness=0)
        bar.pack(fill="x")

        def draw(event=None):
            bar.delete("all")
            w = bar.winfo_width() or 1500
            stops = [(0.0, BLUE), (0.5, PURPLE), (1.0, ACCENT)]
            steps = 120
            for i in range(steps):
                t = i / steps
                for j in range(len(stops) - 1):
                    t0, c0 = stops[j]
                    t1, c1 = stops[j + 1]
                    if t0 <= t <= t1:
                        local = (t - t0) / (t1 - t0) if t1 > t0 else 0
                        color = self._lerp_color(c0, c1, local)
                        break
                else:
                    color = stops[-1][1]
                x0 = int(w * i / steps)
                x1 = int(w * (i + 1) / steps)
                bar.create_rectangle(x0, 0, x1, 4, fill=color, width=0)

        bar.bind("<Configure>", draw)

    @staticmethod
    def _lerp_color(c0, c1, t):
        c0 = c0.lstrip("#"); c1 = c1.lstrip("#")
        r0, g0, b0 = (int(c0[i:i + 2], 16) for i in (0, 2, 4))
        r1, g1, b1 = (int(c1[i:i + 2], 16) for i in (0, 2, 4))
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    # -------------------------------------------------- HEADER --------
    def _build_header(self):
        header = tk.Frame(self, bg=PANEL, highlightthickness=1,
                           highlightbackground=BORDER)
        header.pack(fill="x", padx=14, pady=(14, 8))

        left = tk.Frame(header, bg=PANEL)
        left.pack(side="left", padx=16, pady=10)

        logo = tk.Canvas(left, width=44, height=44, bg=PANEL, highlightthickness=0)
        logo.create_oval(2, 2, 42, 42, fill=BLUE, outline="")
        logo.create_text(22, 22, text="U", fill="white", font=FONT_TITLE)
        logo.pack(side="left", padx=(0, 12))

        txts = tk.Frame(left, bg=PANEL)
        txts.pack(side="left")
        tk.Label(txts, text="UNIVERSIDAD ESTATAL DE MILAGRO — SISTEMA DE COMUNICACIÓN DE DATOS",
                  bg=PANEL, fg=TXT, font=FONT_BOLD).pack(anchor="w")
        tk.Label(txts, text="SIMULADOR OSI — Encapsulamiento y Desencapsulamiento",
                  bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(anchor="w")

        right = tk.Label(header, text="Conectando conocimientos,\nconstruyendo futuro — UNEMI 2026",
                          bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "italic"), justify="right")
        right.pack(side="right", padx=16)

    # -------------------------------------------------- CONTROLS -------
    def _build_controls(self):
        ctrl = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        ctrl.pack(fill="x", padx=14, pady=(0, 8))
        inner = tk.Frame(ctrl, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=10)

        msgbox = tk.Frame(inner, bg=PANEL)
        msgbox.pack(side="left", padx=(0, 20))
        tk.Label(msgbox, text="Mensaje a transmitir", bg=PANEL, fg=MUTED,
                  font=FONT_SMALL).pack(anchor="w")
        self.msg_entry = tk.Entry(msgbox, width=40, bg=PANEL2, fg=TXT,
                                   insertbackground=TXT, relief="flat",
                                   highlightthickness=1, highlightbackground=BORDER,
                                   font=FONT_BASE)
        self.msg_entry.insert(0, "Hola UNEMI 2026 - Redes de Computadoras")
        self.msg_entry.pack(ipady=4)

        modebox = tk.Frame(inner, bg=PANEL)
        modebox.pack(side="left", padx=20)
        self.mode_var = tk.StringVar(value="auto")
        for txt, val in [("Automático", "auto"), ("Paso a paso", "step")]:
            tk.Radiobutton(modebox, text=txt, variable=self.mode_var, value=val,
                           bg=PANEL, fg=TXT, selectcolor=PANEL2, activebackground=PANEL,
                           font=FONT_BASE).pack(side="left", padx=6)

        btns = tk.Frame(inner, bg=PANEL)
        btns.pack(side="left", padx=20)

        def mkbtn(text, bg, fg, cmd):
            hover = _shade(bg, 0.16)
            b = tk.Button(btns, text=text, bg=bg, fg=fg, relief="flat", font=FONT_BOLD,
                          padx=16, pady=7, activebackground=hover, activeforeground=fg,
                          bd=0, highlightthickness=0, command=cmd, cursor="hand2")
            b.pack(side="left", padx=4)
            add_hover(b, bg, hover)
            return b

        self.btn_start = mkbtn("▶ Iniciar", GREEN, "#04101f", self.on_start)
        self.btn_pause = mkbtn("⏸ Pausar", BLUE, "white", self.on_pause)
        self.btn_next  = mkbtn("⏭ Siguiente", "#3a63d8", "white", self.on_next)
        self.btn_reset = mkbtn("⟲ Reiniciar", "#3a4a6b", "white", self.reset_all)

        hint = tk.Label(ctrl, bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w",
                         text="💡 Haz clic en la capa resaltada en dorado para procesarla, "
                              "o en cualquier otra capa para ver su información.")
        hint.pack(fill="x", padx=14, pady=(0, 10))

    # -------------------------------------------------- MAIN GRID ------
    def _build_main_grid(self):
        grid = tk.Frame(self, bg=BG)
        grid.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        for i, w in enumerate([3, 3, 3, 2]):
            grid.columnconfigure(i, weight=w)
        grid.rowconfigure(0, weight=1)

        # --- Panel PC-A ---
        panelA = self._make_panel(grid, "💻 PC-A (EMISOR)", "ENCAPSULAMIENTO 7 → 1", GREEN)
        panelA.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.rowsA = {}
        for l in ENC_ORDER:
            row = LayerRow(panelA.body, l, "A", self.on_layer_click)
            row.pack(fill="x", pady=3)
            self.rowsA[l["n"]] = row

        # --- Panel Canal ---
        panelC = self._make_panel(grid, "", "", BLUE)
        panelC.grid(row=0, column=1, sticky="nsew", padx=8)
        self._build_channel(panelC.body)

        # --- Panel PC-B ---
        panelB = self._make_panel(grid, "💻 PC-B (RECEPTOR)", "DESENCAPSULAMIENTO 1 → 7", ORANGE)
        panelB.grid(row=0, column=2, sticky="nsew", padx=8)
        self.rowsB = {}
        for l in DEC_ORDER:
            row = LayerRow(panelB.body, l, "B", self.on_layer_click)
            row.pack(fill="x", pady=3)
            self.rowsB[l["n"]] = row

        # --- Panel Info de capa ---
        panelI = self._make_panel(grid, "⚙ INFORMACIÓN DE LA CAPA", "", PURPLE)
        panelI.grid(row=0, column=3, sticky="nsew", padx=(8, 0))
        self._build_info_panel(panelI.body)

    def _make_panel(self, master, title, subtitle, accent=ACCENT):
        outer = tk.Frame(master, bg=BG)
        strip = tk.Frame(outer, bg=accent, height=3)
        strip.pack(fill="x")
        panel = tk.Frame(outer, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        panel.pack(fill="both", expand=True)
        if title:
            tk.Label(panel, text=title, bg=PANEL, fg=TXT, font=FONT_BOLD,
                      anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        if subtitle:
            tk.Label(panel, text=subtitle, bg=PANEL, fg=MUTED, font=FONT_SMALL,
                      anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        body = tk.Frame(panel, bg=PANEL)
        body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        outer.body = body
        outer.panel = panel
        return outer

    def _build_channel(self, parent):
        tk.Label(parent, text="CANAL DE COMUNICACIÓN M/M/1", bg=PANEL2, fg=MUTED,
                  font=FONT_SMALL, padx=10, pady=4).pack(pady=(0, 10))

        self.canal_canvas = tk.Canvas(parent, height=110, bg=PANEL, highlightthickness=0)
        self.canal_canvas.pack(fill="x", pady=(0, 10))
        self.canal_canvas.bind("<Configure>", self._draw_wire)

        packet = tk.Frame(parent, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        packet.pack(fill="x", pady=(0, 10))
        tk.Label(packet, text="PAQUETE DE DATOS", bg=PANEL2, fg=MUTED,
                  font=FONT_SMALL).pack(pady=(6, 2))
        chip = tk.Frame(packet, bg=PANEL2)
        chip.pack(pady=(0, 8))
        for c in [GREEN, ORANGE, PURPLE, BLUE]:
            tk.Frame(chip, bg=c, width=34, height=14).pack(side="left", padx=2)

        prog = tk.Frame(parent, bg=PANEL2, highlightthickness=1, highlightbackground=BORDER)
        prog.pack(fill="x")
        tk.Label(prog, text="⏱ TRANSFERENCIA EN CURSO", bg=PANEL2, fg=MUTED,
                  font=FONT_SMALL).pack(anchor="w", padx=10, pady=(8, 4))

        self.progress_canvas = tk.Canvas(prog, height=10, bg="#16233f", highlightthickness=0)
        self.progress_canvas.pack(fill="x", padx=10)
        self.progress_bar = self.progress_canvas.create_rectangle(0, 0, 0, 10, fill=ACCENT, width=0)

        row1 = tk.Frame(prog, bg=PANEL2)
        row1.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(row1, text="Capa actual:", bg=PANEL2, fg=MUTED, font=FONT_SMALL).pack(side="left")
        self.lbl_cur_layer = tk.Label(row1, text="—", bg=PANEL2, fg=TXT, font=FONT_BOLD)
        self.lbl_cur_layer.pack(side="left", padx=6)

        row2 = tk.Frame(prog, bg=PANEL2)
        row2.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(row2, text="PDU:", bg=PANEL2, fg=MUTED, font=FONT_SMALL).pack(side="left")
        self.lbl_cur_pdu = tk.Label(row2, text="—", bg=PANEL2, fg=ACCENT, font=FONT_BOLD)
        self.lbl_cur_pdu.pack(side="left", padx=(4, 16))
        tk.Label(row2, text="Estado:", bg=PANEL2, fg=MUTED, font=FONT_SMALL).pack(side="left")
        self.lbl_cur_estado = tk.Label(row2, text="Detenido", bg=PANEL2, fg=ACCENT, font=FONT_BOLD)
        self.lbl_cur_estado.pack(side="left", padx=4)

    def _draw_wire(self, event=None):
        c = self.canal_canvas
        c.delete("all")
        w = c.winfo_width() or 400
        c.create_text(30, 25, text="💻", font=("Segoe UI Emoji", 22), fill=TXT, anchor="w")
        c.create_text(30, 50, text="PC-A", font=FONT_SMALL, fill=MUTED, anchor="w")
        c.create_text(w - 30, 25, text="💻", font=("Segoe UI Emoji", 22), fill=TXT, anchor="e")
        c.create_text(w - 30, 50, text="PC-B", font=FONT_SMALL, fill=MUTED, anchor="e")
        c.create_line(70, 25, w - 70, 25, fill=BLUE, width=2)
        for x in range(90, w - 80, 28):
            c.create_oval(x, 21, x + 5, 26, fill=ACCENT, outline="")
        self.wire_arrow = c.create_text(w // 2, 25, text="▶", fill=ACCENT, font=("Segoe UI", 12, "bold"))

    def _build_info_panel(self, parent):
        def kv(label):
            f = tk.Frame(parent, bg=PANEL)
            f.pack(fill="x", pady=6)
            tk.Label(f, text=label, bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w").pack(fill="x")
            val = tk.Label(f, text="—", bg=PANEL, fg=TXT, font=FONT_BASE, anchor="w",
                            wraplength=220, justify="left")
            val.pack(fill="x")
            return val

        self.if_capa = kv("Capa")
        self.if_funcion = kv("Función")
        self.if_pdu = kv("PDU")
        self.if_info = kv("Información agregada")

        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=6)
        tk.Label(f, text="Estado", bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w").pack(fill="x")
        self.if_estado = tk.Label(f, text="Detenido", bg=PANEL, fg=ACCENT, font=FONT_BOLD, anchor="w")
        self.if_estado.pack(fill="x")

        self.if_datos = kv("Datos actuales")

        f2 = tk.Frame(parent, bg=PANEL)
        f2.pack(fill="x", pady=6)
        tk.Label(f2, text="En Base64 (Presentación)", bg=PANEL, fg=MUTED,
                  font=FONT_SMALL, anchor="w").pack(fill="x")
        self.if_b64 = tk.Label(f2, bg=PANEL2, fg=PURPLE, font=FONT_MONO, anchor="w",
                                wraplength=220, justify="left", padx=6, pady=6)
        self.if_b64.pack(fill="x")

        f3 = tk.Frame(parent, bg=PANEL)
        f3.pack(fill="x", pady=6)
        tk.Label(f3, text="Visualización del PDU", bg=PANEL, fg=MUTED,
                  font=FONT_SMALL, anchor="w").pack(fill="x")
        self.pdu_flow = tk.Frame(f3, bg=PANEL)
        self.pdu_flow.pack(fill="x", pady=4)

    # -------------------------------------------------- BOTTOM ---------
    def _build_bottom(self):
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="both", expand=False, padx=14, pady=(0, 14))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        bottom.columnconfigure(2, weight=1)

        consoleA = self._make_console(bottom, "🖥 CONSOLA PC-A (Eventos)", GREEN)
        consoleA.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.console_a = consoleA.txt

        consoleB = self._make_console(bottom, "🖥 CONSOLA PC-B (Eventos)", ORANGE)
        consoleB.grid(row=0, column=1, sticky="nsew", padx=8)
        self.console_b = consoleB.txt

        result_outer = tk.Frame(bottom, bg=BG)
        result_outer.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        tk.Frame(result_outer, bg=ACCENT, height=3).pack(fill="x")
        result = tk.Frame(result_outer, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        result.pack(fill="both", expand=True)
        self.result_frame = result
        self._build_result(result)

    def _make_console(self, master, title, accent):
        outer = tk.Frame(master, bg=BG)
        tk.Frame(outer, bg=accent, height=3).pack(fill="x")
        frame = tk.Frame(outer, bg="#040c1c", highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=title, bg="#040c1c", fg=TXT, font=FONT_BOLD,
                  anchor="w").pack(fill="x", padx=10, pady=(8, 4))
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x", padx=10)

        body = tk.Frame(frame, bg="#040c1c")
        body.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        txt = tk.Text(body, height=11, bg="#040c1c", fg=MUTED, insertbackground=TXT,
                      relief="flat", font=FONT_MONO, wrap="word", bd=0,
                      highlightthickness=0, padx=4, pady=2)
        scroll = tk.Scrollbar(body, command=txt.yview, bg="#0b1730", troughcolor="#040c1c",
                               activebackground=accent, relief="flat", bd=0, width=10)
        txt.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.tag_config("out", foreground=ACCENT)
        txt.tag_config("in", foreground=ORANGE)
        txt.tag_config("dim", foreground=MUTED)
        txt.config(state="disabled")
        frame = outer
        frame.txt = txt
        return frame

    def _build_result(self, parent):
        for w in parent.winfo_children():
            w.destroy()
        self.result_content = tk.Frame(parent, bg=PANEL)
        self.result_content.pack(fill="both", expand=True, padx=16, pady=16)

    def _show_result_placeholder(self):
        for w in self.result_content.winfo_children():
            w.destroy()
        tk.Label(self.result_content, text="Esperando finalización de la transmisión…",
                  bg=PANEL, fg=MUTED, font=FONT_SMALL, wraplength=200,
                  justify="center").pack(expand=True)

    def _show_result_success(self):
        for w in self.result_content.winfo_children():
            w.destroy()
        canvas = tk.Canvas(self.result_content, width=44, height=44, bg=PANEL, highlightthickness=0)
        canvas.create_oval(2, 2, 42, 42, fill=GREEN, outline="")
        canvas.create_text(22, 22, text="✓", fill="#04101f", font=("Segoe UI", 16, "bold"))
        canvas.pack(pady=(0, 8))
        tk.Label(self.result_content, text="¡ÉXITO!", bg=PANEL, fg=TXT,
                  font=("Segoe UI", 13, "bold")).pack()
        tk.Label(self.result_content, text="El mensaje fue recuperado correctamente.",
                  bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(pady=(2, 10))
        box = tk.Label(self.result_content, text=f'"{self.msg}"', bg=PANEL2, fg=ACCENT,
                        font=FONT_BOLD, wraplength=220, pady=10, padx=6)
        box.pack(fill="x")

        elapsed = round(time.time() - self.start_time, 1) if self.start_time else 0
        stats = tk.Frame(self.result_content, bg=PANEL)
        stats.pack(fill="x", pady=(12, 0))
        for col, (val, label) in enumerate([
            (f"{elapsed} s", "Tiempo total"),
            ("7 / 7", "Capas procesadas"),
            ("Auto" if not self.step_mode else "Paso a paso", "Modo"),
        ]):
            f = tk.Frame(stats, bg=PANEL)
            f.grid(row=0, column=col, padx=4)
            tk.Label(f, text=val, bg=PANEL, fg=TXT, font=FONT_BOLD).pack()
            tk.Label(f, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 7)).pack()

    # -------------------------------------------------- LOGICA ---------
    def log(self, widget, text, tag):
        widget.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        arrow = ">>>" if tag == "out" else "<<<"
        widget.insert("end", f"[{ts}] ", "dim")
        widget.insert("end", f"{arrow} ", tag)
        widget.insert("end", f"{text}\n")
        widget.see("end")
        widget.config(state="disabled")

    def clear_console(self, widget):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.config(state="disabled")

    def set_progress(self, pct, animate=True):
        if self.prog_anim_id:
            self.after_cancel(self.prog_anim_id)
            self.prog_anim_id = None
        if not animate:
            self.prog_current = pct
            self._draw_progress(pct)
            return
        self._animate_progress(self.prog_current, pct)

    def _animate_progress(self, start, end, step=0):
        steps = 10
        t = step / steps
        value = start + (end - start) * t
        self._draw_progress(value)
        if step < steps:
            self.prog_anim_id = self.after(16, lambda: self._animate_progress(start, end, step + 1))
        else:
            self.prog_current = end

    def _draw_progress(self, pct):
        c = self.progress_canvas
        w = c.winfo_width() or 300
        c.coords(self.progress_bar, 0, 0, w * pct / 100, 10)

    def update_info_panel(self, layer, phase):
        self.if_capa.config(text=f'Capa {layer["n"]} - {layer["name"]}')
        self.if_funcion.config(text=layer["fn"])
        self.if_pdu.config(text=layer["pdu"])
        self.if_info.config(text=layer["add"])
        estado = "Encapsulando" if phase == "enc" else "Desencapsulando"
        self.if_estado.config(text=estado)
        self.if_datos.config(text=self.msg)
        self.if_b64.config(text=base64.b64encode(self.msg.encode("utf-8")).decode())
        self.lbl_cur_layer.config(text=f'{layer["n"]} - {layer["name"]}')
        self.lbl_cur_pdu.config(text=layer["pdu"])
        self.lbl_cur_estado.config(text=f"{estado}...")

    def push_pdu_chip(self, label, color):
        chip = tk.Label(self.pdu_flow, text=label, bg=color, fg="white",
                          font=("Segoe UI", 8, "bold"), padx=8, pady=3)
        chip.pack(side="left", padx=2, pady=2)

    def reset_all(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.running = False
        self.step_index = 0
        self.start_time = None
        self.msg = self.msg_entry.get().strip() or "Mensaje de prueba"

        self.clear_console(self.console_a)
        self.clear_console(self.console_b)
        for row in list(self.rowsA.values()) + list(self.rowsB.values()):
            row.set_state("idle")
        self.set_progress(0, animate=False)
        self.lbl_cur_layer.config(text="—")
        self.lbl_cur_pdu.config(text="—")
        self.lbl_cur_estado.config(text="Detenido")
        self.if_capa.config(text="—")
        self.if_funcion.config(text="—")
        self.if_pdu.config(text="—")
        self.if_info.config(text="—")
        self.if_estado.config(text="Detenido")
        self.if_datos.config(text="—")
        self.if_b64.config(text="—")
        for w in self.pdu_flow.winfo_children():
            w.destroy()
        self._show_result_placeholder()
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="normal")
        self.btn_next.config(state="normal")
        self._update_next_hint()

    def do_step(self):
        if self.start_time is None:
            self.start_time = time.time()

        if self.step_index < 7:
            layer = ENC_ORDER[self.step_index]
            for row in self.rowsA.values():
                if row.state == "active":
                    row.set_state("done")
            self.rowsA[layer["n"]].set_state("active")
            self.update_info_panel(layer, "enc")
            self.log(self.console_a, f'Capa {layer["n"]} - {layer["name"]}: {layer["add"]}', "out")
            self.push_pdu_chip(layer["pdu"].split(" ")[0], layer["color"])

        elif self.step_index == 7:
            self.log(self.console_a, "Envío al canal de comunicación...", "out")
            self.rowsA[1].set_state("done")
            self.lbl_cur_estado.config(text="Transmitiendo por el canal...")
            self.if_estado.config(text="Transmitiendo")

        elif self.step_index < 15:
            idx = self.step_index - 8
            layer = DEC_ORDER[idx]
            if self.step_index == 8:
                self.log(self.console_b, "Paquete recibido desde el canal", "in")
            for row in self.rowsB.values():
                if row.state == "active":
                    row.set_state("done")
            self.rowsB[layer["n"]].set_state("active")
            self.update_info_panel(layer, "dec")
            if layer["n"] == 1:
                verb = "Bits recibidos"
            elif layer["n"] == 7:
                verb = "Mensaje recuperado"
            elif layer["n"] == 2:
                verb = "Se elimina Header y Trailer"
            else:
                verb = "Se elimina Header"
            self.log(self.console_b, f'Capa {layer["n"]} - {layer["name"]}: {verb}', "in")
            if layer["n"] == 7:
                self.rowsB[7].set_state("done")

        pct = min(100, round(((self.step_index + 1) / TOTAL_STEPS) * 100))
        self.set_progress(pct)
        self.step_index += 1
        self._update_next_hint()

        if self.step_index >= TOTAL_STEPS:
            self.finish()
            return False
        return True

    def _get_next_expected(self):
        """Devuelve (lado, numero_de_capa) del siguiente paso pendiente, o (None, None)."""
        if self.step_index < 7:
            return "A", ENC_ORDER[self.step_index]["n"]
        elif self.step_index == 7:
            return None, None  # paso de transmisión: no corresponde a una capa clicable
        elif self.step_index < 15:
            return "B", DEC_ORDER[self.step_index - 8]["n"]
        return None, None

    def _update_next_hint(self):
        """Resalta en dorado la capa que corresponde procesar a continuación."""
        for row in list(self.rowsA.values()) + list(self.rowsB.values()):
            if row.state not in ("done", "active"):
                row.set_state("idle")
        side, n = self._get_next_expected()
        if side == "A":
            self.rowsA[n].set_state("next")
        elif side == "B":
            self.rowsB[n].set_state("next")

    def on_layer_click(self, side, n):
        """El usuario hizo clic sobre una capa: muestra su información y,
        si es la próxima capa pendiente, avanza la simulación con ese clic."""
        layer = next(l for l in LAYERS if l["n"] == n)
        phase = "enc" if side == "A" else "dec"
        self.update_info_panel(layer, phase)

        expected_side, expected_n = self._get_next_expected()
        if side == expected_side and n == expected_n:
            if self.after_id:
                self.after_cancel(self.after_id)
                self.after_id = None
            self.running = False
            self.do_step()

    def finish(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.running = False
        self.lbl_cur_estado.config(text="Completado")
        self.if_estado.config(text="Completado")
        self.btn_pause.config(state="disabled")
        self.btn_next.config(state="disabled")
        self.btn_start.config(state="disabled")
        self._show_result_success()

    def auto_loop(self):
        if not self.running:
            return
        cont = self.do_step()
        if cont:
            self.after_id = self.after(900, self.auto_loop)

    # -------------------------------------------------- HANDLERS -------
    def on_start(self):
        if self.running:
            return
        self.step_mode = (self.mode_var.get() == "step")
        if self.step_index == 0:
            self.msg = self.msg_entry.get().strip() or "Mensaje de prueba"
        self.running = True
        if self.step_mode:
            self.do_step()
            self.running = False
        else:
            self.auto_loop()

    def on_pause(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.lbl_cur_estado.config(text="Pausado")

    def on_next(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.step_index < TOTAL_STEPS:
            self.do_step()


if __name__ == "__main__":
    app = SimuladorOSI()
    app.mainloop()