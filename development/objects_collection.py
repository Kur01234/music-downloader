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
    d = b.song_collection[0].album_collection[0]
    e = d.song_collection[0].album_collection[0]
    f = e.song_collection[0].album_collection[0]
    g = f.song_collection[0].album_collection[0]

    print(a.id, a.title, a.barcode, a.albumsort)
    print(b.id, b.title, b.barcode, b.albumsort)
    print(c.id, c.title, c.barcode, c.albumsort)
    print(d.id, d.title, d.barcode, d.albumsort)
    print(e.id, e.title, e.barcode, e.albumsort)
    print(f.id, f.title, f.barcode, f.albumsort)
    print(g.id, g.title, g.barcode, g.albumsort)
    print()

    d.title = "new_title"

    print(a.id, a.title, a.barcode, a.albumsort)
    print(b.id, b.title, b.barcode, b.albumsort)
    print(c.id, c.title, c.barcode, c.albumsort)
    print(d.id, d.title, d.barcode, d.albumsort)
    print(e.id, e.title, e.barcode, e.albumsort)
    print(f.id, f.title, f.barcode, f.albumsort)
    print(g.id, g.title, g.barcode, g.albumsort)
    print()

    print(artist.main_album_collection._indexed_values)