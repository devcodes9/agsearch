"""A top result whose preview card is blank reads as a broken search.

The card AND-matches query words against message text. When the ranker put a session first
because of its title or first prompt, no single message has every word and the card used to
render `0 match(es)` and nothing else. On the local corpus every observed case of that had
some query word in the body, so showing the closest messages recovers all of them.
"""

import unittest

from load_agsearch import load_agsearch


class BestMatchingTests(unittest.TestCase):
    def test_exact_and_when_a_message_has_every_word(self):
        ag = load_agsearch()
        texts = [
            "unrelated chatter",
            "the chat ownership rules are here",
            "chat only",
        ]
        picked, best = ag.best_matching(texts, ["chat", "ownership"])
        self.assertEqual((picked, best), ([1], 2))

    def test_falls_back_to_the_closest_messages(self):
        ag = load_agsearch()
        texts = [
            "nothing relevant at all",
            "we discussed chat retention",
            "chat again here",
        ]
        picked, best = ag.best_matching(texts, ["chat", "ownership"])
        self.assertEqual((picked, best), ([1, 2], 1))

    def test_reports_nothing_when_no_word_appears(self):
        ag = load_agsearch()
        picked, best = ag.best_matching(["totally unrelated"], ["chat", "ownership"])
        self.assertEqual((picked, best), ([], 0))

    def test_partial_hits_do_not_beat_a_full_hit(self):
        ag = load_agsearch()
        texts = ["chat " * 50, "chat ownership once"]
        picked, best = ag.best_matching(texts, ["chat", "ownership"])
        self.assertEqual((picked, best), ([1], 2))

    def test_uses_word_starts_so_substrings_do_not_count(self):
        ag = load_agsearch()
        picked, best = ag.best_matching(["approach improve compress"], ["pr"])
        self.assertEqual((picked, best), ([], 0))

    def test_empty_transcript_is_not_an_error(self):
        ag = load_agsearch()
        self.assertEqual(ag.best_matching([], ["chat"]), ([], 0))


if __name__ == "__main__":
    unittest.main()
