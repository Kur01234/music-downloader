# Shell

## Searching

```mkshell
> s: {querry or url}

# examples
> s: https://musify.club/release/some-random-release-183028492
> s: r: #a an Artist #r some random Release
```

Searches for an url, or a query

### Query Syntax

```
#a {artist} #r {release} #t {track}
```

You can escape stuff like `#` doing this: `\#`

## Downloading

To download something, you either need a direct link, or you need to have already searched for options

```mkshell
> d: {option ids or direct url}

# examples
> d: 0, 3, 4
> d: 1
> d: https://musify.club/release/some-random-release-183028492
```

## Results

If options are printed in **bold** they can be downloaded. Else they may or maybe can't be downloaded

## Misc

### Exit

```mkshell
> q
> quit
> exit
> abort
```

### Current Options

```mkshell
> .
```

### Previous Options

```
> ..
```
