import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from scripts.validate_dataset_syntax import validate_sample_fol

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

print("Checking FOL 378...")
res_378, err_378 = validate_sample_fol(fol_378)
print(f"Result: {res_378}, Error: {err_378}")

print("\nChecking FOL 382...")
res_382, err_382 = validate_sample_fol(fol_382)
print(f"Result: {res_382}, Error: {err_382}")
