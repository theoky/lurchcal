"""Run the LurchCal web server on localhost."""
import logging
import os
import uvicorn

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    host = os.environ.get("LURCHCAL_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("LURCHCAL_WEB_PORT", "8000"))
    logger.info("Starting LurchCal Web Server on http://%s:%s", host, port)
    uvicorn.run("lurchcal.web_app:app", host=host, port=port)


if __name__ == "__main__":
    main()