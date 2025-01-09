import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, UploadFile, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse
from starlette.websockets import WebSocket

import app.database as db_handler


# === FASTAPI ===z
@asynccontextmanager
async def lifespan(app: FastAPI):
    # INFO: Needs to set up environment variables before running the app, refer to README.md
    # Get the database connection
    await db_handler.get_database()

    yield


app = FastAPI(lifespan=lifespan)


# Custom exception handler to change {detail} to {message}
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


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
async def root() -> dict[str, str]:
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
            "content": {"application/json": {"example": {"message": "ok", "rows": "0"}}},
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request",
            "content": {"application/json": {"example": {"message": "Validation error"}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal server error",
            "content": {"application/json": {"example": {"message": "Internal server error: <error message>"}}},
        }})
async def import_csv(file: UploadFile) -> dict[str, str]:
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
        return {"message": "ok", "rows": str(rows_imported)}
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
            "content": {"application/json": {"example": {"message": "Internal server error: <error message>"}}},
        }})
async def export_csv() -> StreamingResponse:
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
@app.post(
    "/check-in/{entry_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Check in successful",
            "content": {"application/json": {"example": {"message": "ok", "time": "1970-01-01T12:00:00.000000Z"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Not found",
            "content": {"application/json": {"example": {"message": "ID not found"}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal server error",
            "content": {"application/json": {"example": {"message": "Internal server error: <error message>"}}},
        }})
async def check_in(entry_id: str) -> dict[str, str]:
    """
    Check in the given ID.
    """
    # Check in the student
    try:
        time = await db_handler.check_in(entry_id)
        return {"message": "ok", "time": time}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


# RESET ENDPOINT TODO: Implement reset endpoint, all and by nim
@app.post(
    "/reset/{entry-id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Reset successful",
            "content": {"application/json": {"example": {"message": "ok", "rows": "0"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Not found",
            "content": {"application/json": {"example": {"message": "ID not found"}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal server error",
            "content": {"application/json": {"example": {"message": "Internal server error: <error message>"}}},
        }})
async def reset_check_in(entry_id: str) -> dict[str, str]:
    """
    Reset the check in status of the given ID, or all entries.

    use entry_id = "all" to reset all entries.

    DANGEROUS ENDPOINT: Be careful when using this endpoint, because there is no backup for the data.
    """
    # Reset the database
    try:
        rows = await db_handler.reset_check_in(entry_id)
        return {"message": "ok", "rows": str(rows)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{str(e)}")


# UPDATE WEBSOCKET ENDPOINT (OPTIONAL)
@app.websocket("/update")
async def update_websocket(websocket: WebSocket) -> None:
    """
    Update the client with the latest checked in entry.
    """
    # Accept the websocket connection
    await websocket.accept()

    try:
        # Watch for updates on the check_in field
        await db_handler.watch_entries(websocket)
    except Exception as e:
        # Send the error message to the client
        await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close()
