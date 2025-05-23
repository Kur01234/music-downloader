# Music Kraken

[![Woodpecker CI Status](https://ci.elara.ws/api/badges/59/status.svg)](https://ci.elara.ws/repos/59)

<img src="https://gitea.elara.ws/music-kraken/music-kraken-core/media/branch/experimental/assets/logo.svg" width=300  alt="music kraken logo"/>

- [Installation](#installation)
- [Quick-Guide](#quick-guide)
  - [How to search properly](#query)
- [Matrix Space](#matrix-space)

If you want to use this a library or contribute, check out [the wiki](https://gitea.elara.ws/music-kraken/music-kraken-core/wiki) for more information.

---

## Installation

You can find and get this project from either [PyPI](https://pypi.org/project/music-kraken/) as a Python-Package,
or simply the source code from [Gitea](https://gitea.elara.ws/music-kraken/music-kraken-core). **

**NOTES**

- Even though everything **SHOULD** work cross-platform, I have  only tested it on Ubuntu.  
- If you enjoy this project, feel free to give it a star on GitHub.

### From source

```sh
git clone https://gitea.elara.ws/music-kraken/music-kraken-core.git
python3 -m pip install -e music-kraken-core/
```

To update the program, if installed like this, go into the `music-kraken-core` directory and run `git pull`.

### Get it running on other Systems

Here are the collected issues, that are related to running the program on different systems. If you have any issues, feel free to open a new one.

#### Windows + WSL

Add ` ~/.local/bin` to your `$PATH`. [#2][i2]

## Quick-Guide

The **Genre** you define at the start, is the folder my program will download the files into, as well as the value of the ID3 genre field.

When it drops you into the **shell** 2 main things are important:

1. You search with `s: <query/url>`
2. You choose an option with just the index number of the option
3. You download with `d: <options/url>`, where the options are comma separated

### Query

The syntax for the query is really simple.

```mk
> s: #a <any artist>
searches for the artist <any artist>

> s: #a <any artist> #r <any release>
searches for the release (album) <any release> by the artist <any artist>

> s: #r <any release> Me #t <any track>
searches for the track <any track> from the release <any relaese>
```

The escape character is as usual `\`.

---

## Matrix Space

<img align="right" alt="music-kraken logo" src="assets/element_logo.png" width=100>

I decided against creating a discord server, due to various communities get often banned from discord. A good and free Alternative are Matrix Spaces. I recommend the use of the Client [Element](https://element.io/download). It is completely open source.

**Click [this invitation](https://matrix.to/#/#music-kraken:matrix.org) _([https://matrix.to/#/#music-kraken:matrix.org](https://matrix.to/#/#music-kraken:matrix.org))_ to join.**

[i10]: https://github.com/HeIIow2/music-downloader/issues/10
[i2]: https://github.com/HeIIow2/music-downloader/issues/2
