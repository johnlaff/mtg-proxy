import os
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import threading

from proxy import converter_para_63x88_mm
from pdf import criar_pdf_com_cartas, compress_pdf

# Diretórios e nomes de arquivos
IMAGES_DIR = "imagens"        # Pasta com as imagens originais
CONVERTED_DIR = "cartas"      # Pasta com as imagens convertidas pelo proxy.py
PDF_OUTPUT = "cartas_A4.pdf"
PDF_COMPRESSED = "cartas_A4_comprimido.pdf"

def log_message(widget, message):
    """Adiciona uma mensagem ao widget de log e rola para o final."""
    widget.insert(tk.END, message + "\n")
    widget.see(tk.END)

def run_thread(func, *args, **kwargs):
    """Executa a função em uma thread separada para evitar travar a interface."""
    t = threading.Thread(target=func, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()

def convert_images(log_widget):
    """Converte as imagens originais usando o proxy.py."""
    try:
        log_message(log_widget, "Iniciando conversão de imagens...")
        converter_para_63x88_mm(IMAGES_DIR, CONVERTED_DIR, dpi=600)
        log_message(log_widget, "Conversão de imagens concluída.")
    except Exception as e:
        log_message(log_widget, f"Erro na conversão: {e}")

def generate_pdf(log_widget):
    """Gera o PDF usando as imagens convertidas e depois o comprime."""
    try:
        log_message(log_widget, "Iniciando criação do PDF...")
        criar_pdf_com_cartas(CONVERTED_DIR, PDF_OUTPUT)
        log_message(log_widget, "PDF gerado. Iniciando compressão...")
        compress_pdf(PDF_OUTPUT, PDF_COMPRESSED, ghostscript_path="gswin64c.exe", settings="/prepress")
        if os.path.exists(PDF_COMPRESSED):
            size_bytes = os.path.getsize(PDF_COMPRESSED)
            size_mb = size_bytes / (1024 * 1024)
            log_message(log_widget, f"PDF comprimido com sucesso. Tamanho: {size_mb:.2f} MB")
        else:
            log_message(log_widget, "PDF comprimido não encontrado após compressão.")
    except Exception as e:
        log_message(log_widget, f"Erro na geração do PDF: {e}")

def open_pdf(log_widget):
    """Abre o PDF comprimido no visualizador padrão do sistema."""
    try:
        if not os.path.exists(PDF_COMPRESSED):
            messagebox.showerror("Erro", "PDF não encontrado. Gere o PDF primeiro.")
            return
        log_message(log_widget, f"Abrindo PDF: {PDF_COMPRESSED}")
        if sys.platform.startswith("win"):
            os.startfile(PDF_COMPRESSED)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", PDF_COMPRESSED])
        else:
            subprocess.Popen(["xdg-open", PDF_COMPRESSED])
    except Exception as e:
        log_message(log_widget, f"Erro ao abrir o PDF: {e}")

def clear_folders(log_widget):
    """Remove todos os arquivos das pastas de imagens originais e convertidas."""
    try:
        for folder in [IMAGES_DIR, CONVERTED_DIR]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            import shutil
                            shutil.rmtree(file_path)
                        log_message(log_widget, f"Removido: {file_path}")
                    except Exception as e:
                        log_message(log_widget, f"Erro ao remover {file_path}: {e}")
        log_message(log_widget, "Pastas limpadas com sucesso.")
    except Exception as e:
        log_message(log_widget, f"Erro na limpeza: {e}")

def create_gui():
    """Cria a janela principal da interface gráfica."""
    root = tk.Tk()
    root.title("Gerenciador de Cartas")
    root.geometry("600x400")
    
    # Frame para os botões de ação
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    
    btn_convert = tk.Button(btn_frame, text="Converter Imagens", width=20, command=lambda: run_thread(convert_images, log_text))
    btn_pdf = tk.Button(btn_frame, text="Gerar PDF", width=20, command=lambda: run_thread(generate_pdf, log_text))
    btn_open = tk.Button(btn_frame, text="Abrir PDF", width=20, command=lambda: run_thread(open_pdf, log_text))
    btn_clear = tk.Button(btn_frame, text="Limpar Pastas", width=20, command=lambda: run_thread(clear_folders, log_text))
    
    btn_convert.grid(row=0, column=0, padx=5, pady=5)
    btn_pdf.grid(row=0, column=1, padx=5, pady=5)
    btn_open.grid(row=1, column=0, padx=5, pady=5)
    btn_clear.grid(row=1, column=1, padx=5, pady=5)
    
    # Área de log com scrollbar
    global log_text
    log_text = scrolledtext.ScrolledText(root, width=70, height=15)
    log_text.pack(pady=10)
    
    return root

def main():
    root = create_gui()
    root.mainloop()

if __name__ == "__main__":
    main()
