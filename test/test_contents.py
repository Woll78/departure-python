import pytest

from departure.board import contents

COLOURS = {"white": (255, 255, 255), "red": (255, 0, 0)}


@pytest.fixture(scope="module")
def board_text():
    font = contents.read_bdf_font("fonts/6x10_condensed.bdf")
    return contents.BoardText(
        font=font, colour_map=COLOURS, tabs=[[0, "l"], [40, "r"]]
    )


@pytest.fixture(scope="module")
def line_height(board_text):
    return board_text.font[b"FONT_ASCENT"] + board_text.font[b"FONT_DESCENT"]


class TestEmptyInput:
    def test_colour_text_empty_array(self, board_text, line_height):
        assert board_text.colour_text_pixels([]) == ([], (0, line_height))

    def test_tabbed_row_empty_row(self, board_text, line_height):
        assert board_text.colour_text_tabbed_row_pixels([]) == ([], (0, line_height))

    def test_tabbed_rows_with_an_empty_row(self, board_text):
        pixels, (width, height) = board_text.colour_text_tabbed_rows_pixels(
            [[], [["A", "white"]]], row_height=10
        )
        assert pixels and width > 0 and height == 20


class TestUnknownGlyphs:
    def test_unknown_char_renders_as_question_mark(self, board_text):
        # CJK is not in the font
        assert board_text.monochrome_text_pixels("中") == (
            board_text.monochrome_text_pixels("?")
        )

    def test_station_name_with_unknown_char_does_not_raise(self, board_text):
        pixels, size = board_text.colour_text_pixels([["Gare 中", "white"]])
        assert pixels and size[0] > 0

    def test_known_chars_unchanged(self, board_text):
        pixels, (advance, _) = board_text.monochrome_text_pixels("AB")
        single, (advance_a, _) = board_text.monochrome_text_pixels("A")
        assert pixels[: len(single)] == single and advance > advance_a
