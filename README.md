# FastApi-Guest-Book
This project is a guest book application built using FastAPI and MongoDB. It allows users to check-in, import/export data, and reset check-in status. Additionally, it has a paired client application: [Android-Guest-Book](https://github.com/Reishandy/Android-Guest-Book).

# Features
- Check-in: Users can check-in using their ID.
- Import CSV: Import guest data from a CSV file.
- Export CSV: Export guest data to a CSV file.
- Reset Check-in: Reset the check-in status of a specific ID or all entries.
- WebSocket: Real-time updates for clients using WebSockets.

# Requirements
- Python 3.7+
- FastAPI
- MongoDB
- Motor (async MongoDB driver)
- Python-dotenv

# Installation
1. Clone the repository:
```bash
git clone https://github.com/Reishandy/FastApi-Guest-Book.git
cd FastApi-Guest-Book
```

2. Install dependencies:
```bash
pip install -r requirements.txt
Set up environment variables:
```

3. Create a .env file in the root directory and add the following variables:
```env
MONGODB_USERNAME=<your-mongodb-username>
MONGODB_PASSWORD=<your-mongodb-password>
MONGODB_DATABASE=<your-mongodb-database>
MONGODB_HOST=<your-mongodb-host>
MONGODB_PORT=<your-mongodb-port>
```

# Usage
1. Run the FastAPI application:
```bash
uvicorn app.main:app --reload
```

2. Access the API documentation at http://127.0.0.1:8000/docs.

# Endpoints
## Root Endpoint
- GET /:
  - Description: Test the connection to the API.
  - Response: {"message": "ok"}

## Data Endpoints
- POST /data:
  - Description: Import data from a CSV file.
  - Request: file (UploadFile)
  - Responses:
    - 201: {"message": "ok", "rows": "0"}
    - 400: {"message": "Validation error"}
    - 500: {"message": "Internal server error: <error message>"}

- GET /data:
  - Description: Export data to a CSV file.
  - Response: CSV file with columns: id, name, check_in, checked_in_at

## Check-in Endpoint
- POST /check-in/{entry_id}:
  - Description: Check in the given ID.
  - Responses:
    - 200: {"message": "ok", "time": "1970-01-01T12:00:00.000000Z"}
    - 404: {"message": "ID not found"}
    - 500: {"message": "Internal server error: <error message>"}
  
## Reset Endpoint
- POST /reset/{entry_id}:
  - Description: Reset the check-in status of the given ID, or "all" for all entries.
  - Responses:
    - 200: {"message": "ok", "rows": "0"}
    - 404: {"message": "ID not found"}
    - 500: {"message": "Internal server error: <error message>"}

## WebSocket Endpoint (Optional)
- WS /update:
  - Description: Update the client with the latest checked-in entry.
  - Method: WebSocket

# Paired Client
This FastAPI guest book application is paired with an Android client application, which can be found here: [Android-Guest-Book](https://github.com/Reishandy/Android-Guest-Book).

# Contributing
1. Fork the repository.
2. Create a new branch (git checkout -b feature-branch).
3. Commit your changes (git commit -am 'Add new feature').
4. Push to the branch (git push origin feature-branch).
5. Create a new Pull Request.

# License
This project is licensed under the AGPL-3.0 License. See the [LICENSE](LICENSE) file for details.
