"""Model indirmeden ve kamera açmadan yerel çalışma ortamını raporlar."""

import importlib.metadata
import json
import platform
import shutil
import subprocess
from pathlib import Path


def collect_environment() -> dict:
    project_root = Path(__file__).resolve().parents[1]
    package_versions = {}
    for package in ("fastapi", "torch", "torchvision", "ultralytics", "opencv-python"):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = None

    # Komut sabittir; kullanıcı girdisi veya shell çalıştırılmaz.
    nvidia_smi = shutil.which("nvidia-smi")
    gpu = {"status": "not_found", "details": None}
    if nvidia_smi:
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            gpu = {
                "status": "detected" if result.returncode == 0 else "command_failed",
                "details": result.stdout.strip() if result.returncode == 0 else None,
            }
        except (OSError, subprocess.TimeoutExpired):
            gpu = {"status": "command_failed", "details": None}

    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "free_disk_gib": round(shutil.disk_usage(project_root).free / (1024**3), 1),
        "packages": package_versions,
        "nvidia": gpu,
        "note": "GPU sürücüsünün görülmesi PyTorch/CUDA veya model doğrulaması değildir.",
    }


if __name__ == "__main__":
    print(json.dumps(collect_environment(), ensure_ascii=False, indent=2))
