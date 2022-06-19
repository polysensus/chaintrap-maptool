class TestCorridor:

    def test_entangle_horizontal(self, spur_horizontal):

        g = spur_horizontal

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.check_entangled(cb)
        assert cb.check_entangled(ca)

    def test_entangle_horizontal_opposed(self, spur_horizontal_opposed):

        g = spur_horizontal_opposed

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.check_entangled(cb)
        assert cb.check_entangled(ca)

    def test_entangle_horizontal_inverted(self, spur_horizontal_inverted):

        g = spur_horizontal_inverted

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.check_entangled(cb)
        assert cb.check_entangled(ca)


    def test_entangle_horizontal_11(self, spur_horizontal_11):

        g = spur_horizontal_11

        ca = g.corridors[0]
        cb = g.corridors[1]

        assert ca.check_entangled(cb)
        assert cb.check_entangled(ca)

