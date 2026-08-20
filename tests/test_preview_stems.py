import unittest

from load_agsearch import load_agsearch


class PreviewStemTests(unittest.TestCase):
    def test_how_migration_preview_keys_are_stems_not_stopwords(self):
        ag = load_agsearch()
        qterms = ag.parse_query("how migration")
        keys = ag.query_keys(qterms)
        self.assertEqual(keys, ["migrat"])
        self.assertTrue(all(k in "please migrate the database".lower() for k in keys))

    def test_n_mode_keeps_raw_substring_and(self):
        ag = load_agsearch()
        line = ag.SEP.join([
            "sid1", "/repo", "main", "2026-08-19T00:00:00", "user", "0",
            "Migration", "please migrate the database",
        ])
        hits = ag.rank_matches([line], "how migration")
        self.assertEqual(hits, [])
        hits = ag.rank_matches([line], "migrate")
        self.assertEqual(len(hits), 1)

    def test_preview_stem_keys_match_migrate_body(self):
        ag = load_agsearch()
        keys = ag.query_keys(ag.parse_query("how migration"))
        body = "we need to migrate the billing database"
        matches = all(k in body.lower() for k in keys)
        self.assertTrue(matches, keys)
        raw_terms = [t.lower() for t in "how migration".split()]
        self.assertFalse(all(t in body.lower() for t in raw_terms))


if __name__ == "__main__":
    unittest.main()
