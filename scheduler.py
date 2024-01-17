import time

import schedule
from hermes import job as hermes_job


if __name__ == "__main__":
    schedule.every(1).minutes.do(hermes_job)
    while True:
        schedule.run_pending()
        time.sleep(1)
