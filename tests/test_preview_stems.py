import unittest

from load_agsearch import load_agsearch


class PreviewStemTests(unittest.TestCase):
    def test_how_migration_preview_keys_are_stems_not_stopwords(self):
        ag = load_agsearch()
        qterms = ag.parse_query("how migration")
        keys = ag.query_keys(qterms)
        self.assertEqual(keys, ["migrat"])
        self.assertTrue(all(k in "please migrate the database".lower() for k in keys))

    def test_n_mode_stems_too_because_it_shares_the_ranker(self):
        """`-n` used to be an AND of raw substrings, so "how migration" found nothing in a
        session that says "migrate". It runs rank_sessions now, the same as the list."""
        ag = load_agsearch()
        row = ["sid1", "/repo", "2026-08-19", "cc", "cli", "Migration",
               "please migrate the database", "please migrate the database"]
        self.assertEqual(len(ag.rank_sessions([row], ag.parse_query("how migration"))), 1)
        self.assertEqual(len(ag.rank_sessions([row], ag.parse_query("migrate"))), 1)

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
