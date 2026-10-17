import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402


class URLShortenerTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def shorten(self, **payload):
        return self.client.post("/api/shorten", json=payload)

    def test_shorten_and_redirect(self):
        res = self.shorten(url="https://example.com/some/long/path?x=1")
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(len(data["short_code"]), 6)
        self.assertTrue(data["short_url"].endswith("/" + data["short_code"]))

        redirect = self.client.get("/" + data["short_code"])
        self.assertEqual(redirect.status_code, 302)
        self.assertEqual(redirect.headers["Location"], "https://example.com/some/long/path?x=1")

    def test_same_url_reuses_code(self):
        first = self.shorten(url="https://example.com/a").get_json()
        res = self.shorten(url="https://example.com/a")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["short_code"], first["short_code"])

    def test_different_urls_get_different_codes(self):
        a = self.shorten(url="https://example.com/a").get_json()["short_code"]
        b = self.shorten(url="https://example.com/b").get_json()["short_code"]
        self.assertNotEqual(a, b)

    def test_invalid_urls_rejected(self):
        for bad in ["", "   ", "not a url", "ftp://example.com", "javascript:alert(1)", "https://", None, 123]:
            res = self.shorten(url=bad)
            self.assertEqual(res.status_code, 400, msg=f"{bad!r} should be rejected")

    def test_missing_body_rejected(self):
        res = self.client.post("/api/shorten", data="oops", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    def test_too_long_url_rejected(self):
        res = self.shorten(url="https://example.com/" + "a" * 2100)
        self.assertEqual(res.status_code, 400)

    def test_custom_code(self):
        res = self.shorten(url="https://example.com/x", custom_code="my-link_1")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["short_code"], "my-link_1")
        self.assertEqual(self.client.get("/my-link_1").status_code, 302)

    def test_custom_code_conflict_and_validation(self):
        self.shorten(url="https://example.com/x", custom_code="taken")
        self.assertEqual(self.shorten(url="https://example.com/y", custom_code="taken").status_code, 409)
        self.assertEqual(self.shorten(url="https://example.com/y", custom_code="a b").status_code, 400)
        self.assertEqual(self.shorten(url="https://example.com/y", custom_code="ab").status_code, 400)
        self.assertEqual(self.shorten(url="https://example.com/y", custom_code="api").status_code, 400)

    def test_unknown_code_404(self):
        res = self.client.get("/doesnotexist")
        self.assertEqual(res.status_code, 404)

    def test_click_counter_and_stats(self):
        code = self.shorten(url="https://example.com/c").get_json()["short_code"]
        for _ in range(3):
            self.client.get("/" + code)
        stats = self.client.get(f"/api/urls/{code}").get_json()
        self.assertEqual(stats["clicks"], 3)
        self.assertEqual(stats["original_url"], "https://example.com/c")
        self.assertEqual(self.client.get("/api/urls/nope").status_code, 404)

    def test_list_urls_newest_first(self):
        self.shorten(url="https://example.com/1")
        self.shorten(url="https://example.com/2")
        items = self.client.get("/api/urls").get_json()
        self.assertEqual([i["original_url"] for i in items],
                         ["https://example.com/2", "https://example.com/1"])

    def test_frontend_and_health(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"URL Shortener", home.data)
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})

    def test_data_persists_in_database(self):
        code = self.shorten(url="https://example.com/p").get_json()["short_code"]
        fresh = create_app(self.db_path).test_client()  # new app instance, same DB file
        self.assertEqual(fresh.get("/" + code).status_code, 302)


if __name__ == "__main__":
    unittest.main()
