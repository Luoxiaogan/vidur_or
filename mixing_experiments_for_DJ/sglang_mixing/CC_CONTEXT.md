# Claude Code Context - SGLang Mixing 实验

> 新开 CC session 时，使用以下指令获取上下文

## 快速启动指令

```
阅读以下文件获取项目上下文：
1. mixing_experiments_for_DJ/sglang_mixing/STATUS.md - 当前状态和已完成任务
2. mixing_experiments_for_DJ/sglang_mixing/NOTES.md - 技术细节和代码位置
3. /home/lg/.claude/plans/polished-hopping-zebra.md - V3 修改计划（可选）
```

## 项目概述

SGLang Fake Decode 模式下的 batch metrics 记录功能开发，用于 mixing 实验数据收集。

## 关键代码位置

| 文件 | 路径 |
|------|------|
| BatchMetrics 定义 | `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py:59-84` |
| Decode metrics 记录 | `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py:622-647` |
| Queue snapshot | `sglang/python/sglang/srt/disaggregation/decode.py:980-985` |
| Retraction 计数 | `sglang/python/sglang/srt/managers/scheduler.py:2195` |

## 测试命令

```bash
# Server (tmux: sglang_server)
conda activate sglang_mix
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
python -m sglang.launch_server \
    --model-path /data/pretrained_models/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --export-batch-metrics-to-file /home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_batch/batch_metrics.csv

# Test (tmux: sglang_test)
cd /home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing
python test_2.py
```

## Git 信息

- **分支**: `batch-metrics-export`
- **最新 commit**: `7e2e412d4` - V2/V3: Fix batch metrics recording for decode mode
