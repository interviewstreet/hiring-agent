import requests
import time

lecture_ids = [
963,964,970,973,974,975,977,978,980,983,985,
4693,4699,4704,4706,4709,
4713,4716,4720,
4724,4726,4727,
4728,4729,
4730,4731,
4732,4734,4737,
4740,4742,4745,
4749,4752,4756,4758,
4759,
4763
]

url_template = "https://online.vtu.ac.in/api/v1/student/my-courses/1-understanding-incubation-and-entrepreneurship-prof-b-k-chakravarthy/lectures/{}/progress"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Cookie": "access_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwOi8vb25saW5lLnZ0dS5hYy5pbi9hcGkvdjEvYXV0aC9sb2dpbiIsImlhdCI6MTc3MzQ4MTMwMywiZXhwIjoxNzczNDg0OTAzLCJuYmYiOjE3NzM0ODEzMDMsImp0aSI6IkNMNXh6OEZ0MWtrR25YamQiLCJzdWIiOiI1MTc1MSIsInBydiI6IjIzYmQ1Yzg5NDlmNjAwYWRiMzllNzAxYzQwMDg3MmRiN2E1OTc2ZjcifQ.hpSVqi0UPQslf6xJ5T-XbUPsgniW2kOoNzpPdJkbPJM"
}

body = {
    "current_time_seconds": 502,
    "total_duration_seconds": 1614,
    "seconds_just_watched": 120
}

session = requests.Session()

for lecture_id in lecture_ids:

    url = url_template.format(lecture_id)
    completed = False

    while not completed:

        response = session.post(url, json=body, headers=headers)

        try:
            data = response.json()
        except:
            print("Invalid response:", response.text)
            break

        if "data" not in data:
            print("Unexpected response:", data)
            break

        progress = data["data"]

        if isinstance(progress, list):
            progress = progress[0]

        percent = progress.get("percent", 0)
        completed = progress.get("is_completed", False)

        print(f"Lecture {lecture_id} -- {percent}%")

        if not completed:
            time.sleep(1)

    print(f"Lecture {lecture_id} completed\n")