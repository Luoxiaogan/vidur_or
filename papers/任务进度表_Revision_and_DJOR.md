## OR Revision 

### 1. 总的内容.

- [ ] 完整列出所有参数设置
  - 这个后面很简单可以写完
- [ ] 考虑真实GPU验证
  - 先做vidur可以做的. 
- [ ] 添加mean latency vs arrival rate图
- [ ] 详细说明baseline配置
- [ ] 解释Figure 7中的"Prompt Number"
- [ ] near boundary (For Nested WAIT)
  - near boundary直接画latency-time curve
  - 横轴是arrival rate, 纵轴是稳态的throughput or latency or memory usage. 这样的一个dependent on arrival rate的一个region.

### 2. mean latency vs arrival rate

- [ ] single type - known
  - [ ] wait & vllm & sarathi
  - [ ] 目前是需要对于wait来说, 找到选定了gpu参数之后(固定了total allocated kv cache, M)的可以反着算回来的admission threshold n.
  - [ ] 然后说明清楚eviction, 会让vllm的stable region变小
  - [ ] 对比就是和合成数据(single)
- [ ] multi type - known
  - [ ] wait & vllm & sarathi
  - [ ] 还是说把对应于GPU的equilibruim找出来.
- [ ] multi typr - unknown
  - [ ] nested wait & vllm & sarathi

### 3. mean latency vs arrival rate

- [ ] near boundary -> 其实就是说, 接近了整个M的满载的时候, vllm会因为eviction炸掉.(如果没有admission control的话)

## DJ-OR

## 1. 目前要做的

- [ ] multi type包含eviction的理论分析
- [ ] 仔细测试s和wait-s是否有用(simulation)
- [ ] 测试eq-S相比vllm的好在哪里
- [ ] mixing
  - [ ] simulation的rate从接近满载到overloaded的变化 (没有满载的时候，admission from queue可能不一定是符合我们的arrival rate的比例, 所以没有match上我们的modeling。)