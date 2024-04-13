import unittest

from music_kraken.objects import Song, Album, Artist, Collection, Country

class TestCollection(unittest.TestCase):
    @staticmethod
    def complicated_object() -> Artist:
        return Artist(
            name="artist",
            country=Country.by_alpha_2("DE"),
            main_album_list=[
                Album(
                    title="album",
                    song_list=[
                        Song(
                            title="song",
                            album_list=[
                                Album(title="album", albumsort=123),
                            ],
                        ),
                        Song(
                            title="other_song",
                            album_list=[
                                Album(title="album", albumsort=423),
                            ],
                        ),
                    ]
                ),
                Album(title="album", barcode="1234567890123"),
            ]
        )

    def test_song_album_relation(self):
        """
        Tests that
        album = album.any_song.one_album
        is the same object
        """

        a = self.complicated_object().main_album_collection[0]
        b = a.song_collection[0].album_collection[0]
        c = a.song_collection[1].album_collection[0]
        d = b.song_collection[0].album_collection[0]
        e = d.song_collection[0].album_collection[0]
        f = e.song_collection[0].album_collection[0]
        g = f.song_collection[0].album_collection[0]

        self.assertTrue(a.id == b.id == c.id == d.id == e.id == f.id == g.id)
        self.assertTrue(a.title == b.title == c.title == d.title == e.title == f.title == g.title == "album")
        self.assertTrue(a.barcode == b.barcode == c.barcode == d.barcode == e.barcode == f.barcode == g.barcode == "1234567890123")
        self.assertTrue(a.albumsort == b.albumsort == c.albumsort == d.albumsort == e.albumsort == f.albumsort == g.albumsort == 123)

        d.title = "new_title"

        self.assertTrue(a.title == b.title == c.title == d.title == e.title == f.title == g.title == "new_title")

    def test_album_artist_relation(self):
        """
        Tests that
        artist = artist.any_album.any_song.one_artist
        is the same object
        """

        a = self.complicated_object()
        b = a.main_album_collection[0].artist_collection[0]
        c = b.main_album_collection[0].artist_collection[0]
        d = c.main_album_collection[0].artist_collection[0]

        self.assertTrue(a.id == b.id == c.id == d.id)
        self.assertTrue(a.name == b.name == c.name == d.name == "artist")
        self.assertTrue(a.country == b.country == c.country == d.country)

    def test_song_artist_relations(self):
        """
        Tests that
        artist = artist.any_album.any_song.one_artist
        is the same object
        """

        a = self.complicated_object()
        b = a.main_album_collection[0].song_collection[0].main_artist_collection[0]
        c = b.main_album_collection[0].song_collection[0].main_artist_collection[0]
        d = c.main_album_collection[0].song_collection[0].main_artist_collection[0]

        self.assertTrue(a.id == b.id == c.id == d.id)
        self.assertTrue(a.name == b.name == c.name == d.name == "artist")
        self.assertTrue(a.country == b.country == c.country == d.country)

if __name__ == "__main__":
    unittest.main()
