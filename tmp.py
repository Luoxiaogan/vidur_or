#!/usr/bin/env python3
"""
SGLang 实验运行脚本

用法:
    python tmp.py /path/to/exp_dir

功能:
    1. 创建 exp_dir/output/ 目录
    2. 复制 04_24.lg.test_3.py 到 exp_dir/run.py
    3. 修改 OUTPUT_DIR 为 exp_dir/output
    4. 运行实验
"""
import sys
import shutil
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python tmp.py /path/to/exp_dir")
        sys.exit(1)

    exp_dir = Path(sys.argv[1]).resolve()
    output_dir = exp_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    src_script = Path("/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/04_24.lg.test_3.py")
    if not src_script.exists():
        print(f"Error: Source script not found: {src_script}")
        sys.exit(1)

    dst_script = exp_dir / "run.py"
    shutil.copy2(src_script, dst_script)

    # 读取并修改 OUTPUT_DIR
    content = dst_script.read_text()

    # 替换 OUTPUT_DIR 行（匹配任意现有路径）
    import re
    content = re.sub(
        r'OUTPUT_DIR = ".*?"',
        f'OUTPUT_DIR = "{output_dir}"',
        content
    )

    # 也替换旧的硬编码路径格式（兼容旧脚本）
    content = content.replace(
        '/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/output',
        str(output_dir)
    )
    content = content.replace(
        '/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg_single_longer/output',
        str(output_dir)
    )

    dst_script.write_text(content)

    print(f"Copied: {src_script} -> {dst_script}")
    print(f"Output dir: {output_dir}")

    # 运行
    print(f"\n{'='*70}")
    print(f"Running experiment in {exp_dir}")
    print(f"{'='*70}\n")

    result = subprocess.run(
        [sys.executable, str(dst_script)],
        cwd=str(exp_dir),
    )

    if result.returncode == 0:
        print(f"\n{'='*70}")
        print(f"Done! Output: {output_dir}")
        print(f"{'='*70}")
    else:
        print(f"\nFailed with code: {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
