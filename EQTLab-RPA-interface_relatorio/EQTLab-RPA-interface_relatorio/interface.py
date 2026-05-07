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


def pasta_programa():
    
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent  # quando vira .exe
    return Path(__file__).parent  # quando roda como .py


def pasta_recursos():
    # pega a pasta dos arquivos embutidos no .exe
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def salvar_config(modo, inicio=None, fim=None):
    # caminho do arquivo de configuracao
    caminho = pasta_programa() / "config" / "endpoints.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)  # cria a pasta config se faltar

    # copia o config padrao se ainda nao existir
    if not caminho.exists():
        padrao = pasta_recursos() / "config" / "endpoints.json"
        if padrao.exists() and padrao != caminho:
            shutil.copy(padrao, caminho)

    # le o config atual
    if caminho.exists():
        config = json.loads(caminho.read_text(encoding="utf-8"))
    else:
        config = {"endpoints": []}

    # salva o modo escolhido
    config["date_filter_mode"] = modo
    config["custom_start_date"] = inicio if modo == "custom" else None
    config["custom_end_date"] = fim if modo == "custom" else None

    # grava no arquivo
    caminho.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


class log_handler(logging.Handler):
    # manda os logs para a tela
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record):
        self.app.after(0, self.app.escrever_log, self.format(record))


class app(ctk.CTk):
    def __init__(self):
        super().__init__()

        # aparencia da janela
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("gerador de relatorios rpa")
        self.geometry("900x650")
        self.configure(fg_color="white")

        # guarda o modo e as datas
        self.modo = ctk.StringVar(value="monthly")
        self.data_inicio = None
        self.data_fim = None

        self.carregar_icone()
        self.criar_tela()

        # ativa os logs na interface
        logging.getLogger().addHandler(log_handler(self))
        logging.getLogger().setLevel(logging.INFO)

        self.mostrar_datas()

    def carregar_icone(self):
        try:
            icone = pasta_recursos() / "getsitelogo.ico"
            if icone.exists():
                self.iconbitmap(str(icone))  # icone da janela
        except Exception:
            pass  # se der erro no icone, o programa continua

    def criar_tela(self):
        # titulo principal
        ctk.CTkLabel(
            self,
            text="extracao de relatorios rpa",
            font=("Arial", 24, "bold"),
            text_color="black"
        ).pack(pady=20)

        # area principal
        self.frame = ctk.CTkFrame(self, fg_color="#f5f5f5")
        self.frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            self.frame,
            text="1. selecione o periodo:",
            font=("Arial", 16, "bold"),
            text_color="black"
        ).pack(anchor="w", padx=20, pady=10)

        # opcoes de periodo
        for valor, texto in [
            ("monthly", "mensal"),
            ("weekly", "semanal"),
            ("daily", "diario"),
        ]:
            ctk.CTkRadioButton(
                self.frame,
                text=texto,
                variable=self.modo,
                value=valor,
                command=self.mostrar_datas,
                text_color="black"
            ).pack(anchor="w", padx=40, pady=5)

        # modo personalizado
        linha = ctk.CTkFrame(self.frame, fg_color="transparent")
        linha.pack(anchor="w", padx=40, pady=5, fill="x")

        ctk.CTkRadioButton(
            linha,
            text="personalizado",
            variable=self.modo,
            value="custom",
            command=self.mostrar_datas,
            text_color="black"
        ).pack(side="left")

        # area das datas
        self.frame_datas = ctk.CTkFrame(linha, fg_color="transparent")
        hoje = dt.date.today()

        ctk.CTkLabel(
            self.frame_datas,
            text="formato dd/mm/aaaa | inicio:",
            text_color="black"
        ).pack(side="left", padx=(15, 5))

        self.entrada_inicio = ctk.CTkEntry(
            self.frame_datas,
            width=120,
            fg_color="white",
            text_color="black"
        )
        self.entrada_inicio.pack(side="left")
        self.entrada_inicio.insert(0, hoje.replace(day=1).strftime("%d/%m/%Y"))
        self.entrada_inicio.bind("<KeyRelease>", self.formatar_data)  # coloca as barras

        ctk.CTkLabel(
            self.frame_datas,
            text="fim:",
            text_color="black"
        ).pack(side="left", padx=(15, 5))

        self.entrada_fim = ctk.CTkEntry(
            self.frame_datas,
            width=120,
            fg_color="white",
            text_color="black"
        )
        self.entrada_fim.pack(side="left")
        self.entrada_fim.insert(0, hoje.strftime("%d/%m/%Y"))
        self.entrada_fim.bind("<KeyRelease>", self.formatar_data)  # coloca as barras automaticamente

        # botao principal (de executtar)
        self.botao = ctk.CTkButton(
            self.frame,
            text="executar",
            command=self.iniciar,
            font=("Arial", 15, "bold")
        )
        self.botao.pack(pady=20, padx=40, fill="x")

        ctk.CTkLabel(
            self.frame,
            text="2. logs:",
            font=("Arial", 16, "bold"),
            text_color="black"
        ).pack(anchor="w", padx=20)

        # caixa logs
        self.caixa_log = ctk.CTkTextbox(
            self.frame,
            font=("Consolas", 12),
            fg_color="white",
            text_color="black"
        )
        self.caixa_log.pack(fill="both", expand=True, padx=20, pady=10)
        self.caixa_log.configure(state="disabled")

    def mostrar_datas(self):
        # so mostra as datas se o modo for personalizado tipo um pop up
        if self.modo.get() == "custom":
            self.frame_datas.pack(side="left")
        else:
            self.frame_datas.pack_forget()

    def formatar_data(self, event):
        # pega o campo que a pessoa digitou
        campo = event.widget

        # deixa so numeros e limita a 8 digitos
        numeros = "".join(c for c in campo.get() if c.isdigit())[:8]

        # monta no formato dd/mm/aaaa
        if len(numeros) <= 2:
            texto = numeros
        elif len(numeros) <= 4:
            texto = f"{numeros[:2]}/{numeros[2:]}"
        else:
            texto = f"{numeros[:2]}/{numeros[2:4]}/{numeros[4:]}"

        campo.delete(0, "end")
        campo.insert(0, texto)

    def escrever_log(self, texto):
        # escreve uma linha na caixa de log
        self.caixa_log.configure(state="normal")
        self.caixa_log.insert("end", texto + "\n")
        self.caixa_log.see("end")  # desce a barra
        self.caixa_log.configure(state="disabled")

    def limpar_log(self):
        # apaga os logs antigos
        self.caixa_log.configure(state="normal")
        self.caixa_log.delete("1.0", "end")
        self.caixa_log.configure(state="disabled")

    def validar_datas(self):
        try:
            # converte o que foi digitado em data
            inicio = dt.datetime.strptime(self.entrada_inicio.get().strip(), "%d/%m/%Y")
            fim = dt.datetime.strptime(self.entrada_fim.get().strip(), "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("erro", "digite a data no formato dd/mm/aaaa.")
            return False

        # verifica se a data inicial e menor que a final
        if inicio > fim:
            messagebox.showerror("erro", "a data de inicio deve ser menor que a data de fim.")
            return False

        # converte para o formato usado no rpa
        self.data_inicio = inicio.strftime("%Y-%m-%d")
        self.data_fim = fim.strftime("%Y-%m-%d")
        return True

    def iniciar(self):
        # limpa dados antigos
        self.data_inicio = None
        self.data_fim = None
        modo = self.modo.get()

        # se for personalizado, valida as datas
        if modo == "custom":
            if not self.validar_datas():
                return
            salvar_config(modo, self.data_inicio, self.data_fim)
        else:
            salvar_config(modo)

        # prepara a tela para executar
        self.botao.configure(state="disabled", text="extraindo...")
        self.limpar_log()
        self.escrever_log(f"iniciando extracao no modo: {modo}")

        # roda sem travar a interface
        threading.Thread(target=self.executar, daemon=True).start()

    def executar(self):
        try:
            # chama o rpa principal
            if self.modo.get() == "custom":
                main_module.main(self.data_inicio, self.data_fim)
            else:
                main_module.main()
        except Exception as erro:
            logging.error(f"erro durante a execucao: {erro}")
        finally:
            # libera a interface no final
            self.after(0, lambda: self.botao.configure(state="normal", text="executar"))
            self.after(0, lambda: self.escrever_log("extracao finalizada."))


if __name__ == "__main__":
    app().mainloop()  
