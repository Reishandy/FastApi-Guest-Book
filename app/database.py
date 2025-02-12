import json
from csv import DictReader, writer
from datetime import datetime
from zoneinfo import ZoneInfo
from io import StringIO
from os import getenv
from urllib.parse import quote_plus

from bson import InvalidDocument
from dotenv import load_dotenv
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from pymongo.errors import OperationFailure, DuplicateKeyError
from starlette.websockets import WebSocket

# Load the environment variables
load_dotenv()

# Global database variable
DB: AsyncIOMotorDatabase


async def get_database() -> None:
    """
    Get the database connection using the environment variables.

    variables:

    - MONGODB_USERNAME: The username to connect to the MongoDB database.
    - MONGODB_PASSWORD: The password to connect to the MongoDB database.
    - MONGODB_DATABASE: The database name.
    - MONGODB_HOST: The host of the MongoDB database.
    - MONGODB_PORT: The port of the MongoDB database.
    """
    global DB

    # Create connection string from environment variables
    username = quote_plus(getenv("MONGODB_USERNAME"))
    password = quote_plus(getenv("MONGODB_PASSWORD"))
    database = getenv("MONGODB_DATABASE")
    host = getenv("MONGODB_HOST")
    port = int(getenv("MONGODB_PORT"))

    mongodb_url = f"mongodb://{username}:{password}@{host}:{port}/{database}"

    # Connect and return the database
    client = AsyncIOMotorClient(mongodb_url)
    DB = client[database]


async def import_csv(file: UploadFile) -> int:
    """
    Import a CSV file into the database.

    Required CSV columns: "id, name"

    :param file: The CSV file to import.
    :return: The number of rows imported.
    :raises ValueError: If the file format is invalid.
    :raises RuntimeError: If there is an error doing the database operation.
    """
    global DB

    # Read and decode the CSV file
    content = await file.read()
    decoded_content = content.decode("utf-8")

    # Check if the file is empty
    if not decoded_content.strip():
        raise ValueError("Empty file")

    # Use csv module to parse the content
    csv_reader = DictReader(StringIO(decoded_content))
    required_columns = {"id", "name"}
    if not required_columns.issubset(csv_reader.fieldnames):
        raise ValueError("Missing required columns id and/or name")

    # Parse the rows and update or insert entries
    documents = []
    for row in csv_reader:
        documents.append({
            "id": row["id"],
            "name": row["name"],
            "check_in": row.get("check_in", False),
            "checked_in_at": row.get("checked_in_at", None)
            # INFO: Add other fields here if needed
        })

    # Insert or update the documents in the database
    try:
        for doc in documents:
            await DB.entry.update_one({"id": doc["id"]}, {"$set": doc}, upsert=True)
        return len(documents)
    except (ConnectionError, OperationFailure, DuplicateKeyError, InvalidDocument) as e:
        raise RuntimeError(f"Database insertion error: {str(e)}")


async def export_csv() -> StringIO:
    """
    Export data from the database to a CSV file.

    Exported CSV will have the following columns: "id, name, check_in, checked_in_at"

    :return: The CSV file as a StringIO object.
    """
    global DB

    # Fetch data from the database
    try:
        cursor = DB.entry.find({})
        entries = await cursor.to_list(length=None)
    except (ConnectionError, OperationFailure) as e:
        raise RuntimeError(f"Database query error: {str(e)}")

    # Create CSV data
    output = StringIO()
    csv_writer = writer(output)
    csv_writer.writerow(["id", "name", "check_in", "checked_in_at"])

    # Write the entries to the CSV file
    for entry in entries:
        csv_writer.writerow([
            entry.get("id", ""),
            entry.get("name", ""),
            entry.get("check_in", ""),
            entry.get("checked_in_at", "")
        ])

    output.seek(0)  # Move the cursor to the beginning of the file
    return output


async def check_in(entry_id: str) -> str:
    """
    Check in the given ID, and returning the check in time.

    :param entry_id: The ID to check in.
    :return: The check in time.
    :raises ValueError: If the ID is not found.
    :raises RuntimeError: If there is an error doing the database operation.
    """
    global DB

    # Find the entry with the given ID
    try:
        entry = await DB.entry.find_one({"id": entry_id})
    except (ConnectionError, OperationFailure) as e:
        raise RuntimeError(f"Database query error: {str(e)}")

    # Check if the entry exists
    if not entry:
        raise ValueError("ID not found")

    # Check if the entry is already checked in
    if entry.get("check_in", False):
        raise ValueError("Already checked in")

    # Check in the entry
    try:
        time = datetime.now().astimezone(ZoneInfo("Asia/Jakarta")).isoformat()
        await DB.entry.update_one({"id": entry_id}, {"$set": {"check_in": True, "checked_in_at": time}})
        return time
    except (ConnectionError, OperationFailure) as e:
        raise RuntimeError(f"Database update error: {str(e)}")


async def reset_check_in(entry_id: str) -> int:
    """
    Reset the check in status of the given ID, or all entries.

    If entry_id is "all", reset all entries.

    :param entry_id: The ID to reset, or None to reset all entries.
    :return: The number of entries reset.
    :raises ValueError: If the ID is not found.
    :raises RuntimeError: If there is an error doing the database operation.
    """
    global DB

    if entry_id != "all":
        # Find the entry with the given ID
        try:
            entry = await DB.entry.find_one({"id": entry_id})
        except (ConnectionError, OperationFailure) as e:
            raise RuntimeError(f"Database query error: {str(e)}")

        # Check if the entry exists
        if not entry:
            raise ValueError("ID not found")

        # Reset the check in status
        try:
            await DB.entry.update_one({"id": entry_id}, {"$set": {"check_in": False, "checked_in_at": None}})
            return 1
        except (ConnectionError, OperationFailure) as e:
            raise RuntimeError(f"Database update error: {str(e)}")
    else:
        # Reset all entries
        try:
            result = await DB.entry.update_many({}, {"$set": {"check_in": False, "checked_in_at": None}})
            return result.modified_count
        except (ConnectionError, OperationFailure) as e:
            raise RuntimeError(f"Database update error: {str(e)}")


async def watch_entries(websocket: WebSocket):
    """
    Watch for update operations on the check_in field in the entry collection and send updates to the client via WebSocket.

    :param websocket: The WebSocket connection to send updates to.
    """
    global DB

    # Define the pipeline to watch for update or replace operations
    pipeline = [
        {"$match": {"operationType": {"$in": ["update", "replace"]}}}
    ]

    # Watch for changes in the entry collection with mongoDB change streams
    async with DB.entry.watch(pipeline) as stream:
        async for change in stream:
            # Fetch the full document
            document_id = change["documentKey"]["_id"]
            entry = await DB.entry.find_one({"_id": document_id})

            # Send the updated entry to the client
            if entry:
                entry.pop("_id", None)  # Remove the _id field before sending
                await websocket.send_text(json.dumps(entry))
