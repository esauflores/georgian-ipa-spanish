"""FastAPI entry point for the Georgian–Spanish dictionary."""

from fastapi import FastAPI

app = FastAPI(title="Georgian–Spanish IPA Dictionary")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
