from similarity_service import local_similarity, profile_of, split_meals


def test_exact_and_alias_are_identical():
    assert local_similarity(profile_of("돈까스"), profile_of("돈가스")) == 1.0


def test_semantically_related_cutlets_are_detected():
    assert local_similarity(profile_of("돈가스"), profile_of("치킨가스")) >= 0.8


def test_semantically_related_stews_are_detected():
    assert local_similarity(profile_of("김치찌개"), profile_of("부대찌개")) >= 0.8


def test_unrelated_meals_have_lower_similarity():
    related = local_similarity(profile_of("짜장면"), profile_of("간짜장"))
    unrelated = local_similarity(profile_of("짜장면"), profile_of("샐러드"))
    assert related > unrelated


def test_multiple_meals_are_split_by_common_separators():
    assert split_meals("돈가스, 햄버거 / 샐러드") == ["돈가스", "햄버거", "샐러드"]


def test_duplicate_meals_are_removed_when_splitting():
    assert split_meals("돈가스, 돈가스") == ["돈가스"]
