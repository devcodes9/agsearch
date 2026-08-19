import importlib.machinery
import importlib.util
import pathlib
import unittest


def _load_agsearch():
    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "agsearch"
    loader = importlib.machinery.SourceFileLoader("agsearch_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class QueryMappingTests(unittest.TestCase):
    def test_preview_terms_use_normalized_concepts(self):
        ag = _load_agsearch()
        self.assertEqual(ag.preview_match_terms("how legislation"), ["legislat"])

    def test_concept_mappings_show_stem_and_fuzzy_target(self):
        ag = _load_agsearch()
        hay = "eu legislation rollout plan and alibrary production fix notes"
        mapping = ag.concept_mappings("EU legislation alibrry", hay)
        self.assertIn("legislation→legislat", mapping)
        self.assertIn("alibrry→alibrary", mapping)


if __name__ == "__main__":
    unittest.main()
