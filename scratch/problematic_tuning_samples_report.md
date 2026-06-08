# 🔍 Logic Tuning Dataset Problematic Samples Report

This report lists all **17** problematic samples detected in the model tuning dataset (`logic_merged_valid_augmented.json`) during the Z3 syntactic and semantic validation scan.

## 📊 Summary of Issues

- **Total problematic samples**: 17
- **Primary cause**: Contradictory premises (UNSAT). The premises themselves contain logical contradictions, rendering downstream reasoning trivial or invalid.
- **Impact**: These samples can harm the model's ability to learn valid logical structures and should be repaired or filtered out before fine-tuning.

## ❌ Problematic Samples List

### 1. Sample ID: `17`
- **Dataset Source**: `folio-train`
- **Story ID**: `7`
- **Scan Index**: `439`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Six, seven and eight are real numbers.
- If a real number equals another real number adding one, the first number is larger.
- If the number x is larger than number y, then y is not larger than x.
- Seven equals six plus one.
- Eight equals seven plus one.
- Two is positive.
- If a number is positive, then the double of it is also positive.
- Eight is the double of four.
- Four is the double of two.

#### First-Order Logic (FOL) Formulas
```json
[
  "RealNum(six) AND RealNum(seven) AND RealNum(eight)",
  "ForAll(x, ForAll(y, (RealNum(x) AND RealNum(y) AND EqualAddOne(x, y) -> Larger(x, y))))",
  "ForAll(x, ForAll(y, (Larger(x, y) <-> NOT Larger(y, x))))",
  "EqualAddOne(seven, six)",
  "EqualAddOne(eight, seven)",
  "Positive(two)",
  "ForAll(x, ForAll(y, ((Positive(x) AND EqualDouble(y, x)) -> Positive(y))))",
  "EqualDouble(eight, four)",
  "EqualDouble(four, two)"
]
```
#### Question & Target Answer
- **Question**: Eight is larger than seven.
- **Ground Truth Answer**: `True`

---

### 2. Sample ID: `615`
- **Dataset Source**: `folio-train`
- **Story ID**: `214`
- **Scan Index**: `589`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- If a class has prerequisites the student must take the prerequisites to take the class.
- If a class has no prerequisites, then the student can take the class
- CPSC 201 and CPSC 223 are prerequisites for CPSC 323.
- Intro Microeconomics is the only prerequisite for Intermediate Microeconomics.
- Intro Geology has no prerequisites.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, ForAll(y, ((Prereq(x, y) AND Taken(x)) <-> CanTake(y))))",
  "ForAll(x, ForAll(y, (NOT Prereq(x, y) -> CanTake(y))))",
  "Prereq(cpsc201, cpsc323) AND Prereq(cpsc223, cpsc323)",
  "(Prereq(intromicro, intermediatemicro) AND Taken(intromicro)) -> CanTake(intermediatemicro)",
  "ForAll(x, (NOT Prereq(x, introgeology)))"
]
```
#### Question & Target Answer
- **Question**: CPSC 201 has no prerequisites.
- **Ground Truth Answer**: `Unknown`

---

### 3. Sample ID: `17_aug_var0`
- **Dataset Source**: `folio-train-augmented-letters-var0`
- **Story ID**: `7`
- **Scan Index**: `804`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- K, P and Y are real numbers.
- If a real number equals another real number adding one, the first number is larger.
- If the number x is larger than number y, then y is not larger than x.
- P equals K plus one.
- Y equals P plus one.
- S is positive.
- If a number is positive, then the double of it is also positive.
- Y is the double of H.
- H is the double of S.

#### First-Order Logic (FOL) Formulas
```json
[
  "RealNum(k) AND RealNum(p) AND RealNum(y)",
  "ForAll(x, ForAll(y, (RealNum(x) AND RealNum(y) AND EqualAddOne(x, y) -> Larger(x, y))))",
  "ForAll(x, ForAll(y, (Larger(x, y) <-> NOT Larger(y, x))))",
  "EqualAddOne(p, k)",
  "EqualAddOne(y, p)",
  "Positive(s)",
  "ForAll(x, ForAll(y, ((Positive(x) AND EqualDouble(y, x)) -> Positive(y))))",
  "EqualDouble(y, h)",
  "EqualDouble(h, s)"
]
```
#### Question & Target Answer
- **Question**: Y is larger than P.
- **Ground Truth Answer**: `True`

---

### 4. Sample ID: `615_aug_var0`
- **Dataset Source**: `folio-train-augmented-letters-var0`
- **Story ID**: `214`
- **Scan Index**: `828`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- If a class has prerequisites the student must take the prerequisites to take the class.
- If a class has no prerequisites, then the student can take the class
- D and Y are prerequisites for I.
- Intro Microeconomics is the only prerequisite for Intermediate Microeconomics.
- S has no prerequisites.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, ForAll(y, ((Prereq(x, y) AND Taken(x)) <-> CanTake(y))))",
  "ForAll(x, ForAll(y, (NOT Prereq(x, y) -> CanTake(y))))",
  "Prereq(d, i) AND Prereq(y, i)",
  "(Prereq(intromicro, intermediatemicro) AND Taken(intromicro)) -> CanTake(intermediatemicro)",
  "ForAll(x, (NOT Prereq(x, s)))"
]
```
#### Question & Target Answer
- **Question**: D has no prerequisites.
- **Ground Truth Answer**: `Unknown`

---

### 5. Sample ID: `17_perm_var0`
- **Dataset Source**: `folio-train-augmented-permutation-var0`
- **Story ID**: `7`
- **Scan Index**: `1383`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Seven equals six plus one.
- Eight is the double of four.
- If the number x is larger than number y, then y is not larger than x.
- If a number is positive, then the double of it is also positive.
- Two is positive.
- Six, seven and eight are real numbers.
- If a real number equals another real number adding one, the first number is larger.
- Four is the double of two.
- Eight equals seven plus one.

#### First-Order Logic (FOL) Formulas
```json
[
  "EqualAddOne(seven, six)",
  "EqualDouble(eight, four)",
  "ForAll(x, ForAll(y, (Larger(x, y) <-> NOT Larger(y, x))))",
  "ForAll(x, ForAll(y, ((Positive(x) AND EqualDouble(y, x)) -> Positive(y))))",
  "Positive(two)",
  "RealNum(six) AND RealNum(seven) AND RealNum(eight)",
  "ForAll(x, ForAll(y, (RealNum(x) AND RealNum(y) AND EqualAddOne(x, y) -> Larger(x, y))))",
  "EqualDouble(four, two)",
  "EqualAddOne(eight, seven)"
]
```
#### Question & Target Answer
- **Question**: Eight is larger than seven.
- **Ground Truth Answer**: `True`

---

### 6. Sample ID: `615_perm_var0`
- **Dataset Source**: `folio-train-augmented-permutation-var0`
- **Story ID**: `214`
- **Scan Index**: `1523`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Intro Microeconomics is the only prerequisite for Intermediate Microeconomics.
- CPSC 201 and CPSC 223 are prerequisites for CPSC 323.
- Intro Geology has no prerequisites.
- If a class has no prerequisites, then the student can take the class
- If a class has prerequisites the student must take the prerequisites to take the class.

#### First-Order Logic (FOL) Formulas
```json
[
  "(Prereq(intromicro, intermediatemicro) AND Taken(intromicro)) -> CanTake(intermediatemicro)",
  "Prereq(cpsc201, cpsc323) AND Prereq(cpsc223, cpsc323)",
  "ForAll(x, (NOT Prereq(x, introgeology)))",
  "ForAll(x, ForAll(y, (NOT Prereq(x, y) -> CanTake(y))))",
  "ForAll(x, ForAll(y, ((Prereq(x, y) AND Taken(x)) <-> CanTake(y))))"
]
```
#### Question & Target Answer
- **Question**: CPSC 201 has no prerequisites.
- **Ground Truth Answer**: `Unknown`

---

### 7. Sample ID: `152_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `152`
- **Scan Index**: `1694`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Every student attends the university.
- If a student doesnt pass the project, then they will not pass the university course.
- If a student doesnt complete the quiz, they wont pass the university course.
- If a student takes the test, then they pass the university course.
- Not all students pass the university course.
- If a student attends the review session, then they pass the project.
- Every student attends the review session.
- If a student doesnt complete the quiz, they dont attend the university.
- If a student doesnt attend the university, they dont take the test.
- If a student attends the review session, then they take the test.
- If its true that If a student doesnt pass the project, then they dont pass the university course, then its also true that If a student doesnt complete the quiz, then they dont attend the university.
- If all students pass the university course, then all students attend the university.
- If all students attend the review session, then its true that If a student doesnt complete the quiz, then they dont pass the university course.
- If If a student doesnt pass the project, then they dont pass the university course is true, then at least one student attends the university.
- If the implication If a student doesnt pass the project, then they dont pass the university course implies If a student doesnt complete the quiz, then they dont attend the university, then any student who attends the review session must take the test.
- If a student passes the project, then they also complete the quiz.
- If a student passes the university course, then they attend the university.
- All students pass the project.
- If a student doesnt pass the project, then they didnt attend the review session.
- If a student passes the university course, then they complete the quiz.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, Student(x) -> AttendsUniversity(x))",
  "ForAll(x, NOT PassesProject(x) -> NOT PassesUniversityCourse(x))",
  "ForAll(x, NOT CompletesQuiz(x) -> NOT PassesUniversityCourse(x))",
  "ForAll(x, TakesTest(x) -> PassesUniversityCourse(x))",
  "NOT ForAll(x, Student(x) -> PassesUniversityCourse(x))",
  "ForAll(x, AttendsReviewSession(x) -> PassesProject(x))",
  "ForAll(x, Student(x) -> AttendsReviewSession(x))",
  "ForAll(x, NOT CompletesQuiz(x) -> NOT Student(x))",
  "ForAll(x, NOT AttendsUniversity(x) -> NOT TakesTest(x))",
  "ForAll(x, AttendsReviewSession(x) -> TakesTest(x))",
  "ForAll(x, NOT PassesProject(x) -> NOT PassesUniversityCourse(x)) -> ForAll(x, NOT CompletesQuiz(x) -> NOT Student(x))",
  "ForAll(x, Student(x) -> PassesUniversityCourse(x)) -> ForAll(x, Student(x) -> AttendsUniversity(x))",
  "ForAll(x, Student(x) -> AttendsReviewSession(x)) -> ForAll(x, NOT CompletesQuiz(x) -> NOT PassesUniversityCourse(x))",
  "ForAll(x, NOT PassesProject(x) -> NOT PassesUniversityCourse(x)) -> Exists(x, Student(x))",
  "(ForAll(x, NOT PassesProject(x) -> NOT PassesUniversityCourse(x)) -> ForAll(x, NOT CompletesQuiz(x) -> NOT Student(x))) -> ForAll(x, AttendsReviewSession(x) -> TakesTest(x))",
  "ForAll(x, PassesProject(x) -> CompletesQuiz(x))",
  "ForAll(x, PassesUniversityCourse(x) -> AttendsUniversity(x))",
  "ForAll(x, Student(x) -> PassesProject(x))",
  "ForAll(x, NOT PassesProject(x) -> NOT AttendsReviewSession(x))",
  "ForAll(x, PassesUniversityCourse(x) -> CompletesQuiz(x))"
]
```
#### Question & Target Answer
- **Question**: Do all students take the test?
- **Ground Truth Answer**: `Unknown`

---

### 8. Sample ID: `279_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `279`
- **Scan Index**: `1697`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- There is at least one student enrolled in a specialized computer science course.
- There exists a learner who regularly joins advanced seminars.
- If a learner carries out an independent research project, then that learner receives a key academic distinction.
- Any learner who is not in a specialized computer science course will not conduct an independent research project.
- There is at least one learner who successfully undertakes an independent research project.
- If learners outside specialized computer science courses never conduct an independent research project, then there is someone who has indeed completed such a project.
- If at least one learner regularly joins advanced seminars, then assuming learners who are not in specialized courses do not engage in research projects, there is still someone who completes one.
- If there is a learner in a specialized computer science course, then conducting an independent research project leads to earning an academic distinction.
- Any learner not involved in research collaborations will not engage in an independent research project.
- Whoever participates in research collaborations also joins advanced seminars.

#### First-Order Logic (FOL) Formulas
```json
[
  "Exists(x, (SpecializedCourse(x)))",
  "Exists(x, (AdvancedSeminar(x)))",
  "ForAll(x, (IndependentProject(x) -> AcademicDistinction(x)))",
  "ForAll(x, (NOT SpecializedCourse(x) -> NOT IndependentProject(x)))",
  "Exists(x, (IndependentProject(x)))",
  "((ForAll(x, (NOT SpecializedCourse(x) -> NOT IndependentProject(x))) -> Exists(x, (IndependentProject(x)))))",
  "(Exists(x, (AdvancedSeminar(x)) -> ((ForAll(y, (NOT SpecializedCourse(y) -> NOT IndependentProject(y))) -> Exists(z, (IndependentProject(z)))))))",
  "(NOT (Exists(x, (SpecializedCourse(x)) -> (ForAll(y, (IndependentProject(y) -> AcademicDistinction(y)))))))",
  "ForAll(x, (NOT ResearchCollaboration(x) -> NOT IndependentProject(x)))",
  "ForAll(x, (ResearchCollaboration(x) -> AdvancedSeminar(x)))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises, which statement can be inferred if we know that there is at least one learner who successfully undertakes an independent research project?
A. It is not the case that if there is a specialized computer science learner, then an independent research project leads to an academic distinction.
B. If having a specialized computer science learner implies an independent research project leads to an academic distinction, then having a specialized computer science learner implies an independent research project leads to an academic distinction.
C. If having a specialized computer science learner implies an independent research project leads to an academic distinction, and it is also not the case, then both conditions hold simultaneously.
D. If there is a specialized computer science learner, then an independent research project leads to an academic distinction.
- **Ground Truth Answer**: `False`

---

### 9. Sample ID: `392_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `392`
- **Scan Index**: `1702`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- All students complete the final project.
- If a student has presentation skills, then they receive a certificate.
- All students have presentation skills.
- If a student writes a thesis, then they receive a certificate.
- All students have theoretical knowledge.
- If a student has theoretical knowledge, then they write a thesis.
- Not all students receive a certificate.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, CompletesFinalProject(x))",
  "ForAll(x, HasPresentationSkills(x) -> ReceivesCertificate(x))",
  "ForAll(x, HasPresentationSkills(x))",
  "ForAll(x, WritesThesis(x) -> ReceivesCertificate(x))",
  "ForAll(x, HasTheoreticalKnowledge(x))",
  "ForAll(x, HasTheoreticalKnowledge(x) -> WritesThesis(x))",
  "NOT (ForAll(x, ReceivesCertificate(x)))"
]
```
#### Question & Target Answer
- **Question**: Do all students write a thesis?
- **Ground Truth Answer**: `False`

---

### 10. Sample ID: `267_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `267`
- **Scan Index**: `1714`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- If a student qualifies for a scholarship, then they pass the exam.
- There is at least one student who receives a recommendation letter.
- All students attend tutoring sessions.
- If a student does not receive a recommendation letter, then they do not study regularly.
- If a student attends tutoring sessions, then they receive a recommendation letter.
- If a student does not receive a recommendation letter, then they do not pass the exam.
- If a student does not receive a recommendation letter, then they do not qualify for a scholarship.
- If a student does not receive a recommendation letter, then they do not attend tutoring sessions.
- If a student does not pass the exam, then they do not receive a recommendation letter.
- Not all students receive a recommendation letter.
- There is at least one student who qualifies for a scholarship.
- There is at least one student who studies regularly.
- If not passing the exam implies not receiving a recommendation letter, then not receiving a recommendation letter implies not qualifying for a scholarship.
- If not receiving a recommendation letter implies not attending tutoring sessions, then if a student qualifies for a scholarship, they pass the exam.
- There is at least one student who passes the exam.
- If a student does not attend tutoring sessions, then they do not study regularly.
- There is at least one student who attends tutoring sessions.
- If a student passes the exam, then they receive a recommendation letter.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, (QualifiesScholarship(x) -> PassesExam(x)))",
  "Exists(x, ReceivesRecommendation(x))",
  "ForAll(x, AttendsTutoring(x))",
  "ForAll(x, (NOT ReceivesRecommendation(x) -> NOT StudiesRegularly(x)))",
  "ForAll(x, (AttendsTutoring(x) -> ReceivesRecommendation(x)))",
  "ForAll(x, (NOT ReceivesRecommendation(x) -> NOT PassesExam(x)))",
  "ForAll(x, (NOT ReceivesRecommendation(x) -> NOT QualifiesScholarship(x)))",
  "ForAll(x, (NOT ReceivesRecommendation(x) -> NOT AttendsTutoring(x)))",
  "ForAll(x, (NOT PassesExam(x) -> NOT ReceivesRecommendation(x)))",
  "NOT ForAll(x, ReceivesRecommendation(x))",
  "Exists(x, QualifiesScholarship(x))",
  "Exists(x, StudiesRegularly(x))",
  "ForAll(x, ((NOT PassesExam(x) -> NOT ReceivesRecommendation(x)) -> (NOT ReceivesRecommendation(x) -> NOT QualifiesScholarship(x))))",
  "ForAll(x, ((NOT ReceivesRecommendation(x) -> NOT AttendsTutoring(x)) -> (QualifiesScholarship(x) -> PassesExam(x))))",
  "Exists(x, PassesExam(x))",
  "ForAll(x, (NOT AttendsTutoring(x) -> NOT StudiesRegularly(x)))",
  "Exists(x, AttendsTutoring(x))",
  "ForAll(x, (PassesExam(x) -> ReceivesRecommendation(x)))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises, which statement can be inferred?
A. There exists a student who does not receive a recommendation letter.
B. There exists a student who does not attend tutoring sessions.
C. All students pass the exam.
D. All students do not study regularly.
- **Ground Truth Answer**: `True`

---

### 11. Sample ID: `157_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `157`
- **Scan Index**: `1739`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Every student is required to get a passing grade in the reading section.
- If a student doesnt pass the practice test, then they wont pass the TOEFL exam.
- All students are required to attend the IELTS preparation class.
- If a student studies using the universitys official guide, then they are required to get a passing grade in reading.
- If a student attends the IELTS preparation class, then they will understand the reading material.
- If a student is not required to pass the reading section, then they wont understand the reading material.
- If a student doesnt study using the universitys official guide, then they wont understand the reading material.
- If a student doesnt study using the universitys official guide, then they wont attend the IELTS preparation class.
- If a student attends the IELTS class, then they are required to get a passing grade in reading.
- If a student is not required to get a passing grade in reading, then they wont pass the practice test.
- If a student passes the practice test, then they will pass the TOEFL exam.
- If a student doesnt pass the TOEFL exam, then they wont understand the reading material.
- If attending the IELTS class implies being required to pass reading, then not using the official guide implies not attending the IELTS class.
- If studying using the universitys official guide implies being required to pass reading, then not using the guide implies not understanding the reading material.
- If there is at least one student who studies using the official guide, then if a student doesnt pass the TOEFL exam, they wont understand the reading material.
- If not using the official guide implies not attending the IELTS class, then the existence of a student using the guide implies that not passing the TOEFL exam leads to not understanding the reading material.
- If not passing the TOEFL exam implies not understanding the reading material, then not being required to pass reading implies not passing the practice test.
- If a student doesnt understand the reading material, then they didnt study using the official guide.
- If a student is required to pass reading, then they must attend the IELTS class.
- Not every student passed the TOEFL exam.
- If a student doesnt understand the reading material, then they are not required to pass the reading section.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, RequiredToPassReading(x))",
  "ForAll(x, NOT PassedPracticeTest(x) -> NOT PassedTOEFL(x))",
  "ForAll(x, AttendsIELTSClass(x))",
  "ForAll(x, StudiesFromOfficialGuide(x) -> RequiredToPassReading(x))",
  "ForAll(x, AttendsIELTSClass(x) -> UnderstandsReading(x))",
  "ForAll(x, NOT RequiredToPassReading(x) -> NOT UnderstandsReading(x))",
  "ForAll(x, NOT StudiesFromOfficialGuide(x) -> NOT UnderstandsReading(x))",
  "ForAll(x, NOT StudiesFromOfficialGuide(x) -> NOT AttendsIELTSClass(x))",
  "ForAll(x, AttendsIELTSClass(x) -> RequiredToPassReading(x))",
  "ForAll(x, NOT RequiredToPassReading(x) -> NOT PassedPracticeTest(x))",
  "ForAll(x, PassedPracticeTest(x) -> PassedTOEFL(x))",
  "ForAll(x, NOT PassedTOEFL(x) -> NOT UnderstandsReading(x))",
  "ForAll(x, AttendsIELTSClass(x) -> RequiredToPassReading(x)) -> ForAll(x, NOT StudiesFromOfficialGuide(x) -> NOT AttendsIELTSClass(x))",
  "ForAll(x, StudiesFromOfficialGuide(x) -> RequiredToPassReading(x)) -> ForAll(x, NOT StudiesFromOfficialGuide(x) -> NOT UnderstandsReading(x))",
  "Exists(x, StudiesFromOfficialGuide(x)) -> ForAll(x, NOT PassedTOEFL(x) -> NOT UnderstandsReading(x))",
  "(ForAll(x, NOT StudiesFromOfficialGuide(x) -> NOT AttendsIELTSClass(x))) -> (Exists(x, StudiesFromOfficialGuide(x)) -> ForAll(x, NOT PassedTOEFL(x) -> NOT UnderstandsReading(x)))",
  "ForAll(x, NOT PassedTOEFL(x) -> NOT UnderstandsReading(x)) -> ForAll(x, NOT RequiredToPassReading(x) -> NOT PassedPracticeTest(x))",
  "ForAll(x, NOT UnderstandsReading(x) -> NOT StudiesFromOfficialGuide(x))",
  "ForAll(x, RequiredToPassReading(x) -> AttendsIELTSClass(x))",
  "NOT ForAll(x, PassedTOEFL(x))",
  "ForAll(x, NOT UnderstandsReading(x) -> NOT RequiredToPassReading(x))"
]
```
#### Question & Target Answer
- **Question**: Do all students understand the reading material?
- **Ground Truth Answer**: `Unknown`

---

### 12. Sample ID: `345_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `345`
- **Scan Index**: `1754`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- Submitting course registration (S) grants enrollment confirmation (U).
- Meeting prerequisites (Q) allows enrollment in advanced courses (T).
- Some students have successfully submitted registrations.
- All students have cleared tuition payments (P).
- All students satisfy prerequisite requirements.
- Every registration has advisor approval (R).
- Lack of advisor approval blocks enrollment confirmation.
- Unconfirmed enrollments invalidate registration submissions.
- Full tuition compliance by all students waives prerequisite checks.
- Universal advisor approval triggers automatic purge of unconfirmed registrations.
- All students submitted course registrations.
- Outstanding tuition fees void advisor approvals.
- Enrollment confirmation requires cleared payments.
- Advanced course enrollment mandates advisor consent.
- No students qualify for advanced courses.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, (Submitted(x) -> Confirmed(x)))",
  "ForAll(x, (Qualified(x) -> Advanced(x)))",
  "Exists(x, Submitted(x))",
  "ForAll(x, Paid(x))",
  "ForAll(x, Qualified(x))",
  "ForAll(x, Approved(x))",
  "ForAll(x, (NOT Approved(x) -> NOT Confirmed(x)))",
  "ForAll(x, (NOT Confirmed(x) -> NOT Submitted(x)))",
  "(ForAll(x, Paid(x) -> ForAll(x, Qualified(x))))",
  "(ForAll(x, Approved(x) -> ForAll(x, (NOT Confirmed(x) -> NOT Submitted(x)))))",
  "ForAll(x, Submitted(x))",
  "ForAll(x, (NOT Paid(x) -> NOT Approved(x)))",
  "ForAll(x, (Confirmed(x) -> Paid(x)))",
  "ForAll(x, (Advanced(x) -> Approved(x)))",
  "NOT Exists(x, Qualified(x))"
]
```
#### Question & Target Answer
- **Question**: Based on registration policies, which rule is enforced if we know that every registration has advisor approval?
A. Universal advisor approval → (No enrollment → No registration)
B. Policy contradiction exists
C. Tautological redundancy
D. Logical inconsistency
- **Ground Truth Answer**: `False`

---

### 13. Sample ID: `765_neg_var0`
- **Dataset Source**: `folio-train-augmented-negative-var0`
- **Story ID**: `308`
- **Scan Index**: `1761`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- No video games released by Nintendo support the PS4 platform.
- All video games in the Pokemon series are released by Nintendo.
- All video games in the FIFA series support the PS4 platform.
- All video games supporting users to simulate playing soccer games online are in the FIFA series.
- The video game named “Be Lionel” is in the Pokemon series and supports users to simulate playing football games online.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, (Nintendo(x) -> NOT SupportPS4(x)))",
  "ForAll(x, (Pokemon(x) -> Nintendo(x)))",
  "ForAll(x, (FIFA(x) -> SupportPS4(x)))",
  "ForAll(x, (SoccerOnline(x) -> FIFA(x)))",
  "Pokemon(belionel) AND SoccerOnline(belionel)"
]
```
#### Question & Target Answer
- **Question**: The video game "Be Lionel" is in the pokemon series.
- **Ground Truth Answer**: `False`

---

### 14. Sample ID: `305_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `305`
- **Scan Index**: `1774`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- All books in the library are cataloged.
- There exists at least one book that is cataloged.
- If a book is reserved, then it is not available for borrowing.
- If a book is not returned, then it is not available.
- All users of the library follow the library rules.
- There exists at least one book that is available.
- All books in the reference section cannot be borrowed.
- If all reference books cannot be borrowed, then there exists at least one available book.
- If a book is not reserved, then it is cataloged.
- For all books, if a book is available, then it is not cataloged.
- If a book is not cataloged, then it is not in the reference section.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, Cataloged(x))",
  "Exists(x, Cataloged(x))",
  "ForAll(x, (Reserved(x) -> NOT Borrowable(x)))",
  "ForAll(x, (NOT Returned(x) -> NOT Available(x)))",
  "ForAll(x, FollowsRules(x))",
  "Exists(x, Available(x))",
  "ForAll(x, (ReferenceSection(x) -> NOT Borrowable(x)))",
  "((ForAll(x, (ReferenceSection(x) -> NOT Borrowable(x))) -> Exists(x, Available(x))))",
  "ForAll(x, (NOT Reserved(x) -> Cataloged(x)))",
  "ForAll(x, (Available(x) -> NOT Cataloged(x)))",
  "ForAll(x, (NOT Cataloged(x) -> NOT ReferenceSection(x)))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises, which statement can be inferred?
A. All books are available.
B. There exists a book that is not cataloged.
C. There exists a book that is returned.
D. All books are borrowable.
- **Ground Truth Answer**: `False`

---

### 15. Sample ID: `84_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `84`
- **Scan Index**: `1779`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- If x is a student, then x takes advanced courses.
- If x takes advanced courses, then x wins a scholarship.
- If all students take advanced courses, then everyone takes advanced courses.
- If x wins a scholarship, then x publishes research.
- No one publishes research.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, (Student(x) -> TakesAdvancedCourses(x)))",
  "ForAll(x, (TakesAdvancedCourses(x) -> WinsScholarship(x)))",
  "((Student(x) -> TakesAdvancedCourses(x)) -> ForAll(x, TakesAdvancedCourses(x)))",
  "ForAll(x, (WinsScholarship(x) -> PublishesResearch(x)))",
  "NOT (Exists(x, PublishesResearch(x)))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises, which statement can be inferred?
A. If a student wins a scholarship, then they publish research.
B. If a student publishes research, then they take advanced courses.
C. If a student is not a student, then they do not win scholarship.
D. If someone does not take advanced courses, then they cannot publish research.
- **Ground Truth Answer**: `False`

---

### 16. Sample ID: `351_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `351`
- **Scan Index**: `1784`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- There exists at least one object x that has property R.
- If an object x does not have property U, then it does not have property Q.
- No object x has property P.
- If an object x does not have property Q, then it does not have property S.
- If an object x does not have property R, then it does not have property S.
- If an object x has property T, then it has property P.
- If an object x does not have property T, then it does not have property R.
- There exists at least one object x that has property U.
- If it is true that if an object x does not have property T then it does not have property R, then if an object x has property T, it has property P.
- If there exists at least one object x with property R, then there exists at least one object x with property U.
- If there exists at least one object x with property R, then every object x has property P.
- Every object x has property R.
- If an object x does not have property U, then it does not have property T.
- There exists at least one object x that has property Q.

#### First-Order Logic (FOL) Formulas
```json
[
  "Exists(x, Real(x))",
  "ForAll(x, (NOT Universal(x) -> NOT Qualified(x)))",
  "ForAll(x, NOT Perfect(x))",
  "ForAll(x, (NOT Qualified(x) -> NOT Successful(x)))",
  "ForAll(x, (NOT Real(x) -> NOT Successful(x)))",
  "ForAll(x, (True(x) -> Perfect(x)))",
  "ForAll(x, (NOT True(x) -> NOT Real(x)))",
  "Exists(x, Universal(x))",
  "(ForAll(x, (NOT True(x) -> NOT Real(x)) -> ForAll(x, (True(x) -> Perfect(x)))))",
  "(Exists(x, Real(x)) -> Exists(x, Universal(x)))",
  "(Exists(x, Real(x)) -> ForAll(x, Perfect(x)))",
  "ForAll(x, Real(x))",
  "ForAll(x, (NOT Universal(x) -> NOT True(x)))",
  "Exists(x, Qualified(x))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises provided in the context of a university, which of the following statements can be logically deduced if we know that there exists at least one object x that has property R?
A. If there exists at least one object with property R, then every object has property P.
B. It is not true that if there exists at least one object with property R then every object has property P.
C. It is both true and not true that if there exists at least one object with property R then every object has property P.
D. If it is true that if there exists at least one object with property R then every object has property P, then if there exists at least one object with property R every object has property P.
- **Ground Truth Answer**: `False`

---

### 17. Sample ID: `96_0_neg_var0`
- **Dataset Source**: `logic_based-augmented-negative-var0`
- **Story ID**: `96`
- **Scan Index**: `1788`
- **Split**: `train`
- **Validation Error**: `Contradictory premises: The premises themselves are unsatisfiable (UNSAT).`

#### Natural Language Premises
- All students must complete their coursework.
- If a student is not enrolled in a course, they cannot receive a grade.
- If a student qualifies for an advanced placement class, they must have high academic performance.
- If a student is part of the honor program, then they qualify for an advanced placement class.
- At least one student has completed their coursework.
- At least one student has received a grade.
- If a student has completed their coursework, then they are part of the honor program.
- If a student qualifies for an advanced placement class, then they must have completed their coursework.
- If all students qualifying for advanced placement must have high academic performance, then they must also have completed their coursework.
- If completing coursework ensures that students are part of the honor program, then at least one student must have completed their coursework.
- If all students qualifying for advanced placement must have high academic performance, and that leads to completing coursework, then all students who have completed coursework must be in the honor program.
- If a student qualifies for an advanced placement class, then they will receive a grade.
- If a student has high academic performance, then they will receive a grade.
- No students have high academic performance.

#### First-Order Logic (FOL) Formulas
```json
[
  "ForAll(x, CourseworkCompleted(x))",
  "ForAll(x, (NOT Enrolled(x) -> NOT GradeReceived(x)))",
  "ForAll(x, (AdvancedPlacement(x) -> HighPerformance(x)))",
  "ForAll(x, (HonorProgram(x) -> AdvancedPlacement(x)))",
  "Exists(x, CourseworkCompleted(x))",
  "Exists(x, GradeReceived(x))",
  "ForAll(x, (CourseworkCompleted(x) -> HonorProgram(x)))",
  "ForAll(x, (AdvancedPlacement(x) -> CourseworkCompleted(x)))",
  "ForAll(x, ((AdvancedPlacement(x) -> HighPerformance(x)) -> (AdvancedPlacement(x) -> CourseworkCompleted(x))))",
  "((CourseworkCompleted(x) -> HonorProgram(x)) -> Exists(x, CourseworkCompleted(x)))",
  "ForAll(x, (((AdvancedPlacement(x) -> HighPerformance(x)) -> (AdvancedPlacement(x) -> CourseworkCompleted(x))) -> (CourseworkCompleted(x) -> HonorProgram(x))))",
  "ForAll(x, (AdvancedPlacement(x) -> GradeReceived(x)))",
  "ForAll(x, (HighPerformance(x) -> GradeReceived(x)))",
  "ForAll(x, NOT HighPerformance(x))"
]
```
#### Question & Target Answer
- **Question**: Based on the above premises, which of the following statements can be inferred?
A. If all students qualifying for advanced placement must have high academic performance and if this ensures coursework completion, then students who qualify for advanced placement must have completed their coursework.
B. If all students qualifying for advanced placement must have high academic performance and if this ensures coursework completion, then students who qualify for advanced placement may not have completed their coursework.
C. If all students qualifying for advanced placement must have high academic performance and if this ensures coursework completion, then some students who qualify for advanced placement must have completed their coursework.
D. If all students qualifying for advanced placement must have high academic performance and if this ensures coursework completion, then students who qualify for advanced placement have both completed and not completed their coursework.
- **Ground Truth Answer**: `False`

---

