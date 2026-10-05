"""Run the LurchCal web server on localhost."""
import logging
import uvicorn

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting LurchCal Web Server on http://127.0.0.1:8000")
    uvicorn.run("lurchcal.web_app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()