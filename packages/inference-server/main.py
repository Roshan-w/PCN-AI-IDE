import subprocess
import sys
import os

# Add inference-server to sys.path to allow imports from config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.server_config import vLLMServerConfig

def main():
    config = vLLMServerConfig()
    model_conf = config.models[config.default_model]

    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_conf.model_id,
        "--quantization", model_conf.quantization.value,
        "--dtype", model_conf.dtype,
        "--max-model-len", str(model_conf.max_model_len),
        "--gpu-memory-utilization", str(model_conf.gpu_memory_utilization),
        "--port", str(config.port)
    ]
    if model_conf.enable_prefix_caching:
        cmd.append("--enable-prefix-caching")

    print(f"Starting vLLM with command: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
