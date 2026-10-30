"""PyTorch, CUDA ve model paketlerini ağırlık indirmeden doğrula.

Bu betik küçük bir matris çarpımını ekran kartında çalıştırır. Başarılı olması,
modelin doğru tespit yaptığı anlamına gelmez; yalnızca GPU çalışma ortamını sınar.
"""

import importlib
import json
import os
import time
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]

    # Ultralytics kullanıcı ayarını Git'e girmeyen proje veri klasöründe tutar.
    # Burada model oluşturulmadığı için herhangi bir ağırlık dosyası indirilmez.
    config_dir = project_root / "data" / "ultralytics-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))

    try:
        torch = importlib.import_module("torch")
        torchvision = importlib.import_module("torchvision")
        ultralytics = importlib.import_module("ultralytics")
        cv2 = importlib.import_module("cv2")
    except ImportError as exc:
        print(json.dumps({"status": "package_missing", "error": str(exc)}, indent=2))
        return 1

    if not torch.cuda.is_available():
        result = {
            "status": "cuda_unavailable",
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    device_index = 0
    device = torch.device(f"cuda:{device_index}")
    properties = torch.cuda.get_device_properties(device_index)

    # 2048x2048 boyutu 4 GB VRAM'li kart için küçük, fakat GPU hesabını
    # gerçekten çalıştırdığımızı gösterecek kadar anlamlı bir kontroldür.
    left = torch.randn((2048, 2048), device=device)
    right = torch.randn((2048, 2048), device=device)
    torch.cuda.synchronize(device)
    started_at = time.perf_counter()
    product = left @ right
    torch.cuda.synchronize(device)
    elapsed_ms = (time.perf_counter() - started_at) * 1000

    result = {
        "status": "ok",
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "ultralytics": ultralytics.__version__,
        "opencv": cv2.__version__,
        "cuda_runtime": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(device_index),
        "compute_capability": list(torch.cuda.get_device_capability(device_index)),
        "vram_gib": round(properties.total_memory / (1024**3), 2),
        "calculation": {
            "operation": "2048x2048 matrix multiplication",
            "result_device": str(product.device),
            "elapsed_ms": round(elapsed_ms, 2),
        },
        "note": "Bu sonuç model doğruluğu veya gerçek zamanlı FPS ölçümü değildir.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
