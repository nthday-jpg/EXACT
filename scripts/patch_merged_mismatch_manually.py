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

fol_733 = [
    "ForAll(s1, ForAll(s2, (IdenticalAnswersPercentage(s1, s2) > 90 -> MayIndicateCheating(s1))))",
    "ForAll(s1, ForAll(s2, (SubmissionTimeDifference(s1, s2) < 1 -> (FurtherReviewRequired(s1) AND FurtherReviewRequired(s2)))))",
    "ForAll(s, (CompletionPercentageOfAverage(s) < 50 -> MayIndicateAnomalies(s)))",
    "ForAll(s, (UsesRareTermsWithoutCitation(s) -> MayIndicatePlagiarism(s)))",
    "ForAll(s, (GazeLeavingScreenCount(s) > 10 -> MayIndicateCheating(s)))",
    "ForAll(s, (HistoryOfViolations(s) -> RecurrenceProbabilityIncrease(s) = 20))",
    "ForAll(s, (BoardConfirmsCheating(s) -> (Suspended(s) AND ExamScore(s) = 0)))",
    "ForAll(s, (AICheatingConfidence(s) > 95 -> BoardMustConveneWithin48Hours()))",
    "ForAll(s, (NOT Suspended(s) -> CanAppealWithin7Days(s)))",
    "ForAll(s, (AppealDenied(s) -> (MustRetakeCourse(s) AND TuitionPenaltyPercentage(s) = 30)))",
    "ForAll(s, (UsesSecondDevice(s) -> SeriousViolation(s)))",
    "ForAll(s, (CommunicatingViaHeadphones(s) -> ExamInvalidated(s)))",
    "ForAll(e, (TechnicalErrorsCount(e) > 3 -> ExamRescheduled(e)))",
    "ForAll(s, (NOT CameraOnThroughout(s) -> ViolatedRegulations(s)))",
    "ForAll(s, (LateSubmissionMinutes(s) > 5 -> DeductionFromScorePercentage(s) = 10))",
    "ForAll(e, (CheatingSuspectsPercentage(e) > 50 -> ExamReinvestigated(e)))",
    "ForAll(s, (PerfectScore(s) AND AnomaliesDetected(s) -> CrossCheckWithAIDataRequired(s)))",
    "ForAll(s, (BoardConvenedAfter72Hours() -> RightToRequestReview(s)))",
    "ForAll(s, (PreviouslySuspended(s) -> NOT CanAppealThisTime(s)))",
    "ForAll(s, (AIMalfunction() -> CheatingResultsManuallyReviewed()))",
    "ForAll(s, (CourseAverageBeforeExam(s) < 5.0 -> UnderSpecialSurveillance(s)))",
    "ForAll(s, (LeavesSeatDuringOnlineExam(s) -> ViolatedRegulations(s)))",
    "ForAll(s, (UnusualExamFormat(s) -> TechnicalInspectionRequired(s)))",
    "ForAll(s, (NOT CorrectAccountLogin(s) -> ExamNotAccepted(s)))",
    "ForAll(s, (CheatingEvidenceFromStoredCameraFootage(s) -> SubjectToAdditionalFine(s)))",
    "IdenticalAnswersPercentage(StudentA, StudentB) = 95",
    "SubmissionTimeDifference(StudentA, StudentB) = 0.5",
    "CompletionPercentageOfAverage(StudentA) = 37",
    "UsesRareTermsWithoutCitation(StudentA)",
    "GazeLeavingScreenCount(StudentA) = 12",
    "HistoryOfViolations(StudentA)",
    "AICheatingConfidence(StudentA) = 97",
    "BoardMustConveneWithin48Hours() AND NOT BoardConvenedAfter72Hours()",
    "CanAppealWithin7Days(StudentA)"
]

fol_741 = [
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
]

fol_378 = [
    "ForAll(s, (FullTimeStudent(s) -> (Credits(s) >= 14 OR (SpecialCase(s) AND Credits(s) >= 11))))",
    "ForAll(s, (PartTimeStudent(s) -> (Credits(s) >= 11 OR (SpecialCase(s) AND Credits(s) >= 9))))",
    "FullTimeStudent(Linh) AND SpecialCase(Linh) AND Credits(Linh) = 12",
    "SemesterCountSpecialCase(Linh) = 1",
    "ForAll(s, (PartTimeStudent(s) -> MustSubmitWorkSchedule(s)))",
    "ForAll(s, (FullTimeStudent(s) AND Credits(s) < 14 -> MustMeetAdvisor(s)))",
    "Enrolled(Linh, LabCourse) AND Credits(LabCourse) = 4 AND Enrolled(Linh, LectureCourse1) AND Credits(LectureCourse1) = 4 AND Enrolled(Linh, LectureCourse2) AND Credits(LectureCourse2) = 4",
    "PartTimeStudent(Minh) AND SpecialCase(Minh) AND Credits(Minh) = 10",
    "ForAll(c, (Credits(c) > 3 -> AttendanceRequired(c, Percent_80)))",
    "ForAll(s, (Credits(s) = 12 -> EligibleForDiscount(s)))",
    "SemesterCountSpecialCase(Linh) <= 2",
    "WorkHours(Minh) = 20",
    "ForAll(s, (FullTimeStudent(s) AND Semester(s) >= 3 -> MustDeclareMajor(s))) AND Semester(Linh) = 2"
]

fol_382 = [
    "ForAll(s, (ThirdYear(s) <-> ((AccumulatedCredits(s) >= double_M_credits) AND (AccumulatedCredits(s) < triple_M_credits) AND MeetsLanguageStandard(s, YearThree))))",
    "M_credits = 33",
    "AccumulatedCredits(Phong) = 70 AND MeetsLanguageStandard(Phong, YearThree)",
    "ForAll(s, (MeetsLanguageStandard(s, YearThree) <-> IELTS(s) >= 6.0))",
    "IELTS(Phong) = 6.5 AND Certified(Phong, LastMonth)",
    "M_honors = 36",
    "Program(Phong, Regular) AND NOT Program(Phong, Honors)",
    "AccumulatedCredits(Lan) = 60 AND MeetsLanguageStandard(Lan, YearTwo) AND NOT MeetsLanguageStandard(Lan, YearThree)",
    "ForAll(s, (ThirdYear(s) -> (Enrolled(s, CapstoneProject) AND Credits(CapstoneProject) = 5))) AND Enrolled(Phong, CapstoneProject)",
    "TotalCredits(RegularProgram) = 132",
    "GPA(Phong) = 3.4 AND NOT OnProbation(Phong)",
    "NOT CertifiedBefore(Lan, September30)",
    "ForAll(s, (ThirdYear(s) AND MeetsLanguageStandard(s, YearThree) -> EligibleStudyAbroad(s)))"
]

def main():
    print("=" * 80)
    print("MANUALLY PATCHING REMAINING MISMATCHED STORIES IN LOGIC_MERGED_VALID.JSON")
    print("=" * 80)

    path = root_dir / "data" / "processed" / "logic_merged_valid.json"
    if not path.exists():
        print(f"Error: {path} not found.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} samples from {path.name}.")

    # Validate patches
    for label, fol in [("fol_733", fol_733), ("fol_741", fol_741), ("fol_378", fol_378), ("fol_382", fol_382)]:
        is_valid, err = validate_sample_fol(fol)
        if not is_valid:
            print(f"{label} validation failed: {err}")
            sys.exit(1)

    update_count = 0
    for item in data:
        story_id = str(item.get("story_id", ""))
        source = item.get("dataset_source", "")
        if story_id == "36" and source == "logic_based":
            item["premises-FOL"] = fol_733
            item.pop("validation_error", None)
            update_count += 1
        elif story_id == "379" and source == "logic_based":
            item["premises-FOL"] = fol_741
            item.pop("validation_error", None)
            update_count += 1
        elif story_id == "378" and source == "logic_based":
            item["premises-FOL"] = fol_378
            item.pop("validation_error", None)
            update_count += 1
        elif story_id == "382" and source == "logic_based":
            item["premises-FOL"] = fol_382
            item.pop("validation_error", None)
            update_count += 1

    print(f"Updated {update_count} samples in {path.name}.")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Repaired dataset saved successfully.")
    print("=" * 80)

if __name__ == "__main__":
    main()
