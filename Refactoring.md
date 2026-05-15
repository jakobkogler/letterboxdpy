# Refactoring Plan

## Everything typed

Instead of returning a `dict` or `dict[str, Any]`, we return actual dataclasses.
Maybe with an `__getitem__` in order to be backwards compatible.

That way the users have actual safety, when they access some methods and don't need to experimentally run the code to see what's returned.

## Inconsistent Request Behavior

Currently some classes make requests (e.g. `Movie`), some don't (e.g. `Search`).

## Prevent creating those classes by themselv, use `from_`

Make it easy to use.
`Movie.from_slug(str)`, `Movie.from_imdb(str)`, ... instead of `Movie(slug=slug)`

`Search.find_movies(str) -> list[Movie]` instead of `Search(str, filter).find() -> list[dict]`.

## Consistency

Sometimes it's `name`, sometimes `title`, ...
Sometimes `film` sometimes `movie`.


## Improved search (e.g. by directors, year)

Currently not possible.
