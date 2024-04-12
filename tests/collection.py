import unittest

import music_kraken
from music_kraken.objects import Song, Album, Artist, Collection

class TestCollection(unittest.TestCase):
    def test_song_album_relation(self):
        """
        Tests that
        album = album.any_song.one_album
        is the same object
        """

        artist: Artist = Artist(
            name="artist",
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

        a = artist.main_album_collection[0]
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

if __name__ == "__main__":
    unittest.main()
