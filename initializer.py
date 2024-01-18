import os
import sentry_sdk
import rook


def setup_rook():
    token = os.environ["ROOK_TOKEN"]
    rook.start(token=token, labels={"env": "dev"})


def setup_sentry():
    """Sentry の設定"""
    dsn = os.environ.get("SENTRY_DSN")
    if dsn is None:
        print("dsn が None だったので Sentry の設定をスキップ")
        return
    sentry_sdk.init(
        dsn=dsn,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        enable_tracing=True,
        profiles_sample_rate=1.0,
        environment="production",
    )
