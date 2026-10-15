import ee
import geemap

# ==========================================
# ETAPA 1: Autenticação e Inicialização
# ==========================================
# Tenta inicializar especificando o projeto padrão ou force a criação
try:
    ee.Initialize(project='ID projeto') # ID do projeto no earthEngine
except Exception:
    ee.Authenticate()
    ee.Initialize()



# ==========================================
# ETAPA 2: Configuração da Área e Raio de Pesquisa
# ==========================================
ponto = ee.Geometry.Point([-47.77803374652221, -21.168033859743986])  # Ribeirão Preto / SP
aoi = ponto.buffer(10000)                                             # Raio de 10 km



# ==========================================
# ETAPA 3: Processamento e Cálculo do NDVI
# ==========================================
def adicionar_ndvi(imagem): # Função para receber a imagem de satélite
    return imagem.addBands(imagem.normalizedDifference(['B8', 'B4']).rename('NDVI')) # Aplica a fórmula do NDVI

sentinel = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')     # Acessa as imagens do earthEngine
            .filterBounds(aoi)                                    # Filtra a região de interesse
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))  # Filtra imagens sem nuvens
            .map(adicionar_ndvi))                                 # Aplica a função nas imagens

ndvi_2022 = sentinel.filterDate('2022-06-01', '2022-09-30').median().clip(aoi).select('NDVI') # Faz o mesmo que em cima mas nas datas especificas
ndvi_2024 = sentinel.filterDate('2024-06-01', '2024-09-30').median().clip(aoi).select('NDVI') # Faz o mesmo que em cima mas nas datas especificas



# ==========================================
# ETAPA 4: Detecção de Desmatamento
# ==========================================
delta_ndvi = ndvi_2024.subtract(ndvi_2022)        # Subtrai cada mapa e guarda os valores negativos (perda de vegetação)
queda_severa = delta_ndvi.lte(-0.35)              # Cria imagem binária destacando os pixels onde o NDVI caiu 0.35 ou mais
era_floresta_2022 = ndvi_2022.gte(0.4)            #Cria imagem binária onde pixels tinham NDVI maior ou igual a 0.4 (vegetação)
desmatamento_mascara = queda_severa.And(era_floresta_2022) # Combina as duas imagens



# ==========================================
# ETAPA 5: Visualização no Mapa
# ==========================================
Map = geemap.Map(basemap='SATELLITE')
Map.centerObject(ponto, 12)
Map.addLayer(ndvi_2022, {'min': 0, 'max': 0.8, 'palette': ['red', 'yellow', 'green']}, 'NDVI 2022')
Map.addLayer(ndvi_2024, {'min': 0, 'max': 0.8, 'palette': ['red', 'yellow', 'green']}, 'NDVI 2024')
Map.addLayer(desmatamento_mascara.selfMask(), {'palette': ['red']}, 'Área Desmatada')

# Para abrir o mapa no navegador
Map.to_html("mapa_desmatamento.html")
print("Processamento concluído! Abra o arquivo mapa_desmatamento.html no seu navegador.")