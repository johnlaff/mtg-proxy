import os
import re
import subprocess
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

def criar_pdf_com_cartas(
    pasta_cartas: str,
    pdf_saida: str,
    colunas: int = 3,
    linhas: int = 3,
    largura_carta_mm: float = 63,
    altura_carta_mm: float = 88
):
    """
    Cria um PDF A4 com as cartas presentes em 'pasta_cartas'. Cada página terá até 9 cartas
    dispostas em uma grade 3x3, centralizadas na folha. São desenhadas 4 linhas verticais e 4
    horizontais que se estendem por toda a página, em cor cinza claro.
    
    Se o nome de uma carta contiver um padrão do tipo "(Nx)" (por exemplo, "(5x)nome.png"),
    essa carta será repetida N vezes no PDF.
    
    Para reduzir o tamanho final do PDF, o script utiliza:
      - Um cache de imagens, para que a mesma imagem seja incorporada apenas uma vez.
      - Compressão de página, habilitada no canvas.
    
    Parâmetros:
      - pasta_cartas: Pasta onde as imagens das cartas estão armazenadas.
      - pdf_saida: Caminho/nome do PDF a ser gerado (ex.: "cartas_A4.pdf").
      - colunas: Número de colunas da grade (padrão 3).
      - linhas: Número de linhas da grade (padrão 3).
      - largura_carta_mm: Largura da carta em milímetros (padrão 63 mm).
      - altura_carta_mm: Altura da carta em milímetros (padrão 88 mm).
    """
    print("Iniciando criação do PDF...")
    
    # Tamanho da página A4 (em pontos)
    pagina_largura, pagina_altura = A4
    print(f"Tamanho da página A4: {pagina_largura:.2f} x {pagina_altura:.2f} pts")
    
    # Converte dimensões das cartas para pontos
    carta_width = largura_carta_mm * mm
    carta_height = altura_carta_mm * mm
    print(f"Dimensões da carta: {largura_carta_mm} mm x {altura_carta_mm} mm -> {carta_width:.2f} x {carta_height:.2f} pts")
    
    # Dimensão total da grade de cartas
    grid_width = colunas * carta_width
    grid_height = linhas * carta_height
    print(f"Dimensão total da grade: {grid_width:.2f} x {grid_height:.2f} pts")
    
    # Margens para centralizar a grade na página A4
    margem_x = (pagina_largura - grid_width) / 2
    margem_y = (pagina_altura - grid_height) / 2
    print(f"Margens calculadas: margem_x = {margem_x:.2f} pts, margem_y = {margem_y:.2f} pts")
    
    # Cria o canvas com compressão de página habilitada
    c = canvas.Canvas(pdf_saida, pagesize=A4, pageCompression=1)
    print("Canvas criado com compressão habilitada.")
    
    # Extensões de imagem aceitas
    extensoes = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp')
    
    # Lista e ordena os arquivos da pasta das cartas
    arquivos = sorted([
        f for f in os.listdir(pasta_cartas)
        if f.lower().endswith(extensoes)
    ])
    print(f"Encontrados {len(arquivos)} arquivos na pasta '{pasta_cartas}'.")
    
    # Regex para identificar padrão do tipo "(Nx)" no nome do arquivo
    pattern = re.compile(r'\((\d+)x\)')
    
    # Expande a lista de imagens, repetindo o arquivo conforme o número indicado
    caminhos_imagens = []
    for f in arquivos:
        count = 1  # padrão se não houver indicação de repetição
        match = pattern.search(f)
        if match:
            try:
                count = int(match.group(1))
                print(f"Arquivo '{f}' contém padrão de repetição: {count}x")
            except ValueError:
                print(f"Falha ao interpretar o padrão de repetição em '{f}'. Usando 1x como padrão.")
                count = 1
        else:
            print(f"Arquivo '{f}' não contém padrão de repetição. Adicionando 1 vez.")
        for _ in range(count):
            caminhos_imagens.append(os.path.join(pasta_cartas, f))
    print(f"Total de imagens após expansão: {len(caminhos_imagens)}")
    
    total_cartas_por_pagina = colunas * linhas
    print(f"Cada página terá até {total_cartas_por_pagina} cartas.")
    
    # Cache de imagens para evitar repetição desnecessária no PDF
    image_cache = {}
    
    # Processa as imagens em grupos (cada grupo corresponde a uma página A4)
    num_paginas = 0
    for i in range(0, len(caminhos_imagens), total_cartas_por_pagina):
        num_paginas += 1
        grupo = caminhos_imagens[i:i + total_cartas_por_pagina]
        print(f"\nProcessando página {num_paginas} com {len(grupo)} cartas...")
    
        # Posiciona cada carta na grade (primeira carta no canto superior esquerdo)
        for idx, caminho_imagem in enumerate(grupo):
            col = idx % colunas
            linha_from_top = idx // colunas  # índice da linha a partir do topo
            x = margem_x + col * carta_width
            y = margem_y + grid_height - (linha_from_top + 1) * carta_height
            print(f"  Inserindo carta {idx+1}: coluna {col+1}, linha {linha_from_top+1} -> x={x:.2f}, y={y:.2f}")
    
            # Se a imagem não estiver no cache, cria um ImageReader
            if caminho_imagem not in image_cache:
                try:
                    image_cache[caminho_imagem] = ImageReader(caminho_imagem)
                    print(f"    Imagem '{caminho_imagem}' adicionada ao cache.")
                except Exception as e:
                    print(f"    Erro ao carregar a imagem '{caminho_imagem}': {e}")
                    continue
            img_obj = image_cache[caminho_imagem]
    
            # Desenha a imagem mantendo a transparência
            c.drawImage(
                img_obj,
                x,
                y,
                width=carta_width,
                height=carta_height,
                preserveAspectRatio=True,
                anchor='c',
                mask='auto'
            )
            print("    Carta desenhada.")
    
        # Desenha as linhas de corte (linhas contínuas, cor cinza claro)
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        print("  Desenhando linhas de corte...")
    
        for col in range(0, colunas + 1):
            x = margem_x + col * carta_width
            c.line(x, 0, x, pagina_altura)
            print(f"    Linha vertical {col+1} desenhada em x = {x:.2f}")
    
        for linha in range(0, linhas + 1):
            y = margem_y + linha * carta_height
            c.line(0, y, pagina_largura, y)
            print(f"    Linha horizontal {linha+1} desenhada em y = {y:.2f}")
    
        c.showPage()
        print(f"Página {num_paginas} finalizada.")
    
    c.save()
    print(f"\nPDF gerado com sucesso: {pdf_saida}")
    print(f"Total de páginas geradas: {num_paginas}")

def compress_pdf(input_pdf, output_pdf, ghostscript_path="gswin64c.exe", settings="/prepress"):
    """
    Chama o Ghostscript para comprimir o PDF.
    
    Parâmetros:
      - input_pdf: Caminho do PDF original.
      - output_pdf: Caminho do PDF comprimido.
      - ghostscript_path: Caminho para o executável do Ghostscript.
      - settings: Parâmetro para -dPDFSETTINGS (ex.: /prepress, /printer, /ebook, /screen).
    """
    # Verifica se o Ghostscript está instalado
    if not shutil.which(ghostscript_path):
        print("Ghostscript não está instalado ou não está no PATH. Pule a compressão.")
        return

    cmd = [
        ghostscript_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={settings}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_pdf}",
        input_pdf
    ]
    try:
        print("Iniciando compressão do PDF via Ghostscript...")
        subprocess.run(cmd, check=True)
        print(f"PDF comprimido com sucesso: {output_pdf}")
    except subprocess.CalledProcessError as e:
        print(f"Erro na compressão do PDF: {e}")

if __name__ == '__main__':
    # Pasta onde estão as cartas processadas (imagens com fundo original/transparente)
    pasta_cartas = "cartas"
    # Nome do PDF de saída (antes da compressão)
    pdf_saida = "cartas_A4.pdf"
    
    criar_pdf_com_cartas(pasta_cartas, pdf_saida)
    
    # Após gerar o PDF, chama o Ghostscript para comprimi-lo
    pdf_comprimido = "cartas_A4_comprimido.pdf"
    compress_pdf(pdf_saida, pdf_comprimido, ghostscript_path="gswin64c.exe", settings="/prepress")
