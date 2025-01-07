from os import getenv
from urllib.parse import quote_plus
from csv import DictReader, writer
from io import StringIO

from bson import InvalidDocument
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from pymongo.errors import OperationFailure, DuplicateKeyError
from dotenv import load_dotenv

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

    TODO: Format of the CSV file: "nim, name, address, phone_number, email, major, study_program, generation, status"

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
    expected_header = ["nim", "name", "address", "phone_number", "email", "major", "study_program", "generation",
                       "status"]
    expected_header_with_check_in = expected_header + ["check_in", "checked_in_at"]
    if csv_reader.fieldnames != expected_header and csv_reader.fieldnames != expected_header_with_check_in:
        raise ValueError("Invalid file format")

    # Fetch existing nims
    try:
        existing_nims = await DB.entry.distinct("nim")
        existing_nims_set = set(existing_nims)
    except (ConnectionError, OperationFailure) as e:
        raise RuntimeError(f"Database query error: {str(e)}")

    # Parse the rows and filter out existing entries
    documents = []
    for row in csv_reader:
        nim = row["nim"].strip()
        if nim in existing_nims_set:
            continue  # Skip if the entry already exists

        documents.append({
            "nim": nim,
            "name": row["name"].strip(),
            "address": row["address"].strip(),
            "phone_number": row["phone_number"].strip(),
            "email": row["email"].strip(),
            "major": row["major"].strip(),
            "study_program": row["study_program"].strip(),
            "generation": row["generation"].strip(),
            "status": row["status"].strip(),
            "check_in": row.get("check_in", "").strip() or False,
            "checked_in_at": row.get("checked_in_at", "").strip() or None
        })

    # Insert the documents into the database
    try:
        if documents:
            result = await DB.entry.insert_many(documents)
            return len(result.inserted_ids)
        return 0
    except (ConnectionError, OperationFailure, DuplicateKeyError, InvalidDocument) as e:
        raise RuntimeError(f"Database insertion error: {str(e)}")


async def export_csv() -> StringIO:
    """
    Export data from the database to a CSV file.

    TODO: Format of the CSV file: "nim, name, address, phone_number, email, major, study_program, generation, status, check_in, checked_in_at"

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
    csv_writer.writerow(["nim", "name", "address", "phone_number", "email", "major", "study_program",
                         "generation", "status", "check_in", "checked_in_at"])

    # Write the entries to the CSV file
    for entry in entries:
        csv_writer.writerow([
            entry.get("nim", ""),
            entry.get("name", ""),
            entry.get("address", ""),
            entry.get("phone_number", ""),
            entry.get("email", ""),
            entry.get("major", ""),
            entry.get("study_program", ""),
            entry.get("generation", ""),
            entry.get("status", ""),
            entry.get("check_in", ""),
            entry.get("checked_in_at", "")
        ])

    output.seek(0) # Move the cursor to the beginning of the file
    return output