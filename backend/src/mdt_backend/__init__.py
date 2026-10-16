def main() -> None:
    import uvicorn

    uvicorn.run("mdt_backend.app:app", reload=True)
