# CurseForge Mod Downloader Web Application

A modern web interface for downloading Minecraft mods from CurseForge, built with Flask and Tailwind CSS.

## Features

### Single Mod Download
- Search and download individual mods by name
- Real-time progress tracking
- Automatic version selection (Release > Beta > Alpha)
- Downloaded files saved to `downloads/` folder

### Bulk Download via modlist.html
- Upload your `modlist.html` file containing CurseForge mod links
- Automatic parsing and batch processing
- Comprehensive dashboard with:
  - **Success Count**: Number of successfully downloaded mods
  - **Failure Count**: Number of failed downloads
  - **Manual Fallback**: Clickable links for failed mods
  - **Error Analysis**: Most common error reasons
  - **Storage Used**: Total file size in MB
- Individual failures don't stop the batch process

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser to:
```
http://127.0.0.1:5000
```

## Project Structure

```
mine downloader/
├── app.py                              # Flask backend
├── curseforge_downloader_module.py     # Core download logic
├── index.html                          # Frontend UI
├── requirements.txt                    # Python dependencies
├── uploads/                            # Temporary file storage
└── downloads/                          # Downloaded mods directory
```

## API Endpoints

### POST /api/download/single
Download a single mod by name.
- **Body**: `{"mod_name": "mod name"}`
- **Returns**: `{"job_id": "uuid", "status": "processing"}`

### POST /api/download/bulk
Download mods from uploaded modlist.html file.
- **Body**: Multipart form data with file
- **Returns**: `{"job_id": "uuid", "status": "processing"}`

### GET /api/jobs/<job_id>
Get the status of a download job.
- **Returns**: Job status with progress and results

### GET /api/jobs
List all jobs.

## Configuration

The application is configured to download Minecraft 1.20.1 Forge versions by default. To modify:

1. Edit `curseforge_downloader_module.py`
2. Change the `gameVersion` parameter in `get_mod_files()` function
3. Change the `modLoaderType` parameter (1 = Forge, 2 = Fabric)

## Error Handling

The application includes robust error handling:
- API rate limiting with exponential backoff
- Individual mod failures don't stop batch processing
- Detailed error categorization and analysis
- Manual fallback links for failed downloads

## Development

The Flask server runs in debug mode by default. For production:
- Use a production WSGI server (Gunicorn, uWSGI)
- Implement proper job storage (Redis, database)
- Add authentication and rate limiting
- Configure proper logging