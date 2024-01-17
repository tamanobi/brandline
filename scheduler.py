import time

import schedule
from hermes import job as hermes_job
import initializer


if __name__ == "__main__":
    initializer.setup_rook()
    initializer.setup_sentry()

    schedule.every(1).minutes.do(hermes_job)
    while True:
        schedule.run_pending()
        time.sleep(1)
