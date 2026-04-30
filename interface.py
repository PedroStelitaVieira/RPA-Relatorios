import customtkinter as ctk
import threading
import sys
import json
import datetime as dt
import logging
import shutil
from tkinter import messagebox
from pathlib import Path
import main as main_module

# Gerenciador de Configurações
def patch_config(modo: str, s: str = "", e: str = ""):
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent 
    else:
        base = Path(__file__).parent
        
    cfg_path = base / "config" / "endpoints.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Restaura arquivo padrão se não existir no executável
    if not cfg_path.exists() and getattr(sys, 'frozen', False):
        default = Path(sys._MEIPASS) / "config" / "endpoints.json"
        if default.exists(): 
            shutil.copy(default, cfg_path)
            
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text("utf-8")) 
    else:
        cfg = {"endpoints": []}
        
    if modo == "custom":
        cfg.update({
            "date_filter_mode": modo, 
            "custom_start_date": s, 
            "custom_end_date": e
        }) 
    else: 
        cfg.update({
            "date_filter_mode": modo, 
            "custom_start_date": None, 
            "custom_end_date": None
        })
        
    cfg_path.write_text(json.dumps(cfg, indent=2), "utf-8")

# Capturador de Logs para a Interface
class TextHandler(logging.Handler):
    def __init__(self, f): 
        super().__init__()
        self.f = f
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        
    def emit(self, record): 
        self.f(self.format(record))

# Interface Gráfica
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração principal da janela
        self.title("Gerador de Relatórios RPA")
        self.geometry("900x650")
        ctk.set_appearance_mode("dark")
        self.mode = ctk.StringVar(value="monthly")
        
        # Cabeçalho
        lbl_titulo = ctk.CTkLabel(self, text="Extração de Relatórios RPA", font=("Segoe UI", 24, "bold"), text_color="#3B82F6")
        lbl_titulo.pack(pady=20)
        
        # Quadro Principal
        mf = ctk.CTkFrame(self)
        mf.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Seleção de Período
        lbl_periodo = ctk.CTkLabel(mf, text="1. Selecione o período:", font=("Segoe UI", 16, "bold"))
        lbl_periodo.pack(anchor="w", padx=20, pady=10)
        
        # Opções
        opcoes = [
            ("monthly", "Mensal"), 
            ("weekly", "Semanal"), 
            ("daily", "Diário")
        ]
        
        for v, t in opcoes: 
            rb = ctk.CTkRadioButton(mf, text=t, variable=self.mode, value=v, command=self.toggle)
            rb.pack(anchor="w", padx=40, pady=5)
            
        # Opção Personalizada e Datas na mesma linha
        fr_custom_linha = ctk.CTkFrame(mf, fg_color="transparent")
        fr_custom_linha.pack(anchor="w", padx=40, pady=5, fill="x")
        
        rb_custom = ctk.CTkRadioButton(fr_custom_linha, text="Personalizado", variable=self.mode, value="custom", command=self.toggle)
        rb_custom.pack(side="left")
        
        # Quadro de Datas (ao lado do rádio)
        self.fr_dt = ctk.CTkFrame(fr_custom_linha, fg_color="transparent")
        hoje = dt.date.today()
        
        lbl_inicio = ctk.CTkLabel(self.fr_dt, text="Inserir em formato Ano/Mês/Dia    ----->   Inicio:")
        lbl_inicio.pack(side="left", padx=(15, 5))
        
        self.e_start = ctk.CTkEntry(self.fr_dt, width=110)
        self.e_start.pack(side="left")
        self.e_start.insert(0, hoje.replace(day=1).strftime("%Y/%m/%d"))
        
        lbl_fim = ctk.CTkLabel(self.fr_dt, text="Fim:")
        lbl_fim.pack(side="left", padx=(15, 5))
        
        self.e_end = ctk.CTkEntry(self.fr_dt, width=110)
        self.e_end.pack(side="left")
        self.e_end.insert(0, hoje.strftime("%Y/%m/%d"))
        
        # Botão Executar
        self.btn = ctk.CTkButton(mf, text="Executar", font=("Segoe UI", 15, "bold"), height=40, command=self.run)
        self.btn.pack(pady=20, padx=40, fill="x")
        
        # Painel de Logs
        lbl_logs = ctk.CTkLabel(mf, text="2. Logs:", font=("Segoe UI", 16, "bold"))
        lbl_logs.pack(anchor="w", padx=20)
        
        self.log = ctk.CTkTextbox(mf, font=("Consolas", 12), text_color="#38BDF8", state="disabled")
        self.log.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configurações finais
        self.toggle()
        
        log_handler = TextHandler(lambda m: self.after(0, self.add_log, m))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def toggle(self): 
        """Exibe os campos de data se a opção 'Personalizado' for selecionada."""
        if self.mode.get() == "custom":
            self.fr_dt.pack(side="left") 
        else:
            self.fr_dt.pack_forget()

    def add_log(self, msg): 
        """Adiciona uma mensagem ao painel de logs."""
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
    
    def run(self):
        """Prepara as configurações e inicia a extração."""
        m = self.mode.get()
        if m == "custom":
            try:
                data_inicio = dt.datetime.strptime(self.e_start.get().replace("-", "/"), "%Y/%m/%d").strftime("%Y-%m-%d")
                data_fim = dt.datetime.strptime(self.e_end.get().replace("-", "/"), "%Y/%m/%d").strftime("%Y-%m-%d")
                
                if data_inicio > data_fim: 
                    return messagebox.showerror("Atenção", "Data inicial maior que final!")
                    
                patch_config(m, data_inicio, data_fim)
            except: 
                return messagebox.showerror("Erro", "Formato de data inválido!")
        else: 
            patch_config(m)
        
        # Muda estado do botão
        self.btn.configure(state="disabled", text="Extraindo...")
        
        # Limpa o log
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        
        self.add_log(f"[{dt.datetime.now():%H:%M:%S}] Iniciando: {m}")
        
        # Inicia extração em plano de fundo
        threading.Thread(target=self.executar, daemon=True).start()

    def executar(self):
        """Executa a função principal do robô."""
        try: 
            parametros = ["--date", dt.date.today().isoformat()]
            main_module.main(parametros)
            self.after(0, self.add_log, "Sucesso!")
        except Exception as e: 
            self.after(0, self.add_log, f"Erro: {e}")
        finally: 
            self.after(0, lambda: self.btn.configure(state="normal", text="Executar"))

if __name__ == "__main__": 
    App().mainloop()
