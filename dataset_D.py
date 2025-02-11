from datasets import load_dataset

# 指定下载路径
download_path = "/Users/luogan/Desktop/vidur_or"

# 加载数据集并指定下载路径
try:
    ds = load_dataset("lmsys/lmsys-chat-1m", cache_dir=download_path)
    print("Dataset loaded successfully!")
    print(ds)
except Exception as e:
    print(f"Failed to load dataset: {e}")