import os
import time

import rook
import schedule
from hermes import job as hermes_job


def setup_rook():
    token = os.environ["ROOK_TOKEN"]
    rook.start(token=token, labels={"env": "dev"})


if __name__ == "__main__":
    setup_rook()

    schedule.every(1).minutes.do(hermes_job)
    while True:
        schedule.run_pending()
        time.sleep(1)
