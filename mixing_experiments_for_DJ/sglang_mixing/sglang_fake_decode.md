# SGLang Fake Decode 模式使用指南

本文档记录如何使用 SGLang 的 fake decode 模式进行 PD (Prefill-Decode) 分离测试。

## 1. 环境配置

### 1.1 创建 Conda 环境并安装 SGLang

```bash
conda create -n sglang_mix python=3.10 -y
conda activate sglang_mix
pip install "sglang[all]>=0.4.7"
```

### 1.2 安装 RDMA 依赖（关键步骤）

SGLang 的 PD 分离模式默认使用 Mooncake 传输后端，需要 RDMA 库。即使没有真实 RDMA 硬件，也需要安装库文件才能初始化。

```bash
# 在 conda 环境中安装 rdma-core（包含 libibverbs）
conda install -c conda-forge rdma-core -y
```

验证安装：
```bash
ls $CONDA_PREFIX/lib/libibverbs*
# 应该看到 libibverbs.so, libibverbs.so.1 等文件
```

### 1.3 设置环境变量

启动服务前必须设置：
```bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

## 2. 启动 SGLang Server

### 2.1 启动命令

```bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

python -m sglang.launch_server \
    --model-path /data/pretrained_models/Qwen2.5-1.5B-Instruct \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --port 30000
```

**参数说明**：
- `--disaggregation-mode decode`: 启动为 decode 节点
- `--disaggregation-decode-enable-fake-auto`: 启用 fake 模式，无需真实 prefill 节点
- **不要**指定 `--disaggregation-transfer-backend fake`，使用默认的 mooncake

### 2.2 启动成功标志

看到以下日志表示成功：
```
No RDMA devices found, check your device installation  # 正常，会fallback到TCP
TcpTransport: listen on port 15910
The server is fired up and ready to roll!
```

## 3. 测试请求

### 3.1 基本 curl 测试

```bash
curl http://localhost:30000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "sampling_params": {"max_new_tokens": 10, "ignore_eos": true},
    "bootstrap_host": "2.2.2.2",
    "bootstrap_room": 0
  }'
```

**关键参数**：
- `bootstrap_host: "2.2.2.2"`: FAKE_BOOTSTRAP_HOST，表示使用 fake 模式
- `bootstrap_room: 0`: 必须指定
- `ignore_eos: true`: 强制生成精确数量的 tokens
- `max_new_tokens`: 控制 decode 长度

### 3.2 Python 测试脚本

```python
import requests
from transformers import AutoTokenizer

SGLANG_URL = "http://localhost:30000/generate"
tokenizer = AutoTokenizer.from_pretrained("/data/pretrained_models/Qwen2.5-1.5B-Instruct")

def create_prompt_with_exact_tokens(target_tokens: int) -> str:
    """构造精确 token 数的 prompt"""
    base_text = "hello "
    text = base_text * (target_tokens + 100)
    tokens = tokenizer.encode(text, add_special_tokens=False)[:target_tokens]
    return tokenizer.decode(tokens)

def send_request(prompt: str, max_new_tokens: int) -> dict:
    """发送请求"""
    resp = requests.post(SGLANG_URL, json={
        "text": prompt,
        "sampling_params": {"max_new_tokens": max_new_tokens, "ignore_eos": True},
        "bootstrap_host": "2.2.2.2",
        "bootstrap_room": 0
    })
    return resp.json()

# 测试：精确控制 prefill=2000, decode=11
prompt = create_prompt_with_exact_tokens(2000)
result = send_request(prompt, max_new_tokens=11)
print(f"prompt_tokens: {result['meta_info']['prompt_tokens']}")      # 应该是 2000
print(f"completion_tokens: {result['meta_info']['completion_tokens']}")  # 应该是 11
```

## 4. Fake Decode 模式原理

### 4.1 什么是 Fake Decode

Fake decode 模式模拟 PD 分离架构中的 **decode 节点**行为：

```
真实 PD 分离:
[Prefill节点] --KV cache传输--> [Decode节点] --> 生成tokens

Fake Decode 模式:
[请求] --> [Decode节点] --> 生成tokens
           (跳过prefill计算和KV传输)
```

### 4.2 Fake 模式的行为

| 方面 | 行为 |
|------|------|
| Prefill 计算 | **跳过** |
| KV cache 传输 | **跳过**（FakeKVReceiver 直接返回成功） |
| KV cache 内存 | **分配**（基于 prompt_tokens 数量） |
| Decode 执行 | **真实执行** |
| 输出内容 | 乱码（因为 KV cache 未初始化） |

### 4.3 适用场景

1. **测试 decode 吞吐量**：不依赖 prefill 节点
2. **测试内存压力**：不同 prefill 长度对 KV cache 占用的影响
3. **测试调度行为**：内存不足时的抢占等
4. **压力测试**：控制 batch size 和并发

### 4.4 与 Vidur 模拟器的对比

| 方面 | SGLang Fake Decode | Vidur 模拟器 |
|------|-------------------|--------------|
| Prefill 时间 | 跳过 | 可配置 |
| Decode 时间 | 真实 GPU 执行 | 模拟预测 |
| KV cache 内存 | 真实分配 | 模拟计算 |
| 调度细节 | SGLang 内部调度 | 完全可控 |
| 适用场景 | 验证真实性能 | 研究调度算法 |

## 5. 常见问题

### 5.1 启动报错：`libibverbs.so.1: cannot open shared object file`

**原因**：缺少 RDMA 库

**解决**：
```bash
conda install -c conda-forge rdma-core -y
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

### 5.2 启动报错：`TypeError: 'NoneType' object is not callable`

**原因**：使用了 `--disaggregation-transfer-backend fake`

**解决**：不要指定该参数，使用默认的 mooncake 后端

### 5.3 请求报错：`Disaggregated request received without bootstrap room id`

**原因**：请求中缺少必要参数

**解决**：请求必须包含：
```json
{
  "bootstrap_host": "2.2.2.2",
  "bootstrap_room": 0
}
```

### 5.4 没有 sudo 权限，无法安装系统 RDMA 库

**解决**：使用 conda 安装到用户环境（见 1.2 节）

## 6. 参考资料

- [SGLang PR #14628: Fake Decode 功能](https://github.com/sgl-project/sglang/pull/14628)
- [SGLang PD Disaggregation 文档](https://docs.sglang.ai/advanced_features/pd_disaggregation.html)
- [Mooncake GitHub](https://github.com/kvcache-ai/Mooncake)
