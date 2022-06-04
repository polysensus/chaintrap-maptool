from .randprimitives import rand_box, rand_split_box


def test_rand_split_box():
    box = rand_box(100.0, 76.0, 1.1, 2.0)
    boxw, boxh = box.width_height()

    a, b = rand_split_box(box)
    aw, ah = a.width_height()
    bw, bh = b.width_height()
    assert aw != boxw or ah != boxh
    assert bw < boxw or bh < boxh
