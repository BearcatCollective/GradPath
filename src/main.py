import re
import time
import json

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NavigationError(Exception):
    pass


def log(message):
    with open("log.txt", "a", encoding="utf-8") as file:
        file.write(message.rstrip() + "\n")


class WebScraper:
    def __init__(self, url):
        self.url = url
        self.session = None
        self.response = None
        self.payload = None
        self.class_info = []

        self.current_location = {
            "page": "initial",
            "letter": None,
            "department": None,
            "course": None,
            "campus": None,
            "semester": None
        }

        self.initializeSession()

    def initializeSession(self):
        if self.session is not None:
            self.session.close()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/123 Safari/537.36"
            ),
            "Accept": "*/*",
        })
        self.response = self.session.get(self.url, verify=False, timeout=15)
        self.response.raise_for_status()

        soup = BeautifulSoup(self.response.text, "html.parser")

        payload = {
            inp["name"]: inp.get("value", "")
            for inp in soup.select("form[name='win0'] input[type='hidden'][name]")
        }
        payload.update({
            "ICAJAX": "1",
            "ICNAVTYPEDROPDOWN": "0",
            "ICBcDomData": "UnknownValue",
        })
        self.payload = payload

    def post(self, action, expected):
        match = re.search(
            r"ICStateNum\.value\s*=\s*(\d+)",  # Response contains updated state number
            self.response.text
        )
        if match:
            self.payload["ICStateNum"] = match.group(1)
        self.payload["ICAction"] = action

        try:
            time.sleep(1)
            response = self.session.post(self.url, data=self.payload, verify=False, timeout=15)
            if "cmd=login" in response.url and "errorCode=129" in response.url:
                raise NavigationError(
                    f"Redirected to login with errorCode=129 during action {action}"
                )

            response.raise_for_status()

            expected_values = (expected,) if isinstance(expected, str) else expected

            if not any(value in response.text for value in expected_values):
                with open("failed_response.html", "w", encoding="utf-8") as file:
                    file.write(response.text)

                raise NavigationError(
                    f"Expected one of {expected_values!r}, but none was found. "
                    f"Response URL: {response.url}"
                )

            self.response = response
        except (requests.RequestException, NavigationError) as error:
            log(
                "-----------------------------------------------------\n\n"
                f"Action {action} did not reach expected response: \n"
                f"{error}\n"
                f"Current location: {self.current_location}\n\n"
                "-----------------------------------------------------\n"
            )
            raise

    def restore_session(self, saved_location):
        self.initializeSession()

        if saved_location['page'] == "initial":
            return

        self.post(
            f"DERIVED_SSS_BCC_SSR_ALPHANUM_{saved_location['letter']}",
            expected=f"class='PSPAGE' >{saved_location['letter']}"
        )
        if saved_location['page'] == "catalog":
            return

        self.post(
            f"DERIVED_SSS_BCC_SSR_EXPAND_COLLAPS${saved_location['department']}",
            expected=f"CRSE_NBR"
        )
        if saved_location['page'] == "department":
            return

        self.post(
            f"CRSE_NBR${saved_location['course']}",
            expected=("DERIVED_CRSECAT_DESCR200", "CRSE_OFFERING")
        )
        if saved_location['page'] == "campus_selection":
            return

        if saved_location['campus'] is not None:
            self.post(
                f"CAREER${saved_location['campus']}",
                expected="DERIVED_CRSECAT_DESCR200"
            )
        if saved_location['page'] == "course":
            return

        self.post(
            "DERIVED_SAA_CRS_SSR_PB_GO",
            expected="id='DERIVED_SAA_CRS_TERM_ALT'"
        )
        if saved_location['semester'] is not None:
            self.payload.update({"DERIVED_SAA_CRS_TERM_ALT": saved_location['semester']})
            self.post(
                "DERIVED_SAA_CRS_SSR_PB_GO$3$",
                expected="id='DERIVED_SAA_CRS_TERM_ALT'"
            )

    def retry(self, operation):
        saved_location = self.current_location.copy()

        for attempt in [1, 2, 3, 4]:
            try:
                if attempt > 1:
                    self.restore_session(saved_location)
                    self.current_location = saved_location.copy()

                return operation()

            except (RequestException, NavigationError):
                self.session.close()

                if attempt < 4:
                    time.sleep(attempt * 10)
                else:
                    raise

    def go_to_letter(self, letter):
        self.retry(lambda: self.post(
            f"DERIVED_SSS_BCC_SSR_ALPHANUM_{letter}",
            expected=f"class='PSPAGE' >{letter}"
        ))
        self.current_location.update({
            "page": "catalog",
            "letter": letter,
            "department": None,
            "course": None,
            "campus": None,
            "semester": None
        })

    def go_to_department(self, department):
        self.retry(lambda: self.post(
            f"DERIVED_SSS_BCC_SSR_EXPAND_COLLAPS${department}",
            expected=f"CRSE_NBR"
        ))
        self.current_location.update({
            "page": "department",
            "department": department,
            "course": None,
            "campus": None,
            "semester": None
        })

    def go_to_course(self, course):
        self.retry(lambda: self.post(
            f"CRSE_NBR${course}",
            expected=("DERIVED_CRSECAT_DESCR200", "CRSE_OFFERING")
        ))
        if "DERIVED_CRSECAT_DESCR200" in self.response.text:
            page = "course"
        else:
            page = "campus_selection"

        self.current_location.update({
            "page": page,
            "course": course,
            "campus": None,
            "semester": None
        })

    def go_to_campus(self, campus):
        self.retry(lambda: self.post(
            f"CAREER${campus}",
            expected="DERIVED_CRSECAT_DESCR200"
        ))
        self.current_location.update({
            "page": "course",
            "campus": campus,
            "semester": None
        })

    def go_to_offerings(self):
        self.retry(lambda: self.post(
            "DERIVED_SAA_CRS_SSR_PB_GO",
            expected="id='DERIVED_SAA_CRS_TERM_ALT'"
        ))
        self.current_location.update({
            "page": "offerings",
            "semester": None
        })

    def go_to_semester(self, semester):
        def operation():
            self.payload.update({"DERIVED_SAA_CRS_TERM_ALT": semester})
            self.post(
                "DERIVED_SAA_CRS_SSR_PB_GO$3$",
                expected="DERIVED_SAA_CRS_TERM_ALT"
            )
        self.retry(operation)
        self.current_location.update({
            "semester": semester
        })

    def go_back(self, action, expected, destination):
        self.retry(lambda: self.post(action, expected=expected))
        self.current_location = destination.copy()

        page = self.current_location["page"]

        if page == "catalog":
            self.current_location.update({
                "department": None,
                "course": None,
                "campus": None,
                "semester": None,
            })
        elif page == "department":
            self.current_location.update({
                "course": None,
                "campus": None,
                "semester": None,
            })
        elif page == "campus_selection":
            self.current_location.update({
                "campus": None,
                "semester": None,
            })

    def scrape_course(self):
        title = re.search(r"id='DERIVED_CRSECAT_DESCR200'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
        units = re.search(r"id='DERIVED_CRSECAT_UNITS_RANGE\$0'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
        semesters = re.search(r"id='DERIVED_CRSECAT_SSR_TYP_OFFERED\$0'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
        prerequisites = re.search(r"id='DERIVED_CRSECAT_DESCR254A\$0'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
        description = re.search(r"id='SSR_CRSE_OFF_VW_DESCRLONG[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)

        title = title.group(1) if title else None
        units = units.group(1) if units else None
        semesters = semesters.group(1) if semesters else None
        prerequisites = prerequisites.group(1) if prerequisites else None
        description = description.group(1) if description else None

        title, units, semesters, prerequisites, description = [
            BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
            if value is not None else None
            for value in (title, units, semesters, prerequisites, description)
        ]

        offerings = []
        if not "value='View Class Sections'" in self.response.text:
            return {
                "title": title,
                "description": description,
                "units": units,
                "semesters": semesters,
                "prerequisites": prerequisites,
                "offerings": offerings
            }

        self.go_to_offerings()
        academic_group = re.search(
            r"id='ACAD_GROUP_TBL_DESCR\$0'[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL,
        )
        semester_options = re.findall(
            r'<option value="(\d+)"[^>]*>',
            self.response.text
        )
        for index, semester in enumerate(semester_options):
            if index != 0: # first semester is already loaded
                self.go_to_semester(semester)
            semester_name = re.search(
                rf'<option value="{semester}"[^>]*>(.*?)</option>',
                self.response.text,
                flags=re.DOTALL,
            )
            offering_nbrs = re.findall(
                r"id='MTGPAT_DAYS\$(\d+)'",
                self.response.text,
                flags=re.DOTALL
            )
            for offering_nbr in offering_nbrs:
                days = re.search(rf"id='MTGPAT_DAYS\${offering_nbr}'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
                start = re.search(rf"id='MTGPAT_START\${offering_nbr}'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
                end = re.search(rf"id='MTGPAT_END\${offering_nbr}'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)
                instructor = re.search(rf"id='MTGPAT_INSTR\${offering_nbr}'[^>]*>(.*?)</span>", self.response.text, flags=re.DOTALL)

                if days:
                    offerings.append({
                        "campus": academic_group.group(1) if academic_group else None,
                        "semester": semester_name.group(1) if semester_name else None,
                        "days": days.group(1),
                        "start": start.group(1) if start else None,
                        "end": end.group(1) if end else None,
                        "instructor": instructor.group(1) if instructor else None,
                    })

        for offering in offerings:
            for key, value in offering.items():
                if value is not None:
                    offering[key] = BeautifulSoup(
                        value, "html.parser"
                    ).get_text(" ", strip=True)
        unique_offerings = []
        for offering in offerings:
            if offering not in unique_offerings:
                unique_offerings.append(offering)

        offerings = unique_offerings
        return {
            "title": title,
            "description": description,
            "units": units,
            "semesters": semesters,
            "prerequisites": prerequisites,
            "offerings": offerings
        }

    def get_course_info(self, course):
        department_location = self.current_location.copy()
        self.go_to_course(course)

        course_record = None

        if self.current_location['page'] == 'course':
            course_record = self.scrape_course()
            self.go_back(
                "DERIVED_SAA_CRS_RETURN_PB",
                f"class='PSPAGE' >{self.current_location['letter']}",
                department_location
            )
            return course_record

        campuses = re.findall(
            r"<a name='ACAD_GROUP\$(\d+)'",
            self.response.text,
            flags=re.DOTALL
        )

        campus_location = self.current_location.copy()
        for campus in campuses:
            self.go_to_campus(campus)
            campus_record = self.scrape_course()

            if course_record is None:
                course_record = {
                    "title": campus_record['title'],
                    "description": campus_record['description'],
                    "units": campus_record['units'],
                    "semesters": campus_record['semesters'],
                    "prerequisites": campus_record['prerequisites'],
                    "offerings": []
                }
            course_record['offerings'].extend(campus_record['offerings'])
            self.go_back("DERIVED_SAA_CRS_RETURN_PB", "CRSE_OFFERING", campus_location)
        self.go_back("DERIVED_SSS_SEL_RETURN_PB", f"class='PSPAGE' >{self.current_location['letter']}", department_location)

        return course_record

    def save_record(self, record):
        if record is None or not record.get("title"):
            raise NavigationError("No course title was extracted")
        self.class_info.append(record)
        with open("courses.json", "w", encoding="utf-8") as file:
            json.dump(self.class_info, file, ensure_ascii=False, indent=4)

    def run(self):
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.go_to_letter(letter)
            department_nbrs = re.findall(
                r"<a name='DERIVED_SSS_BCC_GROUP_BOX_1\$147\$\$(\d+)'",
                self.response.text,
                flags=re.DOTALL
            )

            for department in department_nbrs:
                self.go_to_letter(letter)
                self.go_to_department(department)
                course_nbrs = re.findall(
                    r"<a name='CRSE_NBR\$(\d+)'",
                    self.response.text,
                    flags=re.DOTALL
                )

                for course in course_nbrs:
                    record = self.get_course_info(course)
                    self.save_record(record)

if __name__ == "__main__":
    scraper = None
    url = "https://classes.catalyst-services.uc.edu/psc/psclass/EMPLOYEE/SA/c/COMMUNITY_ACCESS.SSS_BROWSE_CATLG.GBL"

    try:
        scraper = WebScraper(url)
        scraper.run()

    except (RequestException, NavigationError) as error:
        log(f"Course scraper failed: {error}; completed records are preserved.")

    finally:
        if scraper is not None:
            scraper.session.close()