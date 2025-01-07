from contextlib import asynccontextmanager
from pickle import GLOBAL

from fastapi import FastAPI, status, UploadFile, HTTPException
from starlette.responses import StreamingResponse

import database as db_handler


# === FASTAPI ===z
@asynccontextmanager
async def lifespan(app: FastAPI):
    # INFO: Needs to set up environment variables before running the app, refer to README.md
    # Get the database connection
    await db_handler.get_database()

    yield


app = FastAPI(lifespan=lifespan)


# === ENDPOINTS ===
# ROOT ENDPOINT
@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successful response",
            "content": {"application/json": {"example": {"message": "ok"}}},
        }})
async def root():
    """
    Root endpoint, used to test the connection to the API.
    """
    return {"message": "ok"}


# DATA ENDPOINTS
@app.post(
    "/data",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Data created",
            "content": {"application/json": {"example": {"message": "ok", "rows": 0}}},
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request",
            "content": {"application/json": {"example": {"detail": "Validation error"}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal server error",
            "content": {"application/json": {"example": {"detail": "Internal server error: <error message>"}}},
        }})
async def import_csv(file: UploadFile):
    """
    Import data from a CSV file, then store the data in a database.

    TODO: Format of the CSV file: "nim, name, address, phone_number, email, major, study_program, generation, status"
    """
    # Check if the file is a CSV file
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Read the file and store the data in a database
    try:
        rows_imported = await db_handler.import_csv(file)
        return {"message": "ok", "rows": rows_imported}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


@app.get(
    "/data",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Data exported",
            "content": {"text/csv": {
                "example": "nim,name,address,phone_number,email,major,study_program,generation,status,check_in,checked_in_at\n"
                           "12345,John Doe,123 Main St,555-1234,john.doe@example.com,Computer Science,CS,2020,active,True,2023-10-01T12:00:00Z\n"}}
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal server error",
            "content": {"application/json": {"example": {"detail": "Internal server error: <error message>"}}},
        }})
async def export_csv():
    """
    Export data from a database to a CSV file.

    TODO: Format of the CSV file: "nim, name, address, phone_number, email, major, study_program, generation, status"
    """
    # Export the data from the database to a CSV file
    try:
        output = await db_handler.export_csv()
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=data.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


# CHECK-IN ENDPOINT TODO: Implement check-in endpoint
# RESET ENDPOINT TODO: Implement reset endpoint, all and by nim
# UPDATE WEBSOCKET ENDPOINT (OPTIONAL)