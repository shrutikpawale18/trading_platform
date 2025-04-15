from .app.main import app
# ... existing code ...
# Remove or comment out the old app definition
# app = FastAPI()

# Remove or comment out the old root endpoint if it's defined in main.py too
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}

# You might need to add uvicorn run logic here if it's not handled elsewhere
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 