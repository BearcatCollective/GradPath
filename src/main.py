import json
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebScraper:
    def __init__(self, url):
        self.session = None
        self.url = url
        self.response = None
        self.payload = None
        self.class_info = []
        self.current_state = {'letter': "", 'department': "", 'course': 0, 'location': ""}

    def initializeSession(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/123 Safari/537.36"
            ),
            "Accept": "*/*",
        })
        self.response = self.session.get(self.url, verify=False)
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

    def restore_session(self, error):
        message = str(error) + "\nRestoring session...\n"
        with open("response.txt", "a", encoding="utf-8") as f:
            f.write(message + "Current state: " + str(self.current_state) + "\n")

        self.initializeSession()
        time.sleep(10)

        self.post(f"DERIVED_SSS_BCC_SSR_ALPHANUM_{self.current_state['letter']}")
        if self.current_state['location'] == 'catalog':
            return
        self.post(f"DERIVED_SSS_BCC_SSR_EXPAND_COLLAPS${self.current_state['department']}")
        if self.current_state['location'] == 'department':
            return
        self.post(f"CRSE_NBR${self.current_state['course']}")

    def post(self, state_action):
        try:
            match = re.search(
                r"ICStateNum\.value\s*=\s*(\d+)", # Response contains updated state number
                self.response.text
            )
            if match:
                self.payload["ICStateNum"] = match.group(1)
            self.payload["ICAction"] = state_action

            time.sleep(1)
            response = self.session.post(self.url, data=self.payload, verify=False, timeout=30)

            response.raise_for_status()

            self.response = response
            return True
        except Exception as e:
            return e

    def go_to_letter(self, letter):
        while (error := self.post(f"DERIVED_SSS_BCC_SSR_ALPHANUM_{letter}")) != True:
            self.restore_session(error)

    def go_to_department(self, department):
        while (error := self.post(f"DERIVED_SSS_BCC_SSR_EXPAND_COLLAPS${department}")) != True:
            self.restore_session(error)

    def go_to_course(self, course):
        while (error := self.post(f"CRSE_NBR${course}")) != True:
            self.restore_session(error)

    def go_to_campus(self, campus):
        while (error := self.post(f"CAREER${campus}")) != True:
            self.restore_session(error)

    def go_to_offerings(self):
        while (error := self.post(f"DERIVED_SAA_CRS_SSR_PB_GO")) != True:
            self.restore_session(error)

    def get_offering_info(self):
        offerings = []
        offering_semesters = re.findall(
            r'<option value="(\d+)"[^>]*>(.*?)</option>',
            self.response.text,
            flags=re.DOTALL)

        for semester in offering_semesters:
            semester_id = semester[0]
            semester_name = semester[1]
            self.payload["DERIVED_SAA_CRS_TERM_ALT"] = semester_id
            self.post("DERIVED_SAA_CRS_SSR_PB_GO$3$")

            offering_nbrs = re.findall(r"id='MTGPAT_DAYS\$(\d+)'", self.response.text)
            for offering_nbr in offering_nbrs:
                offering_day = re.search(
                    rf"id='MTGPAT_DAYS\${offering_nbr}'[^>]*>(.*?)</span>",
                    self.response.text,
                    flags=re.DOTALL
                )
                offering_start = re.search(
                    rf"id='MTGPAT_START\${offering_nbr}'[^>]*>(.*?)</span>",
                    self.response.text,
                    flags=re.DOTALL
                )
                offering_end = re.search(
                    rf"id='MTGPAT_END\${offering_nbr}'[^>]*>(.*?)</span>",
                    self.response.text,
                    flags=re.DOTALL
                )
                offerings.append({
                    "semester": semester_name,
                    "day": offering_day.group(1),
                    "start": offering_start.group(1),
                    "end": offering_end.group(1)
                })
        return offerings

    def get_course_info(self, course):
        title_match = re.search(  # get title
            r"id='DERIVED_CRSECAT_DESCR200'[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        description_match = re.search(  # get description
            r"id='SSR_CRSE_OFF_VW_DESCRLONG[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        career_match = re.search( # get college (undergrad, grad)
            r"id='SSR_CRSE_OFF_VW_ACAD_CAREER[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        units_match = re.search( # get credit count in form X.00
            r"id='DERIVED_CRSECAT_UNITS_RANGE[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        semesters_match = re.search( # get semesters typically offered
            r"id='DERIVED_CRSECAT_SSR_TYP_OFFERED[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        prerequisites_match = re.search( # get prerequisite string
            r"id='DERIVED_CRSECAT_DESCR254A[^>]*>(.*?)</span>",
            self.response.text,
            flags=re.DOTALL
        )
        offerings_match = []
        if "DERIVED_SAA_CRS_SSR_PB_GO" in self.response.text:
            self.go_to_offerings()
            offerings_match = self.get_offering_info()

        if not title_match:
            title = "No course title found"
        else:
            title = title_match.group(1)
        if not description_match:
            description = "No course description found"
        else:
            description = description_match.group(1)
        if not career_match:
            career = "No career found"
        else:
            career = career_match.group(1)
        if not units_match:
            units = "No units found"
        else:
            units = units_match.group(1)
        if not semesters_match:
            semester = "Course never offered"
        else:
            semester = semesters_match.group(1)
        if not prerequisites_match:
            prerequisites = "No prerequisites found"
        else:
            prerequisites = prerequisites_match.group(1)
        if not offerings_match:
            offerings = "No offerings found"
        else:
            offerings = offerings_match

        record = {
            "title": title,
            "description": description,
            "career": career,
            "units": units,
            "semester": semester,
            "prerequisites": prerequisites,
            "offerings": offerings,
        }
        self.class_info.append(record)
        with open("courses.json", "w", encoding="utf-8") as f:
            json.dump(self.class_info, f, indent=4, ensure_ascii=False)

        self.post("DERIVED_SAA_CRS_RETURN_PB")  # return to course catalog

def get_all_class_data(scraper):
    scraper.current_state = {
        'letter': 'A',
        'department': '0',
        'course': 0,
        'location': 'catalog',
    }
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        scraper.go_to_letter(letter)
        scraper.current_state['letter'] = letter
        scraper.current_state['location'] = 'catalog'
        department_nbrs = re.findall(
            r"<a name='DERIVED_SSS_BCC_GROUP_BOX_1\$147\$\$(\d+)'",
            scraper.response.text,
            flags=re.DOTALL
        )

        for department_nbr in department_nbrs:
            scraper.go_to_letter(letter)
            scraper.go_to_department(department_nbr)
            scraper.current_state['location'] = 'department'
            scraper.current_state['department'] = department_nbr

            course_number = 0
            while f"<a name='CRSE_NBR${course_number}" in scraper.response.text:
                scraper.go_to_course(course_number)
                scraper.current_state['course'] = course_number
                scraper.current_state['location'] = 'course'

                if 'DERIVED_CRSECAT_DESCR200' not in scraper.response.text:  # not in course info, must be in campus selection
                    campus_selections = re.findall(
                        r"<a name='ACAD_GROUP\$(\d+)'",
                        scraper.response.text,
                        flags=re.DOTALL
                    )
                    for campus in campus_selections:
                        scraper.go_to_campus(campus)
                        scraper.current_state['location'] = 'campus'
                        scraper.get_course_info(course_number)

                    scraper.post("DERIVED_SSS_SEL_RETURN_PB")  # return to catalog
                    scraper.current_state['location'] = 'catalog'
                else: scraper.get_course_info(course_number)

                course_number += 1
                if scraper.url not in scraper.response.url:
                    scraper.restore_session("Mismatched URL found")
                if f"<a name='CRSE_NBR${course_number}" not in scraper.response.text:
                    scraper.go_to_department(department_nbr)


if __name__ == "__main__":
    url = "https://classes.catalyst-services.uc.edu/psc/psclass/EMPLOYEE/SA/c/COMMUNITY_ACCESS.SSS_BROWSE_CATLG.GBL"
    scraper = WebScraper(url)
    scraper.initializeSession()

    get_all_class_data(scraper)