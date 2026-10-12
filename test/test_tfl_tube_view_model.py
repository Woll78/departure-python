from departure.provider.tfl_tube import view_model


def trains(*towards_and_seconds):
    return {
        f"central-{i}": {"towards": towards, "time_to_station": seconds}
        for i, (towards, seconds) in enumerate(towards_and_seconds)
    }


def model():
    return view_model.ViewModelTflTube_192_32()


def test_no_trains_shows_no_service():
    tfl_model = model()

    top_pixels, _, middle_pixels, _, bottom_pixels, _ = tfl_model.next_content({})

    expected, _ = tfl_model.board_text.colour_text_pixels([["No service", "orange"]])
    assert top_pixels == expected
    assert middle_pixels == []
    assert bottom_pixels == []


def test_three_trains_shows_third_train_in_slot_3():
    tfl_model = model()
    next_trains = trains(("Ealing Broadway", 60), ("West Ruislip", 120), ("Northolt", 180))

    *_, bottom_pixels, _ = tfl_model.next_content(next_trains)

    third_train = {"towards": "Northolt", "time_to_station": 180}
    expected, _ = tfl_model.pixels_single_line(third_train, "3")
    assert bottom_pixels == expected


def test_trains_are_shown_in_order_of_arrival():
    tfl_model = model()
    # dict order deliberately differs from arrival order
    next_trains = trains(("Northolt", 180), ("Ealing Broadway", 60), ("West Ruislip", 120))

    top_pixels, _, middle_pixels, _, _, _ = tfl_model.next_content(next_trains)

    first, _ = tfl_model.pixels_single_line(
        {"towards": "Ealing Broadway", "time_to_station": 60}, "1"
    )
    second, _ = tfl_model.pixels_single_line(
        {"towards": "West Ruislip", "time_to_station": 120}, "2"
    )
    assert top_pixels == first
    assert middle_pixels == second
