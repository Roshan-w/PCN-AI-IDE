# packages/inference-server/config/server_config.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class QuantizationMethod(str, Enum):
    AWQ = "awq"
    GPTQ = "gptq"
    FP16 = "fp16"
    FP8 = "fp8"

@dataclass
class ModelConfig:
    model_id: str
    model_name: str
    quantization: QuantizationMethod
    dtype: str = "half"
    max_model_len: int = 8192
    gpu_memory_utilization: float = 0.9
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    enable_prefix_caching: bool = True
    enable_speculative_decoding: bool = False
    speculative_model: Optional[str] = None
    speculative_num_draft_tokens: int = 5

MODEL_CONFIGS = {
    "llama-3.1-8b-instruct": ModelConfig(
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
        model_name="llama-3.1-8b-instruct",
        quantization=QuantizationMethod.AWQ,
        max_model_len=8192,
        gpu_memory_utilization=0.85,
    ),
    "qwen-2.5-coder-7b-instruct": ModelConfig(
        model_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        model_name="qwen-2.5-coder-7b-instruct",
        quantization=QuantizationMethod.AWQ,
        max_model_len=8192,
        enable_speculative_decoding=True,
        speculative_model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
    ),
    "deepseek-coder-6.7b-instruct": ModelConfig(
        model_id="deepseek-ai/deepseek-coder-6.7b-instruct",
        model_name="deepseek-coder-6.7b-instruct",
        quantization=QuantizationMethod.AWQ,
        max_model_len=8192,
    ),
    "qwen-vl-7b": ModelConfig(
        model_id="Qwen/Qwen-VL-7B-Chat",
        model_name="qwen-vl-7b",
        quantization=QuantizationMethod.AWQ,
        max_model_len=4096,
    ),
}

@dataclass
class vLLMServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    default_model: str = "qwen-2.5-coder-7b-instruct"
    models: Dict[str, ModelConfig] = field(default_factory=lambda: MODEL_CONFIGS)
    max_num_seqs: int = 256
    max_num_batched_tokens: int = 32768
    max_waiting_tokens: int = 20
    log_level: str = "INFO"
    api_key: Optional[str] = None
    enable_metrics: bool = True
    metrics_port: int = 8001
