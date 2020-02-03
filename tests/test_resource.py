from pytest import raises


def test_pattern_child_fails_when_no_pattern_child_exists():
    from mulatu.tree import Resource

    with raises(StopIteration):
        Resource(None, "/", None).pattern_child
