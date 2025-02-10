import os
import sys
import json
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from io import BytesIO
import requests
from PIL import Image, ImageTk

# Diretório onde as imagens serão baixadas
IMAGES_DIR = "imagens"
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# Função para buscar a carta (busca única) – busca em inglês para obter o oracle_id
def buscar_carta(card_name):
    url = "https://api.scryfall.com/cards/named"
    params = {"exact": card_name, "lang": "en"}
    headers = {"Accept": "application/json", "User-Agent": "CardSearchApp/1.0"}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Função para buscar todos os prints de uma carta dado o oracle_id e idioma
def buscar_prints(oracle_id, lang):
    query = f"oracleid:{oracle_id} lang:{lang} unique:prints"
    url = "https://api.scryfall.com/cards/search"
    params = {"q": query}
    prints = []
    while url:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            break
        data = response.json()
        prints.extend(data.get("data", []))
        if data.get("has_more"):
            url = data.get("next_page")
            params = {}
        else:
            url = None
    return prints

# Função para obter o URL da arte em qualidade máxima (PNG)
def obter_url_maxima(card):
    if "card_faces" in card and card["card_faces"]:
        face = card["card_faces"][0]
        if "image_uris" in face and "png" in face["image_uris"]:
            return face["image_uris"]["png"]
    elif "image_uris" in card and "png" in card["image_uris"]:
        return card["image_uris"]["png"]
    return None

# Função para realizar uma requisição HEAD e obter o tamanho (em MB) da imagem
def get_image_size_mb(url):
    try:
        head = requests.head(url)
        if "Content-Length" in head.headers:
            size_bytes = int(head.headers["Content-Length"])
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.2f} MB"
    except Exception as e:
        return "Tamanho desconhecido"
    return "Tamanho desconhecido"

# Função para abrir uma nova janela com a imagem em tamanho original
def visualizar_imagem(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            img_data = response.content
            pil_img = Image.open(BytesIO(img_data))
        else:
            messagebox.showerror("Erro", "Não foi possível carregar a imagem.")
            return
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar imagem: {e}")
        return

    top = tk.Toplevel()
    top.title("Visualização da Imagem")
    img_width, img_height = pil_img.size
    screen_width = top.winfo_screenwidth()
    screen_height = top.winfo_screenheight()
    max_width = int(screen_width * 0.8)
    max_height = int(screen_height * 0.8)
    if img_width > max_width or img_height > max_height:
        ratio = min(max_width / img_width, max_height / img_height)
        pil_img = pil_img.resize((int(img_width * ratio), int(img_height * ratio)), Image.LANCZOS)
    photo = ImageTk.PhotoImage(pil_img)
    lbl = tk.Label(top, image=photo)
    lbl.image = photo
    lbl.pack()
    size_info = get_image_size_mb(url)
    info_lbl = tk.Label(top, text=f"Tamanho da imagem: {size_info}")
    info_lbl.pack()

# Função para limpar a pasta de imagens (baixadas)
def limpar_pasta():
    for f in os.listdir(IMAGES_DIR):
        path = os.path.join(IMAGES_DIR, f)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            pass

# Função para baixar uma imagem e salvá-la na pasta IMAGES_DIR
def baixar_imagem(url, filename):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filepath = os.path.join(IMAGES_DIR, filename)
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filepath
    except Exception as e:
        return None

# Classe que implementa a GUI de busca de cartas
class CardSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Busca de Cartas - Scryfall")
        self.root.geometry("900x700")
        self.selected_cards = []  # Armazenará os cards selecionados para download
        self.thumbnail_cache = {}  # Cache para thumbnails

        self.tabControl = ttk.Notebook(root)
        self.tab_single = ttk.Frame(root)
        self.tab_bulk = ttk.Frame(root)
        self.tabControl.add(self.tab_single, text="Busca Única")
        self.tabControl.add(self.tab_bulk, text="Busca em Massa")
        self.tabControl.pack(expand=1, fill="both", padx=10, pady=10)

        self.create_single_tab()
        self.create_bulk_tab()
        self.create_log_area()

    def create_single_tab(self):
        frame = self.tab_single
        lbl = ttk.Label(frame, text="Digite o nome exato da carta:")
        lbl.pack(pady=5)
        self.entry_card = ttk.Entry(frame, width=50)
        self.entry_card.pack(pady=5)
        btn_buscar = ttk.Button(frame, text="Buscar Carta", command=self.buscar_carta_single)
        btn_buscar.pack(pady=10)
        filtro_frame = ttk.Frame(frame)
        filtro_frame.pack(pady=5)
        ttk.Label(filtro_frame, text="Filtrar por idioma:").pack(side=tk.LEFT, padx=5)
        self.filtro_var = tk.StringVar(value="en")
        self.combo_filtro = ttk.Combobox(filtro_frame, textvariable=self.filtro_var, state="readonly", width=15)
        self.combo_filtro['values'] = ("en", "pt", "ambos")
        self.combo_filtro.pack(side=tk.LEFT, padx=5)
        btn_filtrar = ttk.Button(filtro_frame, text="Aplicar Filtro", command=self.aplicar_filtro)
        btn_filtrar.pack(side=tk.LEFT, padx=5)
        self.results_frame_single = ttk.Frame(frame)
        self.canvas_single = tk.Canvas(self.results_frame_single, height=300)
        self.scrollbar_single = ttk.Scrollbar(self.results_frame_single, orient="vertical", command=self.canvas_single.yview)
        self.scrollable_frame_single = ttk.Frame(self.canvas_single)
        self.scrollable_frame_single.bind("<Configure>", lambda e: self.canvas_single.configure(scrollregion=self.canvas_single.bbox("all")))
        self.canvas_single.create_window((0, 0), window=self.scrollable_frame_single, anchor="nw")
        self.canvas_single.configure(yscrollcommand=self.scrollbar_single.set)
        self.results_frame_single.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas_single.pack(side="left", fill="both", expand=True)
        self.scrollbar_single.pack(side="right", fill="y")
        btn_download = ttk.Button(frame, text="Baixar Imagens Selecionadas", command=self.baixar_imagens)
        btn_download.pack(pady=5)

    def create_bulk_tab(self):
        frame = self.tab_bulk
        lbl = ttk.Label(frame, text="Cole sua lista de cartas (um por linha):")
        lbl.pack(pady=5)
        self.text_bulk = scrolledtext.ScrolledText(frame, width=70, height=10)
        self.text_bulk.pack(pady=5)
        filtro_frame = ttk.Frame(frame)
        filtro_frame.pack(pady=5)
        ttk.Label(filtro_frame, text="Filtrar por idioma:").pack(side=tk.LEFT, padx=5)
        self.bulk_filtro_var = tk.StringVar(value="en")
        self.combo_bulk_filtro = ttk.Combobox(filtro_frame, textvariable=self.bulk_filtro_var, state="readonly", width=15)
        self.combo_bulk_filtro['values'] = ("en", "pt", "ambos")
        self.combo_bulk_filtro.pack(side=tk.LEFT, padx=5)
        btn_bulk = ttk.Button(frame, text="Buscar Lista de Cartas", command=self.buscar_carta_bulk)
        btn_bulk.pack(pady=10)
        self.results_frame_bulk = ttk.Frame(frame)
        self.canvas_bulk = tk.Canvas(self.results_frame_bulk, height=300)
        self.scrollbar_bulk = ttk.Scrollbar(self.results_frame_bulk, orient="vertical", command=self.canvas_bulk.yview)
        self.scrollable_frame_bulk = ttk.Frame(self.canvas_bulk)
        self.scrollable_frame_bulk.bind("<Configure>", lambda e: self.canvas_bulk.configure(scrollregion=self.canvas_bulk.bbox("all")))
        self.canvas_bulk.create_window((0, 0), window=self.scrollable_frame_bulk, anchor="nw")
        self.canvas_bulk.configure(yscrollcommand=self.scrollbar_bulk.set)
        self.results_frame_bulk.pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas_bulk.pack(side="left", fill="both", expand=True)
        self.scrollbar_bulk.pack(side="right", fill="y")
        btn_download_bulk = ttk.Button(frame, text="Baixar Imagens Selecionadas", command=self.baixar_imagens)
        btn_download_bulk.pack(pady=5)

    def create_log_area(self):
        self.log_text = scrolledtext.ScrolledText(self.root, width=90, height=10)
        self.log_text.pack(pady=10)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def carregar_imagem_thumbnail(self, url):
        if url in self.thumbnail_cache:
            return self.thumbnail_cache[url]
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.content
                pil_img = Image.open(BytesIO(data))
                pil_img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(pil_img)
                self.thumbnail_cache[url] = photo
                return photo
        except Exception as e:
            self.log(f"Erro ao carregar thumbnail: {e}")
        return None

    def exibir_resultados(self, resultados):
        # Se estivermos na aba Bulk, aplicar filtro antes de agrupar
        if self.tabControl.index("current") == 1:
            filtro = self.bulk_filtro_var.get()
            if filtro != "ambos":
                resultados = [card for card in resultados if card.get("lang") == filtro]
            groups = {}
            for card in resultados:
                name = card.get("name", "N/A")
                groups.setdefault(name, []).append(card)
            lista_grupos = []
            for name in sorted(groups.keys()):
                edicoes = {}
                for card in groups[name]:
                    key = (card.get("set_name", "").lower(), str(card.get("collector_number", "")).lower())
                    edicoes.setdefault(key, []).append(card)
                opcoes = []
                for key, cards in edicoes.items():
                    # Se houver ambas as versões, cria um par; se só houver uma, usa-a para ambas
                    if len(cards) >= 2:
                        # Ordena de forma que a versão em inglês venha primeiro
                        cards_sorted = sorted(cards, key=lambda c: 0 if c.get("lang")=="en" else 1)
                        opcoes.append((cards_sorted[0], cards_sorted[1]))
                    else:
                        opcoes.append((cards[0], cards[0]))
                lista_grupos.append((name, opcoes))
            self.exibir_resultados_bulk(lista_grupos)
        else:
            # Aba única: exibe os resultados individualmente
            for widget in self.scrollable_frame_single.winfo_children():
                widget.destroy()
            container = self.scrollable_frame_single
            self.selected_cards = []
            filtro = self.filtro_var.get()
            lista_resultados = [card for card in resultados if card.get("lang") == filtro]
            for idx, card in enumerate(lista_resultados):
                frame = ttk.Frame(container, relief=tk.RIDGE, borderwidth=2)
                frame.pack(fill="x", pady=5, padx=5)
                txt = f"{card.get('name', 'N/A')} - {card.get('set_name', 'N/A')} #{card.get('collector_number', 'N/A')}"
                lbl = ttk.Label(frame, text=txt)
                lbl.pack(anchor="w", padx=5, pady=2)
                url = obter_url_maxima(card)
                if url:
                    img = self.carregar_imagem_thumbnail(url)
                    lbl_img = ttk.Label(frame, image=img)
                    lbl_img.image = img
                    lbl_img.pack(side="left", padx=5)
                    lbl_img.bind("<Button-1>", lambda e, url=url: visualizar_imagem(url))
                    size = get_image_size_mb(url)
                    ttk.Label(frame, text=f"Tamanho: {size}").pack(side="left", padx=5)
                btn = ttk.Button(frame, text="Selecionar esta arte", command=lambda c=card: self.adicionar_selecionado(c))
                btn.pack(anchor="e", padx=5, pady=5)

    def exibir_resultados_bulk(self, groups):
        for widget in self.scrollable_frame_bulk.winfo_children():
            widget.destroy()
        container = self.scrollable_frame_bulk
        self.selected_cards = []
        # Para cada grupo (nome da carta, edições)
        for name, edicoes in groups:
            # Use tk.Frame para permitir destaque (borda verde)
            group_frame = tk.Frame(container, bd=2, relief="solid")
            group_frame.pack(fill="x", pady=5, padx=5)
            lbl_name = ttk.Label(group_frame, text=name, font=("Segoe UI", 12, "bold"))
            lbl_name.pack(anchor="w", padx=5, pady=2)
            # Se houver mais de uma edição, exibe um combobox para seleção
            if len(edicoes) > 1:
                mapping = {}
                values = []
                for edicao in edicoes:
                    option = f"{edicao[0].get('set_name', 'N/A')} #{edicao[0].get('collector_number', 'N/A')}"
                    mapping[option] = edicao
                    values.append(option)
                combo = ttk.Combobox(group_frame, values=values, state="readonly", width=40)
                combo.current(0)
                combo.mapping = mapping
                combo.pack(anchor="w", padx=5)
            else:
                mapping = {f"{edicoes[0][0].get('set_name', 'N/A')} #{edicoes[0][0].get('collector_number', 'N/A')}": edicoes[0]}
                combo = ttk.Combobox(group_frame, values=list(mapping.keys()), state="readonly", width=40)
                combo.current(0)
                combo.mapping = mapping
                combo.pack(anchor="w", padx=5)
            def update_preview(event, grp=group_frame, cmb=combo):
                option = cmb.get()
                par = cmb.mapping.get(option)
                self.atualizar_preview_bulk(grp, par)
            combo.bind("<<ComboboxSelected>>", update_preview)
            # Cria o frame para o preview e armazena uma tag para posterior limpeza
            preview_frame = ttk.Frame(group_frame)
            preview_frame.pack(fill="x", padx=5, pady=5)
            preview_frame.preview_tag = True
            self.atualizar_preview_bulk(group_frame, combo.mapping.get(combo.get()))
            # Checkbutton para confirmar a escolha com borda verde
            var = tk.IntVar(value=0)
            def on_confirm(grp=group_frame, cmb=combo, v=var):
                if v.get() == 1:
                    grp.config(highlightthickness=2, highlightbackground="green")
                    sel_par = cmb.mapping.get(cmb.get())
                    if sel_par:
                        # Exibe as duas versões lado a lado, mas a seleção final opta pela versão em inglês se disponível; caso contrário, a em português.
                        card = sel_par[0] if sel_par[0].get("lang")=="en" else sel_par[1]
                        if card:
                            url = obter_url_maxima(card)
                            if url and not any(item.get("print_url") == url for item in self.selected_cards):
                                self.selected_cards.append({
                                    "card_name": card.get("name", "N/A"),
                                    "print_url": url,
                                    "set_name": card.get("set_name", "N/A"),
                                    "collector_number": card.get("collector_number", "N/A")
                                })
                                self.log(f"Selecionada: {card.get('name', 'N/A')} - {card.get('set_name', 'N/A')} #{card.get('collector_number', 'N/A')}")
                else:
                    grp.config(highlightthickness=0)
            chk = ttk.Checkbutton(group_frame, text="Confirmar", variable=var, command=lambda grp=group_frame, cmb=combo, v=var: on_confirm(grp, cmb, v))
            chk.pack(anchor="e", padx=5, pady=5)

    def atualizar_preview_bulk(self, parent_frame, par):
        # Remove previews antigos que estejam abaixo do combobox
        for widget in parent_frame.pack_slaves():
            if getattr(widget, "preview_tag", None):
                widget.destroy()
        preview_frame = ttk.Frame(parent_frame)
        preview_frame.pack(fill="x", padx=5, pady=5)
        preview_frame.preview_tag = True
        if par:
            en_card, pt_card = par
            # Exibir as duas versões lado a lado, se disponíveis
            if en_card:
                url_en = obter_url_maxima(en_card)
                if url_en:
                    photo_en = self.carregar_imagem_thumbnail(url_en)
                    lbl_en = ttk.Label(preview_frame, image=photo_en)
                    lbl_en.image = photo_en
                    lbl_en.pack(side="left", padx=5)
                    lbl_en.bind("<Button-1>", lambda e, url=url_en: visualizar_imagem(url))
                    ttk.Label(preview_frame, text=f"Inglês ({get_image_size_mb(url_en)})").pack(side="left", padx=5)
            if pt_card:
                url_pt = obter_url_maxima(pt_card)
                if url_pt:
                    photo_pt = self.carregar_imagem_thumbnail(url_pt)
                    lbl_pt = ttk.Label(preview_frame, image=photo_pt)
                    lbl_pt.image = photo_pt
                    lbl_pt.pack(side="left", padx=5)
                    lbl_pt.bind("<Button-1>", lambda e, url=url_pt: visualizar_imagem(url))
                    ttk.Label(preview_frame, text=f"Português ({get_image_size_mb(url_pt)})").pack(side="left", padx=5)

    def adicionar_selecionado(self, card):
        url = obter_url_maxima(card)
        if url:
            for item in self.selected_cards:
                if item.get("print_url") == url:
                    return
            self.selected_cards.append({
                "card_name": card.get("name", "N/A"),
                "print_url": url,
                "set_name": card.get("set_name", "N/A"),
                "collector_number": card.get("collector_number", "N/A")
            })
            self.log(f"Selecionada: {card.get('name', 'N/A')} - {card.get('set_name', 'N/A')} #{card.get('collector_number', 'N/A')}")

    def baixar_imagens(self):
        if not self.selected_cards:
            messagebox.showwarning("Aviso", "Nenhuma imagem selecionada.")
            return
        self.log("Iniciando download das imagens selecionadas...")
        for item in self.selected_cards:
            url = item.get("print_url")
            if url:
                filename = os.path.basename(url.split("?")[0])
                filepath = baixar_imagem(url, filename)
                if filepath:
                    self.log(f"Baixada: {filepath}")
                else:
                    self.log(f"Falha ao baixar: {url}")
        self.log("Download concluído.")

    def aplicar_filtro(self):
        filtro = self.filtro_var.get()
        card_name = self.entry_card.get().strip()
        if not card_name:
            return
        self.log(f"Aplicando filtro: {filtro}")
        card = buscar_carta(card_name)
        if not card:
            self.log("Carta não encontrada.")
            return
        oracle_id = card.get("oracle_id")
        if not oracle_id:
            self.log("Oracle ID não encontrado.")
            return
        prints_en = buscar_prints(oracle_id, lang="en")
        prints_pt = buscar_prints(oracle_id, lang="pt")
        for p in prints_en:
            p['lang'] = "en"
        for p in prints_pt:
            p['lang'] = "pt"
        if filtro == "ambos":
            resultados = prints_en + prints_pt
        else:
            resultados = [p for p in (prints_en + prints_pt) if p.get("lang") == filtro]
        self.exibir_resultados(resultados)

    def buscar_carta_single(self):
        card_name = self.entry_card.get().strip()
        if not card_name:
            messagebox.showwarning("Aviso", "Digite o nome de uma carta.")
            return
        self.log(f"Buscando carta: {card_name}")
        card = buscar_carta(card_name)
        if not card:
            self.log("Carta não encontrada.")
            return
        oracle_id = card.get("oracle_id")
        if not oracle_id:
            self.log("Oracle ID não encontrado.")
            return
        prints_en = buscar_prints(oracle_id, lang="en")
        prints_pt = buscar_prints(oracle_id, lang="pt")
        for p in prints_en:
            p['lang'] = "en"
        for p in prints_pt:
            p['lang'] = "pt"
        resultados = prints_en + prints_pt
        self.exibir_resultados(resultados)

    def buscar_carta_bulk(self):
        bulk_text = self.text_bulk.get("1.0", tk.END).strip()
        if not bulk_text:
            messagebox.showwarning("Aviso", "Cole a lista de cartas.")
            return
        linhas = bulk_text.splitlines()
        resultados = []
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            match = re.match(r'(\d+)(x)?\s+(.*)', linha)
            if match:
                quantidade = int(match.group(1))
                card_nome = match.group(3).split('(')[0].strip()
            else:
                quantidade = 1
                card_nome = linha
            self.log(f"Buscando carta: {card_nome}")
            card = buscar_carta(card_nome)
            if not card:
                self.log(f"Carta '{card_nome}' não encontrada.")
                continue
            oracle_id = card.get("oracle_id")
            if not oracle_id:
                self.log(f"Oracle ID não encontrado para '{card_nome}'.")
                continue
            prints_en = buscar_prints(oracle_id, lang="en")
            prints_pt = buscar_prints(oracle_id, lang="pt")
            for p in prints_en:
                p['lang'] = "en"
            for p in prints_pt:
                p['lang'] = "pt"
            for _ in range(quantidade):
                resultados.extend(prints_en + prints_pt)
        self.exibir_resultados(resultados)

def main():
    root = tk.Tk()
    app = CardSearchGUI(root)
    app.thumbnail_cache = {}
    root.mainloop()

if __name__ == "__main__":
    main()
