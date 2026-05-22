import unittest
import pandas as pd
import numpy as np
import importlib.util
import os

# Helper to import modules with leading digits
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

etl_transform = import_from_path("etl_02_transform", os.path.join(project_root, "etl", "02_clean_and_transform.py"))
clean_year = etl_transform.clean_year
parse_analysis_string = etl_transform.parse_analysis_string
normalize_columns = etl_transform.normalize_columns

class TestETLTransform(unittest.TestCase):
    def test_clean_year(self):
        self.assertEqual(clean_year("Mar-24"), "Mar 2024")
        self.assertEqual(clean_year("TTM"), "TTM")
        self.assertEqual(clean_year(np.nan), None)

    def test_parse_analysis_string(self):
        self.assertEqual(parse_analysis_string("10 Years: 11%"), (10, 0.11))
        self.assertEqual(parse_analysis_string("5 Years: -2.5%"), (5, -0.025))
        self.assertEqual(parse_analysis_string(None), (None, None))

    def test_normalize_columns(self):
        df = pd.DataFrame(columns=[' Sales ', 'Net Profit', 'SYMBOL'])
        df = normalize_columns(df)
        self.assertIn('revenue', df.columns)
        self.assertIn('net_profit', df.columns)
        self.assertIn('symbol', df.columns)

if __name__ == '__main__':
    unittest.main()
