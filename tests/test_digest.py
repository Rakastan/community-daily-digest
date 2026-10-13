import datetime as dt
import unittest

from digest import RedditReader, build_report, choose_communities


class FakeReader(RedditReader):
    def __init__(self, pages):
        super().__init__("synthetic-token", "test-client")
        self.pages = iter(pages)
        self.requests = []

    def get(self, path, **params):
        self.requests.append((path, params))
        return next(self.pages)


class DigestTests(unittest.TestCase):
    def test_joined_communities_follows_pagination(self):
        reader = FakeReader([
            {"children": [{"data": {"display_name": "ExampleOne"}}], "after": "t5_cursor"},
            {"children": [{"data": {"display_name": "ExampleTwo"}}], "after": None},
        ])
        self.assertEqual(reader.joined(), {"ExampleOne", "ExampleTwo"})
        self.assertEqual(reader.requests[1][1]["after"], "t5_cursor")

    def test_requested_community_must_be_joined(self):
        self.assertEqual(choose_communities({"ExampleOne"}, ["r/exampleone"]), ["ExampleOne"])
        with self.assertRaises(RuntimeError):
            choose_communities({"ExampleOne"}, ["OtherCommunity"])

    def test_report_excludes_old_posts_and_does_not_copy_body(self):
        now = dt.datetime(2026, 10, 13, tzinfo=dt.timezone.utc)
        reader = FakeReader([{"children": [
            {"data": {"title": "Recent [title]", "permalink": "/r/ExampleOne/comments/abc/title/",
                      "created_utc": now.timestamp() - 100, "selftext": "PRIVATE_BODY_MARKER"}},
            {"data": {"title": "Old title", "permalink": "/r/ExampleOne/comments/old/title/",
                      "created_utc": now.timestamp() - 90000}},
        ]}])
        report = build_report(reader, ["ExampleOne"], 25, 24, now)
        self.assertIn("Recent \\[title\\]", report)
        self.assertIn("https://www.reddit.com/r/ExampleOne/comments/abc/title/", report)
        self.assertNotIn("Old title", report)
        self.assertNotIn("PRIVATE_BODY_MARKER", report)


if __name__ == "__main__":
    unittest.main()
