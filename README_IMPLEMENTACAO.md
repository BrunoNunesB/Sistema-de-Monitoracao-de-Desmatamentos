# Estudo de Deteção de Mudanças em Imagens de Satélite com OpenCV

Aplicação desktop desenvolvida em Python para estudo e demonstração de técnicas de **Processamento Digital de Imagens (PDI)** e **Visão Computacional**, focada na identificação de alterações de cobertura vegetal (desmatamento/mudança de solo agrícola) através da comparação de pares de imagens ("Antes" vs "Depois").

## Tecnologias Utilizadas

* **Python 3.14**
* **OpenCV (`opencv-python`)**: Pipeline de PDI (ExG, conversão HSV, limiarização por Otsu, operações morfológicas, contornos e desenho de áreas).
* **NumPy**: Manipulação matricial dos canais BGR.
* **CustomTkinter**: Interface gráfica moderna disposta em grid 2x2.
* **Pillow (PIL)**: Conversão e renderização de imagens na interface.

## Pipeline de Processamento (PDI)

O algoritmo executa localmente as seguintes etapas:

1. **Leitura e Redimensionamento**: Carregamento em formato BGR nativo do OpenCV e compatibilização de dimensões.
2. **Índice Excess Green (ExG)**: Cálculo do índice (2G - R - B) para destacar a vegetação em cada período.
3. **Subtração de Verde**: Diferença direta entre os índices para isolar a perda de vegetação.
4. **Máscara Urbana (Espaço HSV)**: Filtragem por saturação de cor para ignorar zonas urbanas acinzentadas e vias.
5. **Limiarização por Otsu**: Binarização automática do resultado filtrado.
6. **Morfologia Matemática**: Operações de abertura (`MORPH_OPEN`) e fechamento (`MORPH_CLOSE`) com kernel estipulado para remoção de ruídos de alta frequência.
7. **Filtragem de Contornos**: Deteção de regiões alteradas e destaque visual com preenchimento semi-transparente.

## Instalação e Execução

## 1. Como Obter as Imagens de Entrada (Google Earth Pro)

1. Abra o **Google Earth Pro** no computador e navegue até à área de interesse.
2. Anote a **Altitude do Ponto de Visão** exibida no canto inferior direito (ex: `Alt. ponto de visão 3.00 km` = `3000 m`).
2. Ative o **Histórico de Imagens** no ícone de relógio no menu superior (`Ctrl + Alt + S`).
3. Selecione uma data antiga na linha do tempo (ex: 2020) e clique em **Ficheiro -> Guardar -> Guardar Imagem...**.
4. Em **Opções do Mapa**, desmarque todos os elementos visuais (escala, bússola, legenda) e guarde como `antes.jpg`.
5. **Sem alterar o zoom ou a posição do mapa**, altere a linha do tempo para uma data recente e guarde como `depois.jpg`.

## 2. Clonar o repositório e instalar as dependências
```bash
python -m pip install -r requirements.txt
```