"""Testes unitários offline da lógica de integração com Earth Engine.

Valida parâmetros e construção da expressão, sem avaliar imagens reais.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FakeImage:
    def __init__(self, log=None, result=None):
        self.log = log if log is not None else []
        self.result = result

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            self.log.append((name, args, kwargs))
            if name == 'getInfo':
                return self.result
            return FakeImage(self.log, result=self.result)
        return chain


class FakeImageConstructor:
    @staticmethod
    def pixelArea():
        return FakeImage()

    @staticmethod
    def cat(*images):
        return FakeImage(result={
            'bruta_m2': 1500, 'filtrada_m2': 1000, 'observada_m2': 200000,
        })


fake_ee = types.ModuleType('ee')
fake_ee.Image = FakeImageConstructor
fake_ee.Reducer = types.SimpleNamespace(sum=lambda: 'soma')
sys.modules['ee'] = fake_ee
spec = importlib.util.spec_from_file_location('filtro_ruido', ROOT / 'filtro_ruido.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FiltroRuidoTests(unittest.TestCase):
    def test_parametros_padrao(self):
        self.assertEqual(mod.PIXELS_MINIMOS, 5)
        self.assertEqual(mod.OBSERVACOES_MINIMAS, 3)
        self.assertIn(3, mod.SCL_DESCARTADAS)
        self.assertIn(10, mod.SCL_DESCARTADAS)

    def test_filtro_oito_conexoes_e_cinco_pixels(self):
        log = []
        mod.remover_ruido_conectado(FakeImage(log), 'sentinel_b4', 5)
        chamadas = [item for item in log if item[0] == 'connectedPixelCount']
        self.assertEqual(len(chamadas), 1)
        self.assertEqual(chamadas[0][2]['eightConnected'], True)
        self.assertEqual(chamadas[0][2]['maxSize'], 100)
        self.assertIn(('reproject', (), {'crs': 'sentinel_b4'}), log)
        self.assertTrue(any(name == 'gte' and args == (5,) for name, args, kw in log))

    def test_nao_aceita_limite_zero(self):
        with self.assertRaises(ValueError):
            mod.remover_ruido_conectado(FakeImage(), 'p', 0)
        with self.assertRaises(ValueError):
            mod.pixels_com_observacoes_suficientes(FakeImage(), FakeImage(), 0)

    def test_tres_observacoes_nos_dois_periodos(self):
        log = []
        mod.pixels_com_observacoes_suficientes(FakeImage(log), FakeImage(log), 3)
        self.assertEqual(sum(name == 'count' for name, args, kw in log), 2)
        self.assertEqual(sum(name == 'gte' and args == (3,) for name, args, kw in log), 2)
        self.assertEqual(sum(name == 'And' for name, args, kw in log), 1)

    def test_calculo_areas(self):
        areas = mod.calcular_areas(FakeImage(), FakeImage(), FakeImage(), 'aoi')
        self.assertAlmostEqual(areas['bruta_ha'], 0.15)
        self.assertAlmostEqual(areas['filtrada_ha'], 0.1)
        self.assertAlmostEqual(areas['removida_ha'], 0.05)
        self.assertAlmostEqual(areas['observada_ha'], 20)


if __name__ == '__main__':
    unittest.main()
