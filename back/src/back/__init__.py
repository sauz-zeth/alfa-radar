def main() -> None:
    import uvicorn

    uvicorn.run("back.main:app", host="0.0.0.0", port=8000)
