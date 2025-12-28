prompt_types = [
{"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 32},
{"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 16},
{"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 8},
{"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 4},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 2},
]
# 这个不行, nested 不如 sarathi

# 分段应该是这样的，rate应该是2的幂
# rate依次递减
# bs=128

prompt_types = [{"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 64},
{"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 32},
{"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 16},
{"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 8},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 4},
]
# 这个不行, nested 不如 sarathi

prompt_types = [{"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 64},
{"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 32},
{"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 8},
{"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 4},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 2},
]
# 这个不行, nested 不如 sarathi

prompt_types = [{"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 32},
{"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 32},
{"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 8},
{"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 4},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 2},
]
# 这个不行, nested 不如 sarathi

[
{"type": "type2", "prefill": 60, "decode": 100, "arrival_rate": 34},
{"type": "type4", "prefill": 60, "decode": 200, "arrival_rate": 15},
{"type": "type6", "prefill": 60, "decode": 300, "arrival_rate": 10},
{"type": "type8", "prefill": 60, "decode": 400, "arrival_rate": 5},
{"type": "type10", "prefill": 60, "decode": 500, "arrival_rate": 2},
]
# 这个不行, nested 不如 sarathi

[
{"type": "type2", "prefill": 60, "decode": 100, "arrival_rate": 34},
{"type": "type4", "prefill": 60, "decode": 200, "arrival_rate": 15},
{"type": "type6", "prefill": 60, "decode": 300, "arrival_rate": 10},
{"type": "type10", "prefill": 60, "decode": 500, "arrival_rate": 7},
]
# 这个不行, nested 不如 sarathi

prompt_types = [{"type": "type1", "prefill": 60, "decode": 300, "arrival_rate":64},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 8}
]
# 这个不行, nested 不如 sarathi

# bs=128



prompt_types = [{"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 320},
{"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 160},
{"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 80},
{"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 40},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 20},
]
#bs=128 不行
# 试一下 bs = 135