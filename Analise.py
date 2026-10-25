import os
from PIL import Image, ImageTk
import cv2
import customtkinter as ctk
import numpy as np
from tkinter import filedialog

# Funções de Cálculo de Escala e PDI

def calcular_resolucao_por_altitude(altitude_m, largura_px):
    # Calcula a resolução aproximada em m/px com base na Altitude do Ponto de Visão do Google Earth.
    # Largura da cena no solo (m) ≈ 0.535 * Altitude (m). (angulo da câmera do Google Earth)
    if altitude_m <= 0 or largura_px <= 0:
        return 1.0
    largura_terreno_m = 0.535 * altitude_m
    return largura_terreno_m / largura_px

def processar_diferenca(img_antes_path, img_depois_path, min_area=2000, pixel_resolution_m=2.5):

    img_antes = cv2.imread(img_antes_path)
    img_depois = cv2.imread(img_depois_path)

    if img_antes is None or img_depois is None:
        raise ValueError("Não foi possível carregar uma das imagens.")

    if img_antes.shape != img_depois.shape:
        img_depois = cv2.resize(img_depois, (img_antes.shape[1], img_antes.shape[0]))

    # Cálculo do Índice Excess Green (ExG) em BGR
    def calcular_exg(img):
        img_f = img.astype(np.float32)
        b = img_f[:, :, 0]
        g = img_f[:, :, 1]
        r = img_f[:, :, 2]

        exg = 2.0 * g - r - b
        return np.clip(exg, 0, 255).astype(np.uint8)

    exg_antes = calcular_exg(img_antes)
    exg_depois = calcular_exg(img_depois)

    # Queda de vegetação
    perda_verde = cv2.subtract(exg_antes, exg_depois)

    # Máscara de Exclusão Urbana (Saturação HSV >= 55)
    hsv_antes = cv2.cvtColor(img_antes, cv2.COLOR_BGR2HSV)
    saturacao = hsv_antes[:, :, 1]
    _, mascara_rural = cv2.threshold(saturacao, 55, 255, cv2.THRESH_BINARY)

    perda_verde_rural = cv2.bitwise_and(perda_verde, perda_verde, mask=mascara_rural)

    # Suavização e Limiarização por Otsu
    blur = cv2.GaussianBlur(perda_verde_rural, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Operações Morfológicas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mascara_limpa = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    mascara_limpa = cv2.morphologyEx(mascara_limpa, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Remoção de Ruído nas Bordas (Padding de 20px)
    margin = 20
    mascara_limpa[:margin, :] = 0
    mascara_limpa[-margin:, :] = 0
    mascara_limpa[:, :margin] = 0
    mascara_limpa[:, -margin:] = 0

    # Detecção e Contagem de Contornos
    contours, _ = cv2.findContours(mascara_limpa, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_resultado = img_depois.copy()
    overlay = img_resultado.copy()
    focos_detectados = 0
    area_total_pixels = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            focos_detectados += 1

            # Contagem de pixels ativos na região do contorno utilizando NumPy
            mascara_foco = np.zeros_like(mascara_limpa)
            cv2.drawContours(mascara_foco, [cnt], -1, 255, thickness=cv2.FILLED)
            area_total_pixels += cv2.countNonZero(mascara_foco)

            # Desenha preenchimento em BGR: (0, 0, 255)
            cv2.drawContours(overlay, [cnt], -1, (0, 0, 255), thickness=cv2.FILLED)

    # Aplica sobreposição semi-transparente (40% vermelho)
    alpha = 0.4
    cv2.addWeighted(overlay, alpha, img_resultado, 1 - alpha, 0, img_resultado)

    # Cálculos Finais de Área e Porcentagem
    total_pixels_imagem = img_depois.shape[0] * img_depois.shape[1]
    pct_impactada = (area_total_pixels / total_pixels_imagem) * 100

    area_m2 = area_total_pixels * (pixel_resolution_m**2)
    area_hectares = area_m2 / 10000.0

    return (img_resultado, mascara_limpa, focos_detectados, area_total_pixels, area_hectares, pct_impactada)


# Interface Gráfica
class InterfaceDesmatamento(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Estudo de Processamento de Imagens com OpenCV")
        self.geometry("1920x1080")

        self.path_antes = ""
        self.path_depois = ""

        # Layout Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Painel Superior de Controles
        self.frame_topo = ctk.CTkFrame(self)
        self.frame_topo.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.frame_topo.grid_columnconfigure((0, 6), weight=1)

        self.btn_carregar_antes = ctk.CTkButton(
            self.frame_topo,
            text="1. Selecionar Foto 'Antes'",
            command=self.selecionar_antes,
        )
        self.btn_carregar_antes.grid(row=0, column=1, padx=8, pady=10)

        self.btn_carregar_depois = ctk.CTkButton(
            self.frame_topo,
            text="2. Selecionar Foto 'Depois'",
            command=self.selecionar_depois,
        )
        self.btn_carregar_depois.grid(row=0, column=2, padx=8, pady=10)

        # Entrada para Altitude do Ponto de Visão (Google Earth)
        self.lbl_alt = ctk.CTkLabel(self.frame_topo, text="Alt. Visão (m):")
        self.lbl_alt.grid(row=0, column=3, padx=(12, 2), pady=10)

        self.ent_alt = ctk.CTkEntry(self.frame_topo, width=80)
        self.ent_alt.insert(0, "3000")
        self.ent_alt.grid(row=0, column=4, padx=(0, 12), pady=10)

        self.btn_processar = ctk.CTkButton(
            self.frame_topo,
            text="3. Executar OpenCV",
            fg_color="#2ba84a",
            command=self.executar,
        )
        self.btn_processar.grid(row=0, column=5, padx=8, pady=10)

        # Painel do Grid de Imagens
        self.frame_exibicao = ctk.CTkFrame(self)
        self.frame_exibicao.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.frame_exibicao.grid_columnconfigure((0, 1), weight=1)
        self.frame_exibicao.grid_rowconfigure((0, 1), weight=1)

        BORDER_ARGS = {
            "border_width": 2,
            "border_color": "#4a4a4a",
            "corner_radius": 6,
        }

        # Linha 1: Imagens Originais
        self.f_antes = ctk.CTkFrame(self.frame_exibicao, **BORDER_ARGS)
        self.f_antes.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self.f_antes.grid_rowconfigure(0, weight=1)
        self.f_antes.grid_columnconfigure(0, weight=1)

        self.lbl_img_antes = ctk.CTkLabel(self.f_antes, text="Imagem 'Antes' (Original)")
        self.lbl_img_antes.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.f_depois = ctk.CTkFrame(self.frame_exibicao, **BORDER_ARGS)
        self.f_depois.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        self.f_depois.grid_rowconfigure(0, weight=1)
        self.f_depois.grid_columnconfigure(0, weight=1)

        self.lbl_img_depois = ctk.CTkLabel(self.f_depois, text="Imagem 'Depois' (Original)")
        self.lbl_img_depois.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Linha 2: Processamento e Resultados
        self.f_mascara = ctk.CTkFrame(self.frame_exibicao, **BORDER_ARGS)
        self.f_mascara.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
        self.f_mascara.grid_rowconfigure(0, weight=1)
        self.f_mascara.grid_columnconfigure(0, weight=1)

        self.lbl_img_mascara = ctk.CTkLabel(self.f_mascara, text="Máscara de Alterações")
        self.lbl_img_mascara.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.f_resultado = ctk.CTkFrame(self.frame_exibicao, **BORDER_ARGS)
        self.f_resultado.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")
        self.f_resultado.grid_rowconfigure(0, weight=1)
        self.f_resultado.grid_columnconfigure(0, weight=1)

        self.lbl_img_resultado = ctk.CTkLabel(self.f_resultado, text="Destaque de Pixels Alterados")
        self.lbl_img_resultado.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Barra de Status
        self.lbl_status = ctk.CTkLabel(
            self,
            text="Selecione as duas imagens para iniciar.",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_status.grid(row=2, column=0, pady=10)

    # Métodos da Interface
    def carregar_e_exibir_preview(self, filepath, label_widget):
        img_cv = cv2.imread(filepath)
        if img_cv is not None:
            self.exibir_imagem_label(img_cv, label_widget)

    def selecionar_antes(self):
        filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.tif")])
        if filename:
            self.path_antes = filename
            self.carregar_e_exibir_preview(filename, self.lbl_img_antes)
            self.lbl_status.configure(text=f"Imagem 'Antes' carregada: {os.path.basename(filename)}")

    def selecionar_depois(self):
        filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png *.jpg *.jpeg *.tif")])
        if filename:
            self.path_depois = filename
            self.carregar_e_exibir_preview(filename, self.lbl_img_depois)
            self.lbl_status.configure(text=f"Imagem 'Depois' carregada: {os.path.basename(filename)}")

    def exibir_imagem_label(self, img_cv, label_widget):
        if len(img_cv.shape) == 2:
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

        img_pil = Image.fromarray(img_rgb)
        img_pil.thumbnail((480, 360))
        img_ctk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=img_pil.size)

        label_widget.configure(image=img_ctk, text="")
        label_widget.image = img_ctk

    def executar(self):
        if not self.path_antes or not self.path_depois:
            self.lbl_status.configure(
                text="Erro: Carregue ambas as imagens primeiro!",
                text_color="red",
            )
            return

        try:
            # Obtém a largura da imagem para calcular a escala
            img_temp = cv2.imread(self.path_antes)
            largura_px = img_temp.shape[1]

            altitude_m = float(self.ent_alt.get())
            res_m = calcular_resolucao_por_altitude(altitude_m, largura_px)

            res_img, mascara, focos, area_px, area_ha, pct = (
                processar_diferenca(
                    self.path_antes,
                    self.path_depois,
                    min_area=2000,
                    pixel_resolution_m=res_m,
                )
            )

            self.exibir_imagem_label(mascara, self.lbl_img_mascara)
            self.exibir_imagem_label(res_img, self.lbl_img_resultado)

            self.lbl_status.configure(
                text=f"Sucesso! Focos: {focos} | Escala: {res_m:.2f} m/px | Área: {area_px} px (~{area_ha:.2f} ha) | Alteração: {pct:.2f}% da cena",
                text_color="#2ba84a",
            )
        except Exception as e:
            self.lbl_status.configure(text=f"Erro no processamento: {e}", text_color="red")


if __name__ == "__main__":
    app = InterfaceDesmatamento()
    app.mainloop()