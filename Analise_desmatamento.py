import customtkinter as ctk
from tkintermapview import TkinterMapView
from geopy.geocoders import Nominatim
import ee
import folium
import webbrowser
import math
import os

# =============== 1: Inicialização do Earth Engine ========================
PROJECT_ID = os.getenv("GEE_PROJECT_ID", None)

try:
    if PROJECT_ID:
        ee.Initialize(project=PROJECT_ID)
    else:
        ee.Initialize()  # Usa as credenciais locais padrão do usuário
except Exception:
    ee.Authenticate()
    if PROJECT_ID:
        ee.Initialize(project=PROJECT_ID)
    else:
        ee.Initialize()

# =============== 2: Criação de interface gráfica =========================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppDesmatamento(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitorização de Desmatamento por Satélite")
        self.geometry("1080x720")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Painel lateral
        self.frame_menu = ctk.CTkFrame(self, width=400, corner_radius=0)
        self.frame_menu.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.label_titulo = ctk.CTkLabel(
            self.frame_menu,
            text="Parâmetros de Análise", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.label_titulo.pack(padx=10, pady=(15, 15))

        # Entradas
        self.label_local = ctk.CTkLabel(self.frame_menu, text="Cidade ou Local (Coordenadas):")
        self.label_local.pack(anchor="w", padx=15, pady=(5, 0))
        self.entry_local = ctk.CTkEntry(self.frame_menu, placeholder_text="Ex: Ribeirão Preto, SP")
        self.entry_local.pack(fill="x", padx=15, pady=(0, 10))

        self.label_raio = ctk.CTkLabel(self.frame_menu, text="Raio de Busca (km):")
        self.label_raio.pack(anchor="w", padx=15, pady=(5, 0))
        self.entry_raio = ctk.CTkEntry(self.frame_menu, placeholder_text="Ex: 10")
        self.entry_raio.pack(fill="x", padx=15, pady=(0, 10))

        # Datas
        self.label_ano_inicio = ctk.CTkLabel(self.frame_menu, text="Ano Inicial:")
        self.label_ano_inicio.pack(anchor="w", padx=15, pady=(5, 0))
        self.combo_ano_inicio = ctk.CTkOptionMenu(self.frame_menu, values=["2019", "2020", "2021", "2022", "2023"])
        self.combo_ano_inicio.pack(fill="x", padx=15, pady=(0, 10))

        self.label_ano_fim = ctk.CTkLabel(self.frame_menu, text="Ano Final:")
        self.label_ano_fim.pack(anchor="w", padx=15, pady=(5, 0))
        self.combo_ano_fim = ctk.CTkOptionMenu(self.frame_menu, values=["2022", "2023", "2024", "2025", "2026"])
        self.combo_ano_fim.pack(fill="x", padx=15, pady=(0, 10))

        # Botão Processar
        self.btn_analisar = ctk.CTkButton(
            self.frame_menu, 
            text="🔍 Analisar Desmatamento", 
            command=self.processar_analise, 
            fg_color="#2ba84a", 
            hover_color="#1e7a35"
        )
        self.btn_analisar.pack(fill="x", padx=15, pady=(15, 10))

        # Indicador de Área
        self.frame_resultado = ctk.CTkFrame(self.frame_menu, fg_color="#1f242d")
        self.frame_resultado.pack(fill="x", padx=15, pady=5)

        self.label_resultado_titulo = ctk.CTkLabel(self.frame_resultado, text="Área Desmatada:", font=ctk.CTkFont(size=12))
        self.label_resultado_titulo.pack(pady=(8, 2))

        self.label_area = ctk.CTkLabel(self.frame_resultado, text="0.00 ha", font=ctk.CTkFont(size=20, weight="bold"), text_color="#e63946")
        self.label_area.pack(pady=(0, 8))

        # Botão para abrir sobreposição completa
        self.btn_abrir_mapa = ctk.CTkButton(
            self.frame_menu,
            text="🗺️ Ver mapa de desmatamento no Navegador",
            command=self.abrir_mapa_html,
            fg_color="#1d3557",
            hover_color="#457b9d",
            state="disabled"
        )
        self.btn_abrir_mapa.pack(fill="x", padx=15, pady=(10, 10))

        self.label_status = ctk.CTkLabel(self.frame_menu, text="Status: Aguardando dados", font=ctk.CTkFont(size=11))
        self.label_status.pack(padx=10, pady=5)

        # Painel do mapa
        self.frame_mapa = ctk.CTkFrame(self)
        self.frame_mapa.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        self.mapa_widget = TkinterMapView(self.frame_mapa, corner_radius=0)
        self.mapa_widget.pack(fill="both", expand=True)

        self.mapa_widget.set_position(-21.1680, -47.7780)
        self.mapa_widget.set_zoom(12)
        self.mapa_widget.set_tile_server("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", max_zoom=22)

        self.mapa_html_path = "mapa_desmatamento.html"

    # Convertendo a cidade para coordenadas
    def obter_coordenadas(self, nome_local):
        try:
            geolocator = Nominatim(user_agent="app_desmatamento")
            localizacao = geolocator.geocode(nome_local)
            if localizacao:
                return localizacao.latitude, localizacao.longitude
        except Exception:
            return None
        return None

    # Recolhendo dados informados e validando informações
    def processar_analise(self):
        local_texto = self.entry_local.get()
        raio_km = float(self.entry_raio.get()) if self.entry_raio.get() else 10.0
        ano_inicio = self.combo_ano_inicio.get()
        ano_fim = self.combo_ano_fim.get()

        self.label_status.configure(text="A buscar coordenadas...", text_color="yellow")
        self.update()

        coords = self.obter_coordenadas(local_texto)
        if not coords:
            self.label_status.configure(text="Erro: Local não encontrado!", text_color="red")
            return

        lat, lon = coords
        self.label_status.configure(text="Buscando no Earth Engine...", text_color="yellow")
        self.update()

        # Buscando local no Earth Engine
        ponto = ee.Geometry.Point([lon, lat])
        aoi = ponto.buffer(raio_km * 1000)

        # Função p/ calcular diferença de bandas B8 e B4 (NDVI - Normalized Difference Vegetation Index)
        def adicionar_ndvi(imagem):
            return imagem.addBands(imagem.normalizedDifference(['B8', 'B4']).rename('NDVI'))

        sentinel = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') # reflectância de superfície harmonizada
                    .filterBounds(aoi)
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)) # Removendo imagens com +10% de nuvens em cena
                    .map(adicionar_ndvi))

        ndvi_antes = sentinel.filterDate(f'{ano_inicio}-06-01', f'{ano_inicio}-09-30').median().clip(aoi).select('NDVI') # Sempre pegando entre Julho e Setembro por ser período de seca (Inverno)
        ndvi_depois = sentinel.filterDate(f'{ano_fim}-06-01', f'{ano_fim}-09-30').median().clip(aoi).select('NDVI') # Sempre pegando entre Julho e Setembro por ser período de seca (Inverno)

        delta_ndvi = ndvi_depois.subtract(ndvi_antes) # Calcula variação NDVI pixel a pixel
        queda_severa = delta_ndvi.lte(-0.35) # Identifica onde houve queda de NDVI <= -0.35
        era_floresta = ndvi_antes.gte(0.4) # Vê se local era área vegetada no inicio (>= 0.4)
        desmatamento_mascara = queda_severa.And(era_floresta) # Combina as duas condições

        # Calculando a area em Hectares
        area_imagem = desmatamento_mascara.multiply(ee.Image.pixelArea())
        soma_area = area_imagem.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=10,
            maxPixels=1e9
        )
        
        try:
            area_m2 = soma_area.get('NDVI').getInfo()
            area_ha = (area_m2 / 10000.0) if area_m2 is not None else 0.0
            self.label_area.configure(text=f"{area_ha:.2f} ha")
        except Exception:
            area_ha = 0.0
            self.label_area.configure(text="N/A")

        # Gerar ficheiro Folium com sobreposição transparente
        map_id_2022 = ndvi_antes.getMapId({'min': 0, 'max': 0.8, 'palette': ['red', 'yellow', 'green']})
        map_id_2024 = ndvi_depois.getMapId({'min': 0, 'max': 0.8, 'palette': ['red', 'yellow', 'green']})
        map_id_desm = desmatamento_mascara.selfMask().getMapId({'palette': ['red']})

        m = folium.Map(location=[lat, lon], zoom_start=12, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Imagem de Satélite', overlay=False
        ).add_to(m)

        folium.TileLayer(tiles=map_id_2022['tile_fetcher'].url_format, attr='GEE', name=f'NDVI {ano_inicio}', overlay=True).add_to(m)
        folium.TileLayer(tiles=map_id_2024['tile_fetcher'].url_format, attr='GEE', name=f'NDVI {ano_fim}', overlay=True).add_to(m)
        folium.TileLayer(tiles=map_id_desm['tile_fetcher'].url_format, attr='GEE', name='Área Desmatada', overlay=True).add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        m.save(self.mapa_html_path)

        # 4. Atualizar janela
        self.mapa_widget.set_position(lat, lon)
        self.mapa_widget.set_zoom(12)
        self.mapa_widget.delete_all_marker()
        self.mapa_widget.delete_all_path()
        self.mapa_widget.delete_all_polygon()

        # Desenhar perímetro do raio
        def criar_circulo(l_lat, l_lon, r_km, pontos=64):
            coords_list = []
            r_terra = 6371.0
            for i in range(pontos):
                ang = math.radians((i / pontos) * 360)
                l_rad, lo_rad = math.radians(l_lat), math.radians(l_lon)
                d_lat = (r_km / r_terra) * math.cos(ang)
                d_lon = (r_km / (r_terra * math.cos(l_rad))) * math.sin(ang)
                coords_list.append((math.degrees(l_rad + d_lat), math.degrees(lo_rad + d_lon)))
            return coords_list

        self.mapa_widget.set_polygon(criar_circulo(lat, lon, raio_km), outline_color="#e63946", fill_color=None, border_width=2)
        self.mapa_widget.set_marker(lat, lon, text=f"{local_texto}\nRaio: {raio_km}km | Desmatado: {area_ha:.2f} ha")

        self.btn_abrir_mapa.configure(state="normal")
        self.label_status.configure(text="Concluído com sucesso!", text_color="#2ba84a")

    #Abre o mapa no navegador
    def abrir_mapa_html(self):
        webbrowser.open(self.mapa_html_path)


if __name__ == "__main__":
    app = AppDesmatamento()
    app.mainloop()