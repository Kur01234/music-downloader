import unittest

from music_kraken.utils.string_processing import hash_url


class TestCollection(unittest.TestCase):
    def test_remove_schema(self):
        self.assertFalse(hash_url("https://www.youtube.com/watch?v=3jZ_D3ELwOQ").startswith("https"))
        self.assertFalse(hash_url("ftp://www.youtube.com/watch?v=3jZ_D3ELwOQ").startswith("https"))
        self.assertFalse(hash_url("sftp://www.youtube.com/watch?v=3jZ_D3ELwOQ").startswith("https"))
        self.assertFalse(hash_url("http://www.youtube.com/watch?v=3jZ_D3ELwOQ").startswith("https"))

    def test_no_punctuation(self):
        self.assertNotIn(hash_url("https://www.you_tube.com/watch?v=3jZ_D3ELwOQ"), "you_tube")
        self.assertNotIn(hash_url("https://docs.gitea.com/next/install.ation/comparison"), ".")

    def test_three_parts(self):
        """
        The url is parsed into three parts [netloc; path; query]
        Which are then appended to each other with an underscore between.
        """

        self.assertTrue(hash_url("https://duckduckgo.com/?t=h_&q=dfasf&ia=web").count("_") == 2)

    def test_sort_query(self):
        """
        The query is sorted alphabetically
        """
        hashed = hash_url("https://duckduckgo.com/?t=h_&q=dfasf&ia=web")
        sorted_keys = ["ia-", "q-", "t-"]

        self.assertTrue(hashed.index(sorted_keys[0]) < hashed.index(sorted_keys[1]) < hashed.index(sorted_keys[2]))

if __name__ == "__main__":
    unittest.main()
