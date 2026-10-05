"""Run the Task Server as a separate local process."""
import os

import uvicorn


def main() -> None:
    host = os.environ.get("LURCHCAL_TASK_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("LURCHCAL_TASK_SERVER_PORT", "8001"))
    uvicorn.run("task_server.app:app", host=host, port=port)


if __name__ == "__main__":
    main()