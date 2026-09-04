import uvicorn

if __name__ == "__main__":
    uvicorn.run("lisa_api.main:app", host="127.0.0.1", port=8008, reload=True, env_file=".env")