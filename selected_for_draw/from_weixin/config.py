# 虽然是 modifed 更好的情况，但是rate太大了，不太实用

prompt_types1_image1 = [
    {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 2000}, 
    {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 2000}, 
    {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 6000}]

prompt_types2_image2 = [
    {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 2000}, 
    {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000}, 
    {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 2000}]


prompt_types3_image3 = [
    {"type": "type1", "prefill": 20, "decode": 10, "arrival_rate": 2000},
    {"type": "type2", "prefill": 20, "decode": 300, "arrival_rate": 2000},
]

# simulated就可以比较一下不同batch size下，大家的throughput，
# 可以画个折线图，然后取某个固定的batch size画一下throughput关于时间变化的图

# 对短prompt，长prompt两种case都画一画，还可以对不同的比例下也画一画, 那肯定要取爆炸前的数据

