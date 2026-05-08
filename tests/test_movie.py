import pytest

from letterboxdpy.core.exceptions import MovieNotFoundError, ResourceNotFoundError
from letterboxdpy.movie import Movie


@pytest.fixture
def v_for_vendetta():
    """Constructed inside each test's VCR cassette context."""
    return Movie("v-for-vendetta")


class TestMovie:
    def test_get_not_exists_banner_movie(self):
        instance = Movie("avatar-4")
        assert instance.banner is None

    def test_get_exists_banner_movie(self, v_for_vendetta):
        assert v_for_vendetta.banner is not None

    def test_get_movie_title(self, v_for_vendetta):
        assert v_for_vendetta.title == "V for Vendetta"

    def test_get_movie_year(self, v_for_vendetta):
        assert v_for_vendetta.year == 2005

    def test_movie_original_title_nullable(self, v_for_vendetta):
        assert v_for_vendetta.original_title is None

    def test_non_english_movie_original_title(self):
        movie = Movie("parasite-2019")
        assert movie.title == "Parasite"
        assert movie.original_title is not None
        assert movie.title != movie.original_title
        assert movie.original_title == "기생충"

    def test_empty_init(self):
        with pytest.raises(AssertionError):
            Movie()

    def test_movie_not_found_slug(self):
        with pytest.raises(ResourceNotFoundError):
            Movie("this-movie-does-not-exist-999")

    def test_movie_not_found_tmdb(self):
        with pytest.raises(MovieNotFoundError):
            Movie(tmdb=999999999)

    def test_init_tmdb(self):
        movie = Movie(tmdb=27205)
        assert movie.title == "Inception"
        assert movie.year == 2010
        assert movie.slug == "inception"
        assert str(movie.tmdb_id) == "27205"

    def test_init_imdb(self):
        movie = Movie(imdb="tt0133093")
        assert movie.title == "The Matrix"
        assert movie.year == 1999
        assert movie.slug == "the-matrix"
        assert movie.imdb_id == "tt0133093"

    def test_from_tmdb_factory(self):
        movie = Movie.from_tmdb(603)
        assert movie.slug == "the-matrix"

    def test_from_imdb_factory(self):
        movie = Movie.from_imdb("tt0133093")
        assert movie.slug == "the-matrix"
