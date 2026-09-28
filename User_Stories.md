# Assignment 4: User Stories and Use Cases- GradPath



## Stakeholder Map

Primary stakeholders: Undergraduate Students, Academic Advisors

Secondary stakeholders: Students changing majors/ transferring in, Co-op advisor,

Hidden stakeholders: Students with accessibility needs, students not using the program



## User stories

US-01 (Undergraduate Student - Primary): As an undergraduate student at the University of Cincinnati, I want to receive a course plan for each semester generated using my degree audit so that I know what courses I have remaining and my expected graduation term

US-02 (Academic Advisor- Primary): As an academic advisor, I want to review and approve a student's proposed degree plan, so that I can ensure the plan follows university policies, and prerequisite rules, without rebuilding the plan manually.

US-03 (Students changing majors – Secondary): As a student changing majors, I want to visualize how changing my major would affect my graduation plan, so that I can understand which completed courses count and what new course requirements I need, and whether the change affects my graduation timeline.

US-04 (Students transferring – Secondary): As a student transferring from another college, I want to be able to visualize my course plan while accounting for transfer credits, so that I have a way to see how my credits apply to my degree requirement and what remains.

US-05 (Students not using the program – Hidden): As a student who is not using GradPath, I want to be able to register for classes relevant to my major without having to compete with a large number of students using GradPath registering for the same classes.



## Use Cases

UC-01: Generate a Semester Plan

Expands: US-01

Primary Actor: Undergraduate Student

Secondary Actors: Academic Advisor


### Preconditions

1. Student has downloaded their degree audit

2. GradPath has updated information containing student’s major and courses

3. GradPath has updated information containing major’s default curriculum plan identifying co-op semesters


### Main Success Flow

1. Student chooses to create a new plan and uploads degree audit

2. System reads the audit and shows the summary for the student to confirm

   - Major

   - Completed courses

   - Remaining courses

   - In progress courses

3. Student confirms summary

4. System asks clarifying questions

   - Target grad date

   - Max credit hours per semester

   - Include summer if no coop

5. Student responds to questions

6. System pulls prerequisites and term offerings from catalog data and assigns courses to semesters using predefined rules

7. System displays plan semester by semester along with flagged issues

8. Student makes any changes they want

9. Student saves the plan


### Alternate Flow: Student corrects audit summary

3a. Student marks item in summary as wrong and adds the correct info

3b. System records and marks it as student edited for advisor to identify student changes

3c. Resume at step 4


### Exception Flow: Uploaded File not readable

2a. System unable to match the file uploaded to the required audit file and rejects it.  

2b. System informs user how and where to download the audit file

2c. Resume at step 1


### Post Conditions:

- Plan is only visible to student unless shared with advisor

- Audit upload is not saved

- Every remaining course is either in a future semester or flagged



## Given / When / Then Acceptance Criteria

- **AC-01.1**:
  - Given the student has a valid degree audit and GradPath has updated information for the student’s major, courses, and curriculum plan,

  - When the student uploads the degree audit, confirms the audit summary, answers the required planning questions, and generates a semester plan summary to be confirmed by the student,

  - Then the system displays a semester-by-semester plan in which every remaining course is either assigned to a future semester or flagged as an issue.


- **AC-01.2**:

  - Given the student is creating a new semester plan,
  
  - When the student uploads a file that the system cannot identify as the required degree audit file,
  
  - Then the system rejects the file, does not generate a semester plan, and provides instructions explaining where and how to download the required degree audit file. 

 

 

 

 