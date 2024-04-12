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

    a = artist.main_album_collection[0]
    b = a.song_collection[0].album_collection[0]
    c = a.song_collection[1].album_collection[0]

    print(a.id, a.barcode, a.albumsort)
    print(b.id, b.barcode, b.albumsort)
    print(c.id, c.barcode, c.albumsort)
    print()
    print(artist.main_album_collection._indexed_values)