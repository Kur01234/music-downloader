import unittest

from music_kraken.objects import Song, Album, Artist, Collection, Country

class TestCollection(unittest.TestCase):
    def test_song_contains_album(self):
        """
        Tests that every song contains the album it is added to in its album_collection
        """

        a_1 = Album(
            title="album",
            song_list= [
                Song(title="song"),
            ]
        )
        a_2 = a_1.song_collection[0].album_collection[0]
        self.assertTrue(a_1.id == a_2.id)

    def test_album_contains_song(self):
        """
        Tests that every album contains the song it is added to in its song_collection
        """
        s_1 = Song(
            title="song",
            album_list=[
                Album(title="album"),
            ]
        )
        s_2 = s_1.album_collection[0].song_collection[0]
        self.assertTrue(s_1.id == s_2.id)


    def test_auto_add_artist_to_album_feature_artist(self):
        """
        Tests that every artist is added to the album's feature_artist_collection per default
        """

        a_1 = Artist(
            name="artist",
            album_list=[
                Album(title="album")
            ]
        )
        a_2 = a_1.album_collection[0].feature_artist_collection[0]

        self.assertTrue(a_1.id == a_2.id)
    
    def test_auto_add_artist_to_album_feature_artist_push(self):
        """
        Tests that every artist is added to the album's feature_artist_collection per default but pulled into the album's artist_collection if a merge exitst
        """

        a_1 = Artist(
            name="artist",
            album_list=[
                Album(
                    title="album",
                    artist_list=[
                        Artist(name="artist"),
                    ]
                )
            ]
        )
        a_2 = a_1.album_collection[0].artist_collection[0]

        self.assertTrue(a_1.id == a_2.id)


    def test_artist_artist_relation(self):
        """
        Tests the proper syncing between album.artist_collection and song.artist_collection
        """

        album = Album(
            title="album",
            song_list=[
                Song(title="song"),
            ],
            artist_list=[
                Artist(name="artist"),
            ]
        )
        a_1 = album.artist_collection[0]
        a_2 = album.song_collection[0].artist_collection[0]

        self.assertTrue(a_1.id == a_2.id)

    def test_artist_collection_sync(self):
        """
        tests the actual implementation of the test above
        """

        album_1 = Album(
            title="album",
            song_list=[
                Song(title="song", artist_list=[Artist(name="artist")]),
            ],
            artist_list=[
                Artist(name="artist"),
            ]
        )

        album_2 = Album(
            title="album",
            song_list=[
                Song(title="song", artist_list=[Artist(name="artist")]),
            ],
            artist_list=[
                Artist(name="artist"),
            ]
        )

        album_1.merge(album_2)

        self.assertTrue(id(album_1.artist_collection) == id(album_1.artist_collection) == id(album_1.song_collection[0].artist_collection) == id(album_1.song_collection[0].artist_collection))

if __name__ == "__main__":
    unittest.main()
