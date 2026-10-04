"""Run the Task Server as a separate local process."""
import uvicorn


def main() -> None:
    uvicorn.run("task_server.app:app", host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()