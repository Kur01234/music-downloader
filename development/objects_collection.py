import music_kraken
from music_kraken.objects import Song, Album, Artist, Collection

if __name__ == "__main__":
    song_1 = Song(
        title="song",
        feature_artist_list=[Artist(
            name="main_artist"
        )]
    )

    other_artist = Artist(name="other_artist")

    song_2 = Song(
        title = "song",
        artist_list=[other_artist]
    )

    other_artist.name = "main_artist"

    song_1.merge(song_2)

    print("#" * 120)
    print("main", *song_1.artist_collection)
    print("feat", *song_1.feature_artist_collection)
