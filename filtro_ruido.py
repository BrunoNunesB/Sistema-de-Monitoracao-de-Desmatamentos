"""Filtros de qualidade e ruído para máscaras de desmatamento no Earth Engine.

Todo o processamento ocorre no servidor Earth Engine. O limite de pixels
conectados é aplicado numa grade Sentinel-2 B4 de 10 m.
"""

import ee

PIXELS_MINIMOS = 5
OBSERVACOES_MINIMAS = 3

# SCL: saturado, sombra de nuvem, classe incerta, nuvens, cirrus e neve.
# O código 0 (sem dados) já vem mascarado na coleção Sentinel-2 SR.
SCL_DESCARTADAS = (1, 3, 7, 8, 9, 10, 11)


def mascarar_nuvens_scl(imagem):
    """Mantém somente observações SCL adequadas para o cálculo de NDVI."""
    scl = imagem.select('SCL')
    validos = scl.neq(SCL_DESCARTADAS[0])
    for classe in SCL_DESCARTADAS[1:]:
        validos = validos.And(scl.neq(classe))
    return imagem.updateMask(validos)


def pixels_com_observacoes_suficientes(colecao_antes, colecao_depois,
                                      minimo=OBSERVACOES_MINIMAS):
    """Máscara de pixels com >= minimo observações NDVI em ambos os períodos."""
    if minimo < 1:
        raise ValueError('O mínimo de observações deve ser positivo.')
    quantidade_antes = colecao_antes.select('NDVI').count()
    quantidade_depois = colecao_depois.select('NDVI').count()
    return quantidade_antes.gte(minimo).And(quantidade_depois.gte(minimo))


def remover_ruido_conectado(mascara_original, projecao,
                             minimo_pixels=PIXELS_MINIMOS):
    """Mantém agrupamentos com pelo menos 5 pixels 8-conectados.

    A reprojeção ocorre somente na imagem usada para contar os vizinhos.
    Isso estabiliza o filtro na grade Sentinel-2 de 10 m em vez de deixar a
    contagem variar de acordo com o nível de zoom do mapa.
    """
    if minimo_pixels < 1:
        raise ValueError('O mínimo de pixels deve ser positivo.')

    somente_positivos = mascara_original.selfMask().reproject(crs=projecao)
    tamanho_grupo = somente_positivos.connectedPixelCount(
        maxSize=max(100, minimo_pixels),
        eightConnected=True,
    )
    return mascara_original.updateMask(
        tamanho_grupo.gte(minimo_pixels)
    ).rename('desmatamento')


def calcular_areas(mascara_original, mascara_filtrada, pixels_validos, aoi):
    """Retorna áreas (ha) de detecção original, filtrada e retirada.

    A área observável evita comunicar 0 ha se não existirem pixels com as
    três observações válidas em ambos os períodos.
    """
    area_pixel = ee.Image.pixelArea()
    camadas = ee.Image.cat(
        mascara_original.selfMask().multiply(area_pixel).rename('bruta_m2'),
        mascara_filtrada.selfMask().multiply(area_pixel).rename('filtrada_m2'),
        area_pixel.updateMask(pixels_validos).rename('observada_m2'),
    )
    resultado = camadas.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,
        maxPixels=1e9,
        tileScale=4,
    ).getInfo() or {}

    if not resultado.get('observada_m2'):
        raise ValueError(
            'Sem cobertura válida suficiente para analisar esta região. '
            'Tente outros anos ou um intervalo de datas maior.'
        )

    bruta = (resultado.get('bruta_m2') or 0.0) / 10000.0
    filtrada = (resultado.get('filtrada_m2') or 0.0) / 10000.0
    return {
        'bruta_ha': bruta,
        'filtrada_ha': filtrada,
        'removida_ha': max(0.0, bruta - filtrada),
        'observada_ha': resultado['observada_m2'] / 10000.0,
    }
