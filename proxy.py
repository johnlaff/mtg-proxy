import os
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

def redimensionar_manter_proporcao(img, largura_alvo, altura_alvo):
    """
    Redimensiona a imagem mantendo a proporção e depois corta (crop) central
    para caber exatamente em largura_alvo x altura_alvo (px).
    """
    largura_original, altura_original = img.size
    ratio_alvo = largura_alvo / altura_alvo
    ratio_original = largura_original / altura_original

    if ratio_original > ratio_alvo:
        nova_altura = altura_alvo
        nova_largura = int(nova_altura * ratio_original)
    else:
        nova_largura = largura_alvo
        nova_altura = int(nova_largura / ratio_original)

    img_redim = img.resize((nova_largura, nova_altura), Image.LANCZOS)
    esquerda = (nova_largura - largura_alvo) // 2
    topo = (nova_altura - altura_alvo) // 2
    direita = esquerda + largura_alvo
    fundo = topo + altura_alvo
    img_cortada = img_redim.crop((esquerda, topo, direita, fundo))
    return img_cortada

def process_image(caminho_arquivo, pasta_saida, largura_px, altura_px, dpi):
    """
    Processa uma única imagem: abre, converte para RGBA (se necessário), redimensiona,
    realiza o crop central e salva como PNG com otimização.
    """
    nome_arquivo = os.path.basename(caminho_arquivo)
    nome_saida = os.path.splitext(nome_arquivo)[0] + '.png'
    caminho_saida = os.path.join(pasta_saida, nome_saida)
    
    # Se o arquivo de saída já existe, pula o processamento.
    if os.path.exists(caminho_saida):
        return f"Arquivo '{nome_saida}' já existe. Pulando..."
    
    try:
        with Image.open(caminho_arquivo) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img_final = redimensionar_manter_proporcao(img, largura_px, altura_px)
            img_final.save(caminho_saida, format="PNG", dpi=(dpi, dpi), optimize=True, compress_level=9)
        return f"Salvou otimizada para impressão: {caminho_saida}"
    except Exception as e:
        return f"Erro ao processar '{caminho_arquivo}': {e}"

def converter_para_63x88_mm(pasta_entrada: str, pasta_saida: str, dpi: int = 600, num_workers: int = None):
    """
    Redimensiona todas as imagens de 'pasta_entrada' para 63x88 mm na resolução especificada (dpi)
    e salva em 'pasta_saida' usando multiprocessing para acelerar o processamento.
    
    Parâmetros:
      - pasta_entrada: Pasta com as imagens originais.
      - pasta_saida: Pasta onde as imagens processadas serão salvas.
      - dpi: Resolução para impressão (ex.: 600).
      - num_workers: Número de processos simultâneos (padrão é None, que usa o máximo disponível).
    """
    # Converte 63x88 mm para pixels (usando dpi)
    largura_px = int((63 / 25.4) * dpi)
    altura_px  = int((88 / 25.4) * dpi)

    # Cria a pasta de entrada, se não existir   
    if not os.path.exists(pasta_entrada):
        os.makedirs(pasta_entrada)
    
    # Cria a pasta de saída, se não existir
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
    
    # Lista os arquivos de imagem da pasta de entrada
    extensoes = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp')
    arquivos = [os.path.join(pasta_entrada, f) for f in os.listdir(pasta_entrada)
                if f.lower().endswith(extensoes)]
    
    print(f"Iniciando o processamento de {len(arquivos)} imagens...")

    # Processa as imagens em paralelo utilizando ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(process_image, caminho, pasta_saida, largura_px, altura_px, dpi)
            for caminho in arquivos
        ]
        
        # À medida que cada processamento termina, imprime o resultado
        for future in as_completed(futures):
            resultado = future.result()
            print(resultado)

if __name__ == "__main__":
    pasta_entrada = "imagens"   # Pasta com as imagens originais
    pasta_saida   = "cartas"     # Pasta onde as imagens processadas serão salvas
    converter_para_63x88_mm(pasta_entrada, pasta_saida, dpi=600)
