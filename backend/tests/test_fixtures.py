import pytest

from app.parser.parse import parse_html


class TestHappyPathFixture:
    @pytest.fixture(autouse=True)
    def _setup(self, load_fixture):
        self.result = parse_html(load_fixture("happy_path.html"))

    def test_title_is_extracted_correctly(self):
        assert self.result["title"] == "Example Page"

    def test_meta_description_is_extracted_correctly(self):
        assert self.result["meta_description"] == "An example page for testing."

    def test_h1_count_is_one(self):
        assert self.result["h1_count"] == 1

    def test_total_images_is_two(self):
        assert self.result["total_images"] == 2

    def test_one_image_is_missing_alt(self):
        assert self.result["images_missing_alt"] == 1

    def test_approx_word_count_is_positive(self):
        assert self.result["approx_word_count"] > 0

    def test_all_six_keys_are_present(self):
        required = {
            "title", "meta_description", "h1_count",
            "total_images", "images_missing_alt", "approx_word_count",
        }
        assert set(self.result.keys()) == required


class TestMissingMetadataFixture:
    @pytest.fixture(autouse=True)
    def _setup(self, load_fixture):
        self.result = parse_html(load_fixture("missing_metadata.html"))

    def test_title_is_none_when_tag_absent(self):
        assert self.result["title"] is None

    def test_meta_description_is_none_when_tag_absent(self):
        assert self.result["meta_description"] is None

    def test_h1_count_is_one(self):
        assert self.result["h1_count"] == 1

    def test_no_images_in_fixture(self):
        assert self.result["total_images"] == 0
        assert self.result["images_missing_alt"] == 0

    def test_word_count_is_positive(self):
        assert self.result["approx_word_count"] > 0

    def test_does_not_raise(self):
        assert self.result is not None


class TestMalformedFixture:
    @pytest.fixture(autouse=True)
    def _setup(self, load_fixture):
        self.result = parse_html(load_fixture("malformed.html"))

    def test_does_not_raise_on_malformed_html(self):
        assert self.result is not None

    def test_all_fields_are_correct_types(self):
        assert isinstance(self.result["title"], (str, type(None)))
        assert isinstance(self.result["meta_description"], (str, type(None)))
        assert isinstance(self.result["h1_count"], int)
        assert isinstance(self.result["total_images"], int)
        assert isinstance(self.result["images_missing_alt"], int)
        assert isinstance(self.result["approx_word_count"], int)

    def test_integer_fields_are_non_negative(self):
        assert self.result["h1_count"] >= 0
        assert self.result["total_images"] >= 0
        assert self.result["images_missing_alt"] >= 0
        assert self.result["approx_word_count"] >= 0

    def test_images_missing_alt_never_exceeds_total_images(self):
        assert self.result["images_missing_alt"] <= self.result["total_images"]

    def test_best_effort_title_extracted(self):
        assert self.result["title"] is not None
        assert len(self.result["title"]) > 0
