#!/usr/bin/env python3
import sys
import json
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from scripts.validate_dataset_syntax import validate_sample_fol
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


# Define manual, 1-to-1 aligned, Z3-valid FOL formulas for each of the 5 stories
MANUAL_PATCHES = {
    34: [
        "ForAll(x, (change_major(x) -> gpa(x) >= 7.0))",
        "ForAll(x, (change_major(x) -> semesters(x) >= 2))",
        "ForAll(x, (change_major(x) -> accumulated_credits(x) >= half_total_credits(x)))",
        "ForAll(x, (change_major(x) -> similarity(x) >= 60))",
        "ForAll(x, (major_courses_taken(x) -> equivalent_assessment(x)))",
        "ForAll(x, (change_major(x) -> council_approval(x)))",
        "ForAll(x, (council_approval(x) -> march(x) OR september(x)))",
        "ForAll(x, (change_major(x) -> application_days(x) >= 30))",
        "ForAll(x, (late_application(x) -> wait_next_term(x) AND penalty(x) = ten_percent_tuition(x)))",
        "ForAll(x, (change_major(x) -> change_fee(x) = half_tuition(x) OR policy_eligible(x)))",
        "ForAll(x, (scholarship(x) AND change_major(x) -> separate_review(x)))",
        "ForAll(x, (scholarship_revoked(x) -> repayment(x) = quarter_scholarship_value(x)))",
        "ForAll(x, (change_major(x) -> make_up_courses_limit(x) AND make_up_credits(x) <= 15))",
        "ForAll(x, (failed_make_up_courses(x) -> academic_suspension(x)))",
        "ForAll(x, (gpa(x) < 6.0 AND change_major(x) -> academic_warning(x)))",
        "ForAll(x, (academic_warning(x) AND next_term_gpa(x) > 6.5 AND NOT violation(x) -> lift_warning(x)))",
        "ForAll(x, (change_major(x) -> change_count(x) <= 1 OR special_case(x)))",
        "ForAll(x, (change_major(x) -> credit_retention(x) >= 70))",
        "ForAll(x, (policy_eligible(x) -> fee_discount(x) = twenty_percent_fee(x) AND priority_review(x)))",
        "ForAll(x, (entrance_exam(x) -> exam_score(x) >= seventy_five_percent_standard(x)))",
        "ForAll(x, (application_fraud(x) -> NOT council_approval(x)))",
        "gpa(Mai) = 7.2 AND semesters(Mai) = 3",
        "change_major(Mai, IT, BiomedicalEng) AND similarity(Mai) = 65",
        "accumulated_credits(Mai) = 45 AND total_credits(Mai) = 90 AND application_days(Mai) = 45",
        "scholarship(Mai) = half_tuition(Mai) AND change_count(Mai) = 0",
        "entrance_exam(Mai) AND standard_score(Mai) = 80",
        "exam_score(Mai) = 78"
    ],
    379: [
        "ForAll(s, (EligibleForInternship(s) <-> AccumulatedCredits(s) >= 78))",
        "TotalCredits(TrainingProgram) = 120",
        "AccumulatedCredits(Ha) = 80",
        "ForAll(s, (EligibleForInternship(s) -> SubmittedApplicationBeforeJune1(s)))",
        "SubmittedApplicationBeforeJune1(Ha)",
        "ElectiveCredits(TrainingProgram) = 30 AND CountedElectiveCredits(TrainingProgram) = 20",
        "AccumulatedCredits(Vinh) = 75 AND Program(Vinh, TrainingProgram)",
        "ForAll(s, (GPA(s) < 2.5 -> RequiresRemedialCourse(s)))",
        "GPA(Ha) = 3.2 AND NOT RequiresRemedialCourse(Ha)",
        "InternshipCycle(Summer) AND InternshipCycle(Fall) AND Priority(Summer, Seniors)",
        "Status(Ha, Junior) AND ApplyingFor(Ha, Fall)",
        "ForAll(s, (EligibleForInternship(s) -> ApprovedByAdvisor(s))) AND ApprovedByAdvisor(Ha)",
        "NOT SubmittedApplicationBeforeJune1(Vinh) AND ElectiveCreditsAccumulated(Vinh) = 10"
    ],
    380: [
        "ForAll(s, ((AverageScore(s) >= 3.6 AND AverageScore(s) <= 4.0) -> Ranking_Excellent(s))) AND ForAll(s, ((AverageScore(s) >= 3.2 AND AverageScore(s) < 3.6) -> Ranking_Good(s))) AND ForAll(s, ((AverageScore(s) >= 2.5 AND AverageScore(s) < 3.2) -> Ranking_Fair(s))) AND ForAll(s, ((AverageScore(s) >= 2.0 AND AverageScore(s) < 2.5) -> Ranking_Average(s))) AND ForAll(s, ((AverageScore(s) >= 1.0 AND AverageScore(s) < 2.0) -> Ranking_Weak(s))) AND ForAll(s, (AverageScore(s) < 1.0 -> Ranking_Poor(s)))",
        "AverageScore(Phong) = 2.3",
        "ForAll(s, (Ranking_Excellent(s) -> Scholarship(s, dollar500)))",
        "Semester(Phong) = 3 AND Credits(Phong) = 15",
        "AverageScore(Hoa) = 3.7 AND Ranking_Excellent(Hoa)",
        "ForAll(s, (AverageScore(s) = WeightedScore(s)))",
        "ExamScore(Phong) = 2.5 AND ProjectScore(Phong) = 2.0",
        "ForAll(s, ((Ranking_Average(s) OR Ranking_Weak(s) OR Ranking_Poor(s)) -> MustAttendWorkshop(s)))",
        "MaxScorePerCourse() = 4.0 AND EnrolledCourses(Phong) = 4",
        "PartTimeJob(Hoa) AND Ranking_Excellent(Hoa)",
        "IsReviewDeadline(December20)",
        "SubmittedOnTime(Phong, FinalProject) AND NOT Penalty(Phong, point_0_5)"
    ],
    381: [
        "ForAll(s, (SecondYear(s) <-> ((AccumulatedCredits(s) >= M_credits) AND (AccumulatedCredits(s) < double_M_credits) AND MeetsLanguageStandard(s, YearTwo))))",
        "M_credits = 33",
        "AccumulatedCredits(Tam) = 40 AND MeetsLanguageStandard(Tam, YearTwo)",
        "M_accelerated = 40",
        "Program(Tam, Regular) AND NOT Program(Tam, Accelerated)",
        "AccumulatedCredits(Nam) = 70 AND NOT MeetsLanguageStandard(Nam, YearTwo)",
        "ForAll(s, (MeetsLanguageStandard(s, YearTwo) <-> TOEFLScore(s) >= 500))",
        "TOEFLScore(Tam) = 550 AND SubmittedBefore(Tam, October1)",
        "ForAll(s, (CoreCredits(s, CurrentYear) >= 10)) AND CoreCredits(Tam, CurrentYear) = 15",
        "Semester(Nam) = 3 AND GPA(Nam) = 3.0",
        "ForAll(s, (SecondYear(s) AND AppliedBefore(s, November15) -> EligibleMentorship(s)))",
        "AppliedBefore(Tam, November10)",
        "TotalCredits(RegularProgram) = 132"
    ],
    382: [
        "ForAll(s, (ThirdYear(s) <-> ((AccumulatedCredits(s) >= double_M_credits) AND (AccumulatedCredits(s) < triple_M_credits) AND MeetsLanguageStandard(s, YearThree))))",
        "M_credits = 33",
        "AccumulatedCredits(Phong) = 70 AND MeetsLanguageStandard(Phong, YearThree)",
        "ForAll(s, (MeetsLanguageStandard(s, YearThree) <-> IELTS(s) >= 6.0))",
        "IELTS(Phong) = 6.5 AND Certified(Phong, LastMonth)",
        "M_honors = 36",
        "Program(Phong, Regular) AND NOT Program(Phong, Honors)",
        "AccumulatedCredits(Lan) = 60 AND MeetsLanguageStandard(Lan, YearTwo) AND NOT MeetsLanguageStandard(Lan, YearThree)",
        "ForAll(s, (ThirdYear(s) -> Enrolled(s, CapstoneProject) AND Credits(CapstoneProject) = 5)) AND Enrolled(Phong, CapstoneProject)",
        "TotalCredits(RegularProgram) = 132",
        "GPA(Phong) = 3.4 AND NOT OnProbation(Phong)",
        "NOT CertifiedBefore(Lan, September30)",
        "ForAll(s, (ThirdYear(s) AND MeetsLanguageStandard(s, YearThree) -> EligibleStudyAbroad(s)))"
    ]
}


def main():
    print("=" * 80)
    print("MANUALLY PATCHING REMAINING MISMATCHED STORIES")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    input_file = data_dir / "logic_based.json"

    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    patched_count = 0

    for idx, fol_list in MANUAL_PATCHES.items():
        sample = dataset[idx]
        nl_list = sample["premises-NL"]
        
        # Verify alignment count
        if len(nl_list) != len(fol_list):
            print(f"ERROR: Story {idx} NL has {len(nl_list)} items but manual FOL has {len(fol_list)} items.")
            sys.exit(1)

        # Run Z3 validator
        is_valid, z3_error = validate_sample_fol(fol_list)
        if not is_valid:
            print(f"ERROR: Story {idx} failed Z3 validation: {z3_error}")
            sys.exit(1)

        print(f"Story {idx}: Successfully aligned (length {len(nl_list)}) and Z3-validated.")
        
        # Apply patch
        sample["premises-FOL"] = fol_list
        patched_count += 1

    # Save dataset
    print(f"\nSaving {patched_count} manually patched stories to {input_file.name}...")
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print("Saved successfully.")
    print("=" * 80)


if __name__ == "__main__":
    main()
