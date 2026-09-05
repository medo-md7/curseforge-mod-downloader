#!/usr/bin/env python3
"""
Flask backend for CurseForge Mod Downloader web application
"""

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os
import sys
from pathlib import Path
import threading
import uuid
from datetime import datetime
import json
import requests
from curseforge_downloader_module import (
    get_mod_id_from_slug,
    get_mod_details,
    get_mod_versions,
    parse_html_content,
    parse_manifest_json,
    download_mod_by_name,
    process_bulk_download,
    search_mod_by_name,
    download_specific_version,
    CURSEFORGE_API_BASE,
    CURSEFORGE_API_KEY
)

# Add the parent directory to path to import the downloader module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
# Configure CORS to allow requests from Cloudflare Pages and local development
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "https://mod-depot.pages.dev",  # Your Cloudflare Pages domain
            "*"  # Allow all origins during development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
UPLOAD_FOLDER = Path('uploads')
DOWNLOAD_FOLDER = Path('downloads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

# Store job status in memory (in production, use Redis or database)
jobs = {}


@app.route('/')
def serve_frontend():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')


@app.route('/test_api.html')
def serve_test_page():
    """Serve the API test page for debugging"""
    return send_from_directory('.', 'test_api.html')


@app.route('/api/download/single', methods=['POST'])
def download_single_mod():
    """Download a single mod by name with optional version selection"""
    try:
        data = request.json
        mod_name = data.get('mod_name')
        version_id = data.get('version_id')
        download_url = data.get('download_url')
        file_name = data.get('file_name')
        
        if not mod_name:
            return jsonify({'error': 'Mod name is required'}), 400
        
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        jobs[job_id] = {
            'status': 'processing',
            'type': 'single',
            'mod_name': mod_name,
            'version_id': version_id,
            'download_url': download_url,
            'file_name': file_name,
            'progress': 0,
            'result': None,
            'error': None,
            'created_at': datetime.now().isoformat()
        }
        
        # Start download in background thread
        thread = threading.Thread(
            target=run_single_download,
            args=(job_id, mod_name, version_id, download_url, file_name)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'job_id': job_id, 'status': 'processing'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/bulk', methods=['POST'])
def download_bulk_mods():
    """Download mods from uploaded modlist.html file"""
    try:
        print(f"Received bulk download request")
        print(f"Files in request: {list(request.files.keys())}")
        
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        print(f"File received: {file.filename}")
        
        if file.filename == '':
            print("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.html'):
            print(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'File must be an HTML file'}), 400
        
        # Check for manifest version parameter
        manifest_version = request.form.get('manifest_version') if request.form.get('manifest_version') else None
        print(f"Manifest version: {manifest_version}")
        
        # Read file content directly instead of saving
        html_content = file.read().decode('utf-8')
        print(f"HTML content length: {len(html_content)}")
        print(f"HTML content preview: {html_content[:200]}")
        
        # Parse HTML to extract mod links
        mod_links = parse_html_content(html_content)
        print(f"Found {len(mod_links)} mod links: {mod_links}")
        
        if not mod_links:
            return jsonify({'error': 'No mod links found in HTML file. Make sure your HTML file contains links to curseforge.com/minecraft/mc-mods'}), 400
        
        # Return mod information for direct download by frontend
        mod_info = []
        for link in mod_links:
            try:
                mod_slug = link.split('/')[-1]
                mod_id = get_mod_id_from_slug(link)
                
                if mod_id:
                    # Get latest version for the mod
                    versions = get_mod_versions(mod_id, manifest_version, 1)  # Use manifest version if provided
                    if versions:
                        latest_version = versions[0]
                        mod_info.append({
                            'name': mod_slug,
                            'download_url': latest_version.get('downloadUrl'),
                            'file_name': latest_version.get('fileName'),
                            'file_length': latest_version.get('fileLength', 0),
                            'source_url': link,
                            'success': True
                        })
                    else:
                        mod_info.append({
                            'name': mod_slug,
                            'error': 'No versions available',
                            'source_url': link,
                            'success': False
                        })
                else:
                    mod_info.append({
                        'name': mod_slug,
                        'error': 'Could not get mod ID',
                        'source_url': link,
                        'success': False
                    })
            except Exception as e:
                print(f"Error processing mod {link}: {e}")
                mod_info.append({
                    'name': link.split('/')[-1],
                    'error': str(e),
                    'source_url': link,
                    'success': False
                })
        
        return jsonify({
            'total_mods': len(mod_links),
            'mods': mod_info,
            'required_version': manifest_version
        })
        
    except Exception as e:
        print(f"Error in bulk download: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get the status of a download job"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(jobs[job_id])


@app.route('/api/modpack/<mod_id>/manifest', methods=['GET'])
def get_modpack_manifest(mod_id):
    """Get manifest information for a modpack"""
    try:
        # Try to get mod details which might include manifest info
        details = get_mod_details(mod_id)
        if details:
            # For now, return a basic manifest structure
            # In the future, this could be enhanced to extract actual manifest from modpack files
            return jsonify({
                'manifest': {
                    'minecraft': {
                        'version': None,  # Would be extracted from actual manifest
                        'modLoaders': []
                    },
                    'name': details.get('name'),
                    'description': details.get('summary')
                }
            })
        else:
            return jsonify({'error': 'Modpack not found'}), 404
    except Exception as e:
        print(f"Error getting modpack manifest: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/manifest/parse', methods=['POST'])
def parse_manifest():
    """Parse uploaded manifest.json file and extract mod information"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': 'File must be a JSON file'}), 400
        
        manifest_content = file.read().decode('utf-8')
        mod_info = parse_manifest_json(manifest_content)
        
        if mod_info:
            return jsonify({
                'success': True,
                'minecraft_version': mod_info['minecraft_version'],
                'modloader': mod_info['modloader'],
                'mod_count': len(mod_info['mods']),
                'mod_ids': [mod['project_id'] for mod in mod_info['mods']]
            })
        else:
            return jsonify({'error': 'Failed to parse manifest'}), 400
            
    except Exception as e:
        print(f"Error parsing manifest: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    return jsonify(list(jobs.values()))


@app.route('/api/download/direct', methods=['POST'])
def download_direct():
    """Download a file directly without saving to server"""
    try:
        data = request.json
        download_url = data.get('download_url')
        file_name = data.get('file_name')
        
        if not download_url or not file_name:
            return jsonify({'error': 'Download URL and file name are required'}), 400
        
        print(f"Download request: {file_name} from {download_url}")
        
        # Stream the file directly to the client
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                def generate():
                    for chunk in response.iter_content(chunk_size=8192):
                        yield chunk
                
                return Response(
                    generate(),
                    headers={
                        'Content-Disposition': f'attachment; filename="{file_name}"',
                        'Content-Type': 'application/octet-stream'
                    }
                )
            else:
                print(f"Failed to download: HTTP {response.status_code}")
                return jsonify({'error': f'Failed to download file: HTTP {response.status_code}'}), 500
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return jsonify({'error': f'Failed to download file: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Download endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search/modpacks', methods=['GET'])
def search_modpacks():
    """Search for modpacks by name"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        print(f"Modpack search query: '{query}'")
        
        # Modpacks use a different class ID (4471 for Modpacks)
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        search_url = f"{CURSEFORGE_API_BASE}/mods/search"
        params = {
            "gameId": 432,  # Minecraft game ID
            "searchFilter": query,
            "pageSize": 25,
            "sortField": 1,  # Sort by featured
            "sortOrder": "desc",
            "classId": 4471  # Modpacks class ID
        }
        
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                results = data['data']
                print(f"Modpack search results count: {len(results)}")
                if results:
                    print(f"First result: {results[0].get('name')}")
                
                # Format results for frontend
                formatted_results = []
                for mod in results:
                    formatted_results.append({
                        'id': mod.get('id'),
                        'name': mod.get('name'),
                        'slug': mod.get('slug'),
                        'summary': mod.get('summary'),
                        'author': mod.get('author') if isinstance(mod.get('author'), dict) else mod.get('author', ''),
                        'download_count': mod.get('downloadCount'),
                        'categories': [cat.get('name') for cat in mod.get('categories', [])]
                    })
                
                return jsonify({'results': formatted_results})
        
        return jsonify({'results': []})
        
    except Exception as e:
        print(f"Modpack search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/search/mods', methods=['GET'])
def search_mods():
    """Search for mods by name"""
    try:
        query = request.args.get('q', '')
        content_type = request.args.get('type', 'mods')  # mods, shaders, datapacks, resourcepacks
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        print(f"Search query: '{query}', content type: '{content_type}'")
        results = search_mod_by_name(query, content_type)
        print(f"Search results count: {len(results)}")
        if results:
            print(f"First result: {results[0].get('name')}")
        
        # Format results for frontend
        formatted_results = []
        for mod in results:
            formatted_results.append({
                'id': mod.get('id'),
                'name': mod.get('name'),
                'slug': mod.get('slug'),
                'summary': mod.get('summary'),
                'author': mod.get('author') if isinstance(mod.get('author'), dict) else mod.get('author', ''),
                'download_count': mod.get('downloadCount'),
                'categories': [cat.get('name') for cat in mod.get('categories', [])]
            })
        
        return jsonify({'results': formatted_results})
        
    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mod/<mod_id>/files', methods=['GET'])
def get_mod_files(mod_id):
    """Get files for a mod (used for modpack version detection)"""
    try:
        headers = {
            "Accept": "application/json",
            "x-api-key": CURSEFORGE_API_KEY
        }
        
        files_url = f"{CURSEFORGE_API_BASE}/mods/{mod_id}/files"
        params = {
            "gameVersion": None,  # Get all versions
            "pageSize": 1  # Just need the latest file
        }
        
        response = requests.get(files_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return jsonify({'files': data['data']})
        
        return jsonify({'files': []})
        
    except Exception as e:
        print(f"Error getting mod files: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mod/<mod_id>/versions', methods=['GET'])
def get_mod_versions_endpoint(mod_id):
    """Get available versions for a mod"""
    try:
        game_version = request.args.get('game_version', None)  # None = all versions
        mod_loader_type = request.args.get('mod_loader_type', '1')  # 1 = Forge, 2 = Fabric
        
        versions = get_mod_versions(mod_id, game_version, int(mod_loader_type))
        
        # Extract all unique game versions from the files
        all_game_versions = set()
        for file in versions:
            for version in file.get('gameVersions', []):
                all_game_versions.add(version)
        
        # Sort game versions
        sorted_game_versions = sorted(list(all_game_versions), reverse=True)
        
        # Format versions for frontend
        formatted_versions = []
        for file in versions:
            release_type = file.get('releaseType', 1)  # 1 = Release, 2 = Beta, 3 = Alpha
            release_type_names = {1: 'Release', 2: 'Beta', 3: 'Alpha'}
            
            formatted_versions.append({
                'id': file.get('id'),
                'file_name': file.get('fileName'),
                'display_name': file.get('displayName'),
                'file_date': file.get('fileDate'),
                'file_length': file.get('fileLength'),
                'release_type': release_type_names.get(release_type, 'Unknown'),
                'game_versions': file.get('gameVersions', []),
                'download_url': file.get('downloadUrl')
            })
        
        return jsonify({
            'versions': formatted_versions,
            'game_versions': sorted_game_versions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mod/<mod_id>/details', methods=['GET'])
def get_mod_details_endpoint(mod_id):
    """Get detailed information about a mod"""
    try:
        details = get_mod_details(mod_id)
        
        if not details:
            return jsonify({'error': 'Mod not found'}), 404
        
        formatted_details = {
            'id': details.get('id'),
            'name': details.get('name'),
            'slug': details.get('slug'),
            'summary': details.get('summary'),
            'description': details.get('description'),
            'author': details.get('author') if isinstance(details.get('author'), dict) else details.get('author', ''),
            'download_count': details.get('downloadCount'),
            'categories': [cat.get('name') for cat in details.get('categories', [])],
            'latest_files': details.get('latestFiles', [])
        }
        
        return jsonify(formatted_details)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/html-parse', methods=['POST'])
def test_html_parse():
    """Test HTML parsing without API calls"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        html_content = file.read().decode('utf-8')
        
        # Parse HTML to extract mod links
        mod_links = parse_html_content(html_content)
        
        return jsonify({
            'html_length': len(html_content),
            'html_preview': html_content[:500],
            'mod_links_count': len(mod_links),
            'mod_links': mod_links
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview/html', methods=['POST'])
def preview_html_file():
    """Preview the contents of an uploaded HTML file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.html'):
            return jsonify({'error': 'File must be an HTML file'}), 400
        
        # Read file content
        html_content = file.read().decode('utf-8')
        print(f"HTML content length: {len(html_content)}")
        print(f"HTML content preview: {html_content[:200]}")
        
        # Parse HTML to extract mod links
        mod_links = parse_html_content(html_content)
        print(f"Found {len(mod_links)} mod links: {mod_links}")
        
        if not mod_links:
            return jsonify({'error': 'No mod links found in HTML file. Make sure your HTML file contains links to curseforge.com/minecraft/mc-mods'}), 400
        
        # Get details for each mod (limit to first 10 for preview performance)
        preview_mods = []
        for i, link in enumerate(mod_links[:10]):
            try:
                mod_slug = link.split('/')[-1]
                # Try to get mod ID from slug
                mod_id = get_mod_id_from_slug(link)
                if mod_id:
                    details = get_mod_details(mod_id)
                    if details:
                        preview_mods.append({
                            'name': details.get('name'),
                            'slug': details.get('slug'),
                            'summary': details.get('summary'),
                            'download_count': details.get('downloadCount'),
                            'url': link
                        })
                        continue
                
                # Fallback if we can't get details
                preview_mods.append({
                    'name': mod_slug,
                    'slug': mod_slug,
                    'summary': 'Details not available',
                    'download_count': 0,
                    'url': link
                })
            except Exception as e:
                preview_mods.append({
                    'name': link.split('/')[-1],
                    'slug': link.split('/')[-1],
                    'summary': f'Error: {str(e)}',
                    'download_count': 0,
                    'url': link
                })
        
        return jsonify({
            'total_mods': len(mod_links),
            'preview_mods': preview_mods,
            'showing_more': len(mod_links) > 10,
            'additional_count': len(mod_links) - 10
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_single_download(job_id, mod_name, version_id=None, download_url=None, file_name=None):
    """Run single mod download in background"""
    try:
        jobs[job_id]['progress'] = 10
        
        # If version-specific download is requested
        if version_id and download_url and file_name:
            result = download_specific_version(download_url, file_name, DOWNLOAD_FOLDER)
        else:
            # Download the mod by name (auto-select version)
            result = download_mod_by_name(mod_name, DOWNLOAD_FOLDER)
        
        jobs[job_id]['progress'] = 100
        
        if result['success']:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result'] = {
                'success': True,
                'mod_name': mod_name,
                'file_name': result.get('file_name'),
                'file_size_mb': result.get('file_size_mb', 0),
                'download_url': result.get('download_url')
            }
        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = result.get('error', 'Unknown error')
            jobs[job_id]['result'] = {
                'success': False,
                'mod_name': mod_name,
                'error': result.get('error'),
                'manual_url': result.get('manual_url')
            }
            
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


def run_bulk_download(job_id, html_filepath):
    """Run bulk download in background"""
    try:
        jobs[job_id]['progress'] = 5
        
        # Parse HTML file
        with open(html_filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"HTML content length: {len(html_content)}")
        print(f"HTML content preview: {html_content[:200]}")
        
        mod_links = parse_html_content(html_content)
        print(f"Found {len(mod_links)} mod links: {mod_links}")
        
        if not mod_links:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['error'] = 'No mod links found in HTML file. Make sure your HTML file contains links to curseforge.com/minecraft/mc-mods'
            return
        
        jobs[job_id]['total_mods'] = len(mod_links)
        jobs[job_id]['progress'] = 10
        
        # Return mod information for direct download by frontend
        mod_info = []
        for link in mod_links:
            try:
                mod_slug = link.split('/')[-1]
                mod_id = get_mod_id_from_slug(link)
                
                if mod_id:
                    # Get latest version for the mod
                    versions = get_mod_versions(mod_id, manifest_version, 1)  # Use manifest version if provided
                    if versions:
                        latest_version = versions[0]
                        mod_info.append({
                            'name': mod_slug,
                            'download_url': latest_version.get('downloadUrl'),
                            'file_name': latest_version.get('fileName'),
                            'file_length': latest_version.get('fileLength', 0),
                            'source_url': link,
                            'success': True
                        })
                    else:
                        mod_info.append({
                            'name': mod_slug,
                            'error': 'No versions available',
                            'source_url': link,
                            'success': False
                        })
                else:
                    mod_info.append({
                        'name': mod_slug,
                        'error': 'Could not get mod ID',
                        'source_url': link,
                        'success': False
                    })
            except Exception as e:
                mod_info.append({
                    'name': link.split('/')[-1],
                    'error': str(e),
                    'source_url': link,
                    'success': False
                })
        
        jobs[job_id]['progress'] = 100
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['result'] = {
            'total_mods': len(mod_links),
            'mods': mod_info
        }
        
        # Clean up uploaded file
        try:
            os.remove(html_filepath)
        except:
            pass
            
    except Exception as e:
        print(f"Error in run_bulk_download: {e}")
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)