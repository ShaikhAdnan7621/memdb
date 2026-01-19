from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def read_root():
    # Print a message to the server console
    print("GET / called — returning greeting")
    # Return JSON to the client
    return JSONResponse(content={"message": "Hello from FastAPI!", "status": "ok"})

if __name__ == "__main__":
    # Optional: allow running directly with python main.py for quick tests
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

