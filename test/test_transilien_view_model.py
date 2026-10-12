from departure.provider.transilien import view_model


def trains(count):
    return [
        {"mission": f"M{i}", "time": f"10:0{i}", "terminus": f"Gare {i}"}
        for i in range(count)
    ]


def bottom_section(model, next_trains):
    *_, pixels, size = model.next_content(next_trains)
    return pixels, size


def expected_rows(model, next_trains):
    return model.board_text.colour_text_tabbed_rows_pixels(
        [model.text_array_train_overview(train, i + 3) for i, train in enumerate(next_trains)],
        row_height=11,
    )


def test_fewer_than_three_trains_leave_bottom_section_empty():
    model = view_model.ViewModelTransilien_192_32()

    assert bottom_section(model, trains(2)) == ([], (0, 0))


def test_three_trains_show_third_train_in_bottom_section():
    model = view_model.ViewModelTransilien_192_32()
    next_trains = trains(3)

    assert bottom_section(model, next_trains) == expected_rows(model, next_trains[2:])


def test_bottom_section_lists_at_most_eight_trains():
    model = view_model.ViewModelTransilien_192_32()
    next_trains = trains(12)

    # 3rd to 10th trains
    assert bottom_section(model, next_trains) == expected_rows(model, next_trains[2:10])
