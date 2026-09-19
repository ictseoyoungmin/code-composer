from code_composer.theory import (
    quantize_to_scale, scale_degree_to_midi,
    triad_from_degree, nearest_inversion, voice_leading_cost
)

def run():
    assert scale_degree_to_midi("D", "natural_minor", 1, 4) == 62
    assert scale_degree_to_midi("D", "natural_minor", 8, 4) == 74
    assert quantize_to_scale(63, "D", "natural_minor") in (62, 64)
    triad = triad_from_degree("D", "natural_minor", 1, 4)
    assert triad == [62, 65, 69]
    voiced = nearest_inversion(triad, 60)
    assert len(voiced) == 3
    assert voice_leading_cost([60,64,67],[60,65,69]) >= 0
    print("test_theory: OK")

if __name__ == "__main__":
    run()


def test_regression():
    run()
