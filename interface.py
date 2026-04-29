import tkinter as tk, threading, subprocess, sys, json, datetime as dt
from tkinter import messagebox
from pathlib import Path

# gerenciamento de arquivo json
def patch_config(mode: str, start: str = "", end: str = ""):
    p = Path(__file__).parent / "config" / "endpoints.json"
    p.parent.mkdir(parents=True, exist_ok=True)

    config = {"endpoints": []}
    if p.exists():
        try: config = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError: pass

    config["date_filter_mode"] = mode
    if mode == "custom":
        config.update({"custom_start_date": start, "custom_end_date": end})
    else:
        for k in ("custom_start_date", "custom_end_date"): config.pop(k, None)

    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

# interface grafica via tkinter
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Aplicação de Relatórios RPA")
        self.geometry("900x600")
        self.configure(bg="#F7F8FC")

        self.mode = tk.StringVar(value="monthly")

        tk.Label(self, text="Aplicação de Relatórios RPA", font=("Arial", 14, "bold"),
                 bg="#3B82F6", fg="white", pady=15).pack(fill="x")

        tk.Label(self, text="Selecione o período de extração:",
                 bg="#F7F8FC", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(15, 5))

        for val, txt in [("monthly", "Mensal"), ("weekly", "Semanal"), ("daily", "Diário")]:
            tk.Radiobutton(self, text=txt, variable=self.mode, value=val,
                           command=self.toggle_dates, bg="#F7F8FC").pack(anchor="w", padx=30)

        self.fr_custom = tk.Frame(self, bg="#F7F8FC")
        self.fr_custom.pack(anchor="w", padx=30, fill="x")
        tk.Radiobutton(self.fr_custom, text="Personalizado, Inserir a data em formato ANO/MÊS/DIA", variable=self.mode,
                       value="custom", command=self.toggle_dates,
                       bg="#F7F8FC").pack(side="left")

        self.fr_dt = tk.Frame(self.fr_custom, bg="#FFFFFF", relief="solid", bd=1, padx=5, pady=5)

        hoje = dt.date.today()
        tk.Label(self.fr_dt, text="Início:", bg="#FFFFFF").pack(side="left")
        self.e_start = tk.Entry(self.fr_dt, width=11); self.e_start.pack(side="left", padx=(2, 10))
        self.e_start.insert(0, hoje.replace(day=1).strftime("%Y/%m/%d"))

        tk.Label(self.fr_dt, text="Fim:", bg="#FFFFFF").pack(side="left")
        self.e_end = tk.Entry(self.fr_dt, width=11); self.e_end.pack(side="left")
        self.e_end.insert(0, hoje.strftime("%Y/%m/%d"))

        self.btn = tk.Button(self, text="Executar Extração", bg="#22C55E", fg="white",
                             font=("Arial", 11, "bold"), pady=8, command=self.run)
        self.btn.pack(pady=20, fill="x", padx=20)

        tk.Label(self, text="Log:", bg="#F7F8FC").pack(anchor="w", padx=20)
        self.log = tk.Text(self, bg="#1E1E2E", fg="#CDD6F4", state="disabled")
        self.log.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.toggle_dates()

    # logica e eventos
    def toggle_dates(self):
        if self.mode.get() == "custom": self.fr_dt.pack(side="left", padx=10)
        else: self.fr_dt.pack_forget()

    def add_log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.config(state="disabled")

    def run(self):
        mode = self.mode.get()
        if mode == "custom":
            try:
                s = dt.datetime.strptime(self.e_start.get().replace("-", "/"), "%Y/%m/%d").strftime("%Y-%m-%d")
                e = dt.datetime.strptime(self.e_end.get().replace("-", "/"), "%Y/%m/%d").strftime("%Y-%m-%d")
                if s > e: return messagebox.showerror("Erro", "Data inicial maior que final!")
                patch_config(mode, s, e)
            except ValueError:
                return messagebox.showerror("Erro", "Formato inválido! Ex: 2026/02/09")
        else: patch_config(mode)

        self.btn.config(state="disabled", bg="#6B7280", text="Executando...")
        self.log.config(state="normal"); self.log.delete("1.0", tk.END); self.log.config(state="disabled")
        self.add_log(f"[{dt.datetime.now():%H:%M:%S}] Iniciando modo: {mode}")
        threading.Thread(target=self.executar, daemon=True).start()

    def executar(self):
        try:
            cmd = [sys.executable, str(Path(__file__).parent / "main.py"),
                   "--date", dt.date.today().isoformat()]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)

            for line in proc.stdout: self.after(0, self.add_log, line.rstrip())
            proc.wait()
            self.after(0, self.add_log, "Processo finalizado!")
        except Exception as e:
            self.after(0, self.add_log, f"Erro: {e}")
        finally:
            self.after(0, lambda: self.btn.config(state="normal",
                                                  bg="#22C55E",
                                                  text="Executar Extração"))

if __name__ == "__main__":
    App().mainloop()
