from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import os
import hashlib
import logging
from PIL import Image
import requests

app = FastAPI()

class ScanRequest(BaseModel):
    path: str

class FileAnalysisResult(BaseModel):
    duplicates: list
    large_files: list
    screenshots: list
    installers: list
    total_size: int

class PlanResponse(BaseModel):
    suggestions: list

class DryRunResponse(BaseModel):
    move_plan: list

def calculate_md5(file_path):
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def scan_directory(path):
    duplicates = []
    large_files = []
    screenshots = []
    installers = []
    total_size = 0
    file_info = []

    for root, _, files in os.walk(path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                file_size = os.path.getsize(file_path)
                total_size += file_size

                if file_size > 100 * 1024 * 1024:
                    large_files.append(file_path)

                _, ext = os.path.splitext(file_name.lower())
                if ext in ['.png', '.jpg', '.jpeg']:
                    try:
                        with Image.open(file_path) as img:
                            if img.size[0] > 1920:
                                screenshots.append(file_path)
                    except Exception:
                        logging.exception(f"Error processing image: {file_path}")

                if ext in ['.exe', '.msi', '.dmg', '.7z', '.zip']:
                    installers.append(file_path)

                file_md5 = calculate_md5(file_path)
                if file_md5:
                    file_info.append((file_path, file_size, file_md5))
            except Exception as e:
                logging.exception(f"Error processing file: {file_path}")

    md5_to_files = {}
    for path, size, md5 in file_info:
        if md5 not in md5_to_files:
            md5_to_files[md5] = []
        md5_to_files[md5].append((path, size))

    for md5, group_files in md5_to_files.items():
        if len(group_files) > 1:
            duplicates.append({"group": md5, "files": [path for path, _ in group_files], "size": group_files[0][1]})

    return {
        "duplicates": duplicates,
        "large_files": large_files,
        "screenshots": screenshots,
        "installers": installers,
        "total_size": total_size
    }

@app.post("/api/scan", response_model=FileAnalysisResult)
async def scan(request: ScanRequest):
    result = scan_directory(request.path)
    return FileAnalysisResult(**result)

def generate_suggestions(scan_result):
    suggestions = []

    # Suggest archiving duplicates
    for duplicate_group in scan_result["duplicates"]:
        if len(duplicate_group["files"]) > 1:
            suggestions.append({
                "category": "Duplicates",
                "action": "archive",
                "reason": duplicate_group["files"][0]
            })

    # Suggest archiving large files
    for large_file in scan_result["large_files"]:
        suggestions.append({
            "category": "Large Files",
            "action": "archive",
            "reason": f"Large file found: {large_file}"
        })

    # Suggest archiving screenshots
    for screenshot in scan_result["screenshots"]:
        suggestions.append({
            "category": "Screenshots",
            "action": "archive",
            "reason": f"Screenshot found: {screenshot}"
        })

    # Suggest archiving installers
    for installer in scan_result["installers"]:
        suggestions.append({
            "category": "Installers",
            "action": "archive",
            "reason": f"Installer found: {installer}"
        })

    return PlanResponse(suggestions=suggestions)

@app.post("/api/plan", response_model=PlanResponse)
async def plan(request: ScanRequest):
    scan_result = scan_directory(request.path)
    return generate_suggestions(scan_result)

def dry_run_plan(plan, base_path):
    move_plan = []
    for suggestion in plan.suggestions:
        if suggestion["action"] == "archive":
            raw = suggestion["reason"]
            source_file = raw.split(": ", 1)[1] if ": " in raw else raw
            source_file = source_file.strip(" []'\"")
            destination_dir = os.path.join(base_path, "__archive__")
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            file_name = os.path.basename(source_file)
            file_extension = os.path.splitext(file_name)[1]
            base_name = os.path.splitext(file_name)[0]
            count = 1
            new_file_name = file_name
            while os.path.exists(os.path.join(destination_dir, new_file_name)):
                new_file_name = f"{base_name}_{count}{file_extension}"
                count += 1
            move_plan.append({"source": source_file, "destination": os.path.join(destination_dir, new_file_name)})

    return DryRunResponse(move_plan=move_plan)

@app.post("/api/dry-run", response_model=DryRunResponse)
async def dry_run(request: ScanRequest):
    scan_result = scan_directory(request.path)
    plan = generate_suggestions(scan_result)
    return dry_run_plan(plan, request.path)


@app.post("/api/apply")
async def apply(request: ScanRequest):
    """按 dry-run 计划归档文件（只移动，不删除）"""
    scan_result = scan_directory(request.path)
    plan = generate_suggestions(scan_result)
    moved = []
    for item in dry_run_plan(plan, request.path).move_plan:
        src, dst = item["source"], item["destination"]
        if not os.path.isfile(src):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.rename(src, dst)
            moved.append({"source": src, "destination": dst})
        except OSError as e:
            print(f"Failed to move {src}: {e}")
    return {"moved": moved, "count": len(moved)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8706)