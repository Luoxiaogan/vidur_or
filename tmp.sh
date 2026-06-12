#!/bin/bash
conda activate sglang_mix
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
cd /root/vidur_or/sglang/python
python -m sglang.launch_server \
    --model-path /root/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --export-batch-metrics-to-file /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_batch/exp_single_batch.csv \
    --export-request-metrics-to-csv /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_req/exp_single_req.csv


python -m sglang.launch_server \
    --model-path /root/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --disaggregation-transfer-backend fake \
    --export-batch-metrics-to-file /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_batch/exp_single_batch.csv \
    --export-request-metrics-to-csv /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_req/exp_single_req.csv


# ============================================
# 安装 Mooncake 编译依赖
# ============================================
apt-get update && apt-get install -y \
    libgflags-dev \
    libgoogle-glog-dev \
    libjsoncpp-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libgrpc++-dev \
    grpc-proto \
    libgtest-dev \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libssl-dev

# 编译 Mooncake
cd /root/Mooncake/build
rm -rf *
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 安装 Python 绑定
cd /root/Mooncake/mooncake-wheel
pip install .

# 验证安装
python -c "from mooncake.engine import TransferEngine; print('Mooncake OK')"


python -m sglang.launch_server \
    --model-path /root/Qwen2.5-1.5B-Instruct \                                                                                                                                                                                       
    --port 30000 \                                                                                                                                                                                                                   
    --disaggregation-mode decode \                                                                                                                                                                                                   
    --disaggregation-decode-enable-fake-auto \                                                                                                                                                                                       
    --disaggregation-transfer-backend fake \                                                                                                                                                                                         
    --export-batch-metrics-to-file /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_batch/exp_single_batch.csv \                                                                                       
    --export-request-metrics-to-csv /root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg/new_results_req/exp_single_req.csv


# ============================================
# 配置 Git Submodule 代理
# ============================================
cd /root/Mooncake
git config submodule.extern/pybind11.url https://ghfast.top/https://github.com/pybind/pybind11.git
git config submodule.extern/yalantinglibs.url https://ghfast.top/https://github.com/alibaba/yalantinglibs.git
git submodule update --init --recursive

# 重新编译
cd /root/Mooncake/build
rm -rf *
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 安装 Python 绑定
cd /root/Mooncake/mooncake-wheel
pip install .

# 验证
python -c "from mooncake.engine import TransferEngine; print('Mooncake OK')"
