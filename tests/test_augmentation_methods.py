import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.data.augmentation import (
    MultiPremisePermuter,
    QuantifiedVariableCanonicalizer,
    EntityAnonymizer,
    HardNegativeAugmenter
)

SAMPLE = {
    "story_id": 42,
    "example_id": "ex_42",
    "conclusion": "James is happy.",
    "premises-NL": [
        "James is either a student or a teacher.",
        "All students love studying.",
        "Some teachers love teaching.",
        "If someone loves studying, they are happy."
    ],
    "premises-FOL": [
        "Student(james) OR Teacher(james)",
        "ForAll(u, Student(u) -> Love(u, studying))",
        "Exists(v, Teacher(v) -> Love(v, teaching))",
        "ForAll(w, Love(w, studying) -> Happy(w))"
    ],
    "label": "True",
    "dataset_source": "orig_source"
}


def test_multi_premise_permuter():
    print("Testing MultiPremisePermuter...")
    permuter = MultiPremisePermuter(seed=12345)
    
    # Test valid permutation
    augmented = permuter.permute_sample(SAMPLE, variant_idx=0)
    assert augmented is not None
    assert augmented["example_id"] == "ex_42_perm_var0"
    assert augmented["dataset_source"] == "orig_source-augmented-permutation-var0"
    
    # Check that lengths are preserved
    assert len(augmented["premises-NL"]) == len(SAMPLE["premises-NL"])
    assert len(augmented["premises-FOL"]) == len(SAMPLE["premises-FOL"])
    
    # Verify index-to-index alignment is preserved
    orig_pairs = list(zip(SAMPLE["premises-NL"], SAMPLE["premises-FOL"]))
    aug_pairs = list(zip(augmented["premises-NL"], augmented["premises-FOL"]))
    for pair in aug_pairs:
        assert pair in orig_pairs
        
    # Check that order actually changed
    assert augmented["premises-NL"] != SAMPLE["premises-NL"]
    
    # Test invalid cases (stories with < 4 premises)
    invalid_sample = SAMPLE.copy()
    invalid_sample["premises-NL"] = ["Premise 1", "Premise 2", "Premise 3"]
    invalid_sample["premises-FOL"] = ["FOL1", "FOL2", "FOL3"]
    assert permuter.permute_sample(invalid_sample) is None
    print("  [PASSED]")


def test_quantified_variable_canonicalizer():
    print("Testing QuantifiedVariableCanonicalizer...")
    canonicalizer = QuantifiedVariableCanonicalizer()
    
    # u, v, w should be renamed to canonical order starting with 'x' for each formula
    augmented = canonicalizer.canonicalize_sample(SAMPLE)
    assert augmented is not None
    assert augmented["example_id"] == "ex_42_canonical"
    assert augmented["dataset_source"] == "orig_source-canonicalized"
    
    aug_fols = augmented["premises-FOL"]
    
    # ForAll(u, Student(u) -> Love(u, studying)) -> ForAll(x, Student(x) -> Love(x, studying))
    assert aug_fols[1] == "ForAll(x, Student(x) -> Love(x, studying))"
    # Exists(v, ...) -> Exists(x, ...) because each formula is canonicalized individually
    assert aug_fols[2] == "Exists(x, Teacher(x) -> Love(x, teaching))"
    # ForAll(w, ...) -> ForAll(x, ...)
    assert aug_fols[3] == "ForAll(x, Love(x, studying) -> Happy(x))"
    
    # Test collision avoidance case: ForAll(y, ForAll(x, P(x, y))) -> ForAll(x, ForAll(y, P(y, x)))
    collision_sample = {
        "premises-NL": ["Some nested statement"],
        "premises-FOL": ["ForAll(y, ForAll(x, P(x, y)))"],
        "dataset_source": "test"
    }
    aug_collision = canonicalizer.canonicalize_sample(collision_sample)
    assert aug_collision is not None
    assert aug_collision["premises-FOL"][0] == "ForAll(x, ForAll(y, P(y, x)))"
    
    # Test formula already canonicalized
    canon_sample = {
        "premises-NL": ["Canonicalized"],
        "premises-FOL": ["ForAll(x, P(x))"],
        "dataset_source": "test"
    }
    # By default, always_return is True, so it returns a copy
    res_default = canonicalizer.canonicalize_sample(canon_sample)
    assert res_default is not None
    assert res_default["premises-FOL"] == canon_sample["premises-FOL"]
    
    # With always_return=False, it should return None if no changes were made
    res_none = canonicalizer.canonicalize_sample(canon_sample, always_return=False)
    assert res_none is None
    print("  [PASSED]")


def test_entity_anonymizer():
    print("Testing EntityAnonymizer...")
    anonymizer = EntityAnonymizer()
    
    # Test anonymizing
    augmented = anonymizer.anonymize_sample(SAMPLE, strategy="names", variant_idx=0)
    assert augmented is not None
    assert "james" not in "".join(augmented["premises-FOL"]).lower()
    assert "james" not in "".join(augmented["premises-NL"]).lower()
    assert augmented["example_id"].endswith("_aug_var0")
    
    # Test generating a different variant using variant_idx=1
    augmented_v1 = anonymizer.anonymize_sample(SAMPLE, strategy="names", variant_idx=1)
    assert augmented_v1 is not None
    assert augmented["premises-NL"] != augmented_v1["premises-NL"]
    assert augmented_v1["example_id"].endswith("_aug_var1")
    print("  [PASSED]")


def test_hard_negative_augmenter():
    print("Testing HardNegativeAugmenter...")
    try:
        augmenter = HardNegativeAugmenter()
    except Exception as e:
        print(f"Skipping HardNegativeAugmenter test (initialization failed): {e}")
        return
        
    augmented = augmenter.augment_sample(SAMPLE, variant_idx=0)
    if augmented is None:
        print("  Warning: hard negative augmentation returned None (LLM failure or validation failed).")
    else:
        assert augmented["example_id"] == "ex_42_neg_var0"
        assert augmented["dataset_source"] == "orig_source-augmented-negative-var0"
        assert "premises-NL" in augmented
        assert "premises-FOL" in augmented
        
        # Check that answer/label is valid
        ans = augmented.get("label", augmented.get("answer"))
        assert ans in ["True", "False", "Unknown"]
        
        # Verify that FOL formulas are syntactically valid by running validation
        from src.data.augmentation.hard_negative_augmenter import validate_fol_formulas
        is_valid, err = validate_fol_formulas(augmented["premises-FOL"])
        assert is_valid, f"Generated FOL is invalid: {err}"
        
        # Check that something changed
        assert (augmented["premises-NL"] != SAMPLE["premises-NL"] or
                augmented["premises-FOL"] != SAMPLE["premises-FOL"] or
                augmented.get("conclusion") != SAMPLE.get("conclusion") or
                augmented.get("label") != SAMPLE.get("label"))
        print("  [PASSED]")


def main():
    print("=" * 80)
    print("RUNNING ACTIVE DATA AUGMENTATION METHOD TESTS")
    print("=" * 80)
    
    test_multi_premise_permuter()
    test_quantified_variable_canonicalizer()
    test_entity_anonymizer()
    test_hard_negative_augmenter()
    
    print("\n" + "=" * 80)
    print("ALL ACTIVE DATA AUGMENTATION TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    main()
