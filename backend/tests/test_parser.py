from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.parser.headings import count_h1
from app.parser.images import audit_images
from app.parser.meta_description import extract_meta_description
from app.parser.parse import parse_html
from app.parser.title import extract_title
from app.parser.word_count import approx_word_count

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class TestExtractTitle:
    def test_returns_title_text_when_present(self):
        soup = _soup("<html><head><title>My Page</title></head></html>")
        assert extract_title(soup) == "My Page"

    def test_strips_surrounding_whitespace(self):
        soup = _soup("<title>  Padded Title  </title>")
        assert extract_title(soup) == "Padded Title"

    def test_returns_none_when_title_tag_absent(self):
        soup = _soup("<html><head></head><body></body></html>")
        assert extract_title(soup) is None

    def test_returns_none_when_title_tag_is_empty(self):
        soup = _soup("<title></title>")
        assert extract_title(soup) is None

    def test_returns_none_when_title_is_whitespace_only(self):
        soup = _soup("<title>   </title>")
        assert extract_title(soup) is None

    def test_returns_none_on_empty_html_string(self):
        soup = _soup("")
        assert extract_title(soup) is None


class TestExtractMetaDescription:
    def test_returns_content_when_present(self):
        soup = _soup('<meta name="description" content="A page about things.">')
        assert extract_meta_description(soup) == "A page about things."

    def test_is_case_insensitive_on_name_attribute(self):
        soup = _soup('<meta name="Description" content="Case test.">')
        assert extract_meta_description(soup) == "Case test."

    def test_returns_none_when_tag_absent(self):
        soup = _soup("<html><head></head></html>")
        assert extract_meta_description(soup) is None

    def test_returns_none_when_content_is_empty(self):
        soup = _soup('<meta name="description" content="">')
        assert extract_meta_description(soup) is None

    def test_returns_none_when_content_is_whitespace_only(self):
        soup = _soup('<meta name="description" content="   ">')
        assert extract_meta_description(soup) is None

    def test_strips_whitespace_from_content(self):
        soup = _soup('<meta name="description" content="  trimmed  ">')
        assert extract_meta_description(soup) == "trimmed"


class TestCountH1:
    def test_returns_zero_when_no_h1(self):
        soup = _soup("<html><body><h2>subtitle</h2></body></html>")
        assert count_h1(soup) == 0

    def test_returns_one_for_single_h1(self):
        soup = _soup("<html><body><h1>Main Heading</h1></body></html>")
        assert count_h1(soup) == 1

    def test_returns_correct_count_for_multiple_h1s(self):
        soup = _soup("<h1>First</h1><h1>Second</h1><h1>Third</h1>")
        assert count_h1(soup) == 3

    def test_returns_zero_on_empty_document(self):
        soup = _soup("")
        assert count_h1(soup) == 0


class TestAuditImages:
    def test_returns_zeros_when_no_images(self):
        soup = _soup("<html><body><p>text</p></body></html>")
        total, missing = audit_images(soup)
        assert total == 0
        assert missing == 0

    def test_counts_image_with_good_alt_as_not_missing(self):
        soup = _soup('<img src="a.jpg" alt="A description">')
        total, missing = audit_images(soup)
        assert total == 1
        assert missing == 0

    def test_flags_image_with_no_alt_attribute(self):
        soup = _soup('<img src="a.jpg">')
        total, missing = audit_images(soup)
        assert total == 1
        assert missing == 1

    def test_flags_image_with_empty_alt(self):
        soup = _soup('<img src="a.jpg" alt="">')
        total, missing = audit_images(soup)
        assert total == 1
        assert missing == 1

    def test_flags_image_with_whitespace_only_alt(self):
        soup = _soup('<img src="a.jpg" alt="   ">')
        total, missing = audit_images(soup)
        assert total == 1
        assert missing == 1

    def test_counts_mixed_alt_states_correctly(self):
        html = (
            '<img src="a.jpg" alt="good">'
            '<img src="b.jpg">'
            '<img src="c.jpg" alt="">'
            '<img src="d.jpg" alt="   ">'
        )
        soup = _soup(html)
        total, missing = audit_images(soup)
        assert total == 4
        assert missing == 3


class TestApproxWordCount:
    def test_counts_visible_words(self):
        soup = _soup("<p>hello world</p>")
        assert approx_word_count(soup) == 2

    def test_returns_zero_on_empty_document(self):
        soup = _soup("")
        assert approx_word_count(soup) == 0

    def test_excludes_script_content_from_count(self):
        soup = _soup(
            "<p>visible words</p>"
            "<script>var x = 'these should not be counted';</script>"
        )
        count = approx_word_count(soup)
        assert count == 2

    def test_excludes_style_content_from_count(self):
        soup = _soup(
            "<p>only this</p>"
            "<style>.hidden { display: none; color: red; }</style>"
        )
        assert approx_word_count(soup) == 2

    def test_excludes_noscript_content_from_count(self):
        soup = _soup(
            "<p>real content</p>"
            "<noscript>please enable javascript</noscript>"
        )
        assert approx_word_count(soup) == 2

    def test_mutates_tree_by_removing_invisible_tags(self):
        soup = _soup("<p>text</p><script>js</script>")
        approx_word_count(soup)
        assert soup.find("script") is None


class TestParseHtml:
    def test_happy_path_extracts_all_signals_correctly(self):
        result = parse_html(load_fixture("happy_path.html"))

        assert result["title"] == "Example Page"
        assert result["meta_description"] == "An example page for testing."
        assert result["h1_count"] == 1
        assert result["total_images"] == 2
        assert result["images_missing_alt"] == 1
        assert result["approx_word_count"] > 0

    def test_missing_title_and_meta_resolve_to_none_not_raise(self):
        result = parse_html(load_fixture("missing_metadata.html"))

        assert result["title"] is None
        assert result["meta_description"] is None
        assert result["h1_count"] == 1

    def test_malformed_html_does_not_raise_and_returns_best_effort(self):
        result = parse_html(load_fixture("malformed.html"))

        assert isinstance(result["h1_count"], int)
        assert isinstance(result["approx_word_count"], int)
        assert isinstance(result["total_images"], int)
        assert isinstance(result["images_missing_alt"], int)

    def test_multiple_h1s_and_script_stripping(self):
        result = parse_html(load_fixture("multiple_h1_and_scripts.html"))

        assert result["h1_count"] == 3
        assert result["approx_word_count"] > 0
        assert result["approx_word_count"] < 30

    def test_mixed_alt_states_in_integration(self):
        result = parse_html(load_fixture("multiple_h1_and_scripts.html"))

        assert result["total_images"] == 4
        assert result["images_missing_alt"] == 3

    def test_case_insensitive_meta_name_in_integration(self):
        result = parse_html(load_fixture("multiple_h1_and_scripts.html"))
        assert result["meta_description"] == "Case-insensitive meta check."

    def test_whitespace_title_is_stripped(self):
        result = parse_html(load_fixture("multiple_h1_and_scripts.html"))
        assert result["title"] == "Whitespace Title"

    def test_empty_html_string_does_not_raise(self):
        result = parse_html("")

        assert result["title"] is None
        assert result["meta_description"] is None
        assert result["h1_count"] == 0
        assert result["total_images"] == 0
        assert result["images_missing_alt"] == 0
        assert result["approx_word_count"] == 0

    def test_parse_result_has_all_required_keys(self):
        result = parse_html("<html></html>")

        required_keys = {
            "title",
            "meta_description",
            "h1_count",
            "total_images",
            "images_missing_alt",
            "approx_word_count",
        }
        assert required_keys == set(result.keys())
