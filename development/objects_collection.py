import music_kraken
from music_kraken.objects import Song, Album, Artist, Collection

if __name__ == "__main__":
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

    print(artist.main_album_collection[0].barcode)
    print(artist.main_album_collection[0].albumsort)

    print(artist.main_album_collection._indexed_values)