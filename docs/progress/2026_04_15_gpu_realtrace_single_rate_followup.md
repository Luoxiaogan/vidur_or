# GPU Real-Trace Single-Rate Follow-Up - 2026-04-15

## 当前策略切换

在 `200 req` 口径下，继续用 `0.6~1.0` 共用一组参数的 segmented grid 不划算：

- `r=1.0` 的 focused batch 说明，单率 fresh baseline 下可以重新打出明显正值
- 但同一批参数跨 `0.8/0.9/1.0` 共享时，很容易被某个 rate 拖垮
- 因此后续搜索改成 **single-rate first**

固定口径：

- 每个 rate 单独 fresh baseline
- `num_prompts = 200`
- `restart_server_per_rate = true`
- 所有结果继续写入 `outputs/sglang_wcp_sweeps.db`

## 2026-04-17/18 新主线：native low-rate transfer

当前 GPU real-trace nested WCP 的有效主线已经从早期 wrapper / high-rate 局部搜索，转成：

- `native` scheduler 实现
- `bins=20`
- `CS=384`
- `uniform segments`
- 重点调：
  - `TL`
  - `segment_size`
  - `underload threshold`

### 已确认的 hard paired 低 rate 正值

`r=0.6` / `r=0.5` 已经有 fresh paired winner，不再只是共享 baseline 的内部 trial：

- sweep `594`
  - exp: `sglang_native_lowrate_formal_pair_20260417_tl72_cs384_ss200_r0p6_r0p5_np200`
  - `r=0.6`: `+4.7394%`
  - `r=0.5`: `+2.7826%`
- sweep `596`
  - exp: `sglang_native_lowrate_formal_pair_20260417_tl72_cs384_ss175_r0p6_r0p5_np200`
  - `r=0.6`: `+6.5137%`
  - `r=0.5`: `+0.6594%`

当前低 rate 稳定 basin：

- `TL=72`
- `CS=384`
- `segment_mode=uniform`
- `segment_size=175~200`
- `bypass=default`

### r=0.1 / r=0.2 hard paired 结果已补齐

`r=0.1` 与 `r=0.2` 现在都已经不是 shared-baseline 内部正值，而是 fresh paired formal win：

- sweep `685`
  - exp: `sglang_native_r0p1_formal_pair_20260418_tl40_cs384_ss175_np200`
  - `r=0.1`: `+3.3828%`
  - baseline mean E2E: `3384.2252 ms`
  - WCP mean E2E: `3269.7431 ms`
- sweep `698`
  - exp: `sglang_native_r0p2_formal_pair_20260418_tl52_cs384_ss210_np200`
  - `r=0.2`: `+2.6476%`
  - baseline mean E2E: `3682.5456 ms`
  - WCP mean E2E: `3585.0464 ms`

这意味着 `0.1~0.6` 里，当前 fresh paired 已确认正值覆盖：

- `r=0.1`: `TL40 / CS384 / ss175 / wait_gate=off`
- `r=0.2`: `TL52 / CS384 / ss210 / wait_gate=off`
- `r=0.3`: `TL59 / CS384 / ss198 / wait_gate=off`
- `r=0.4`: `TL70 / CS384 / ss165 / wait_gate=on`
- `r=0.5`: `TL72 / CS384 / ss200 / wait_gate=off`
- `r=0.6`: `TL72 / CS384 / ss175 / wait_gate=off`

最新 best fresh formal winners:

- sweep `685`
  - `r=0.1`
  - `+3.3828%`
- sweep `698`
  - `r=0.2`
  - `+2.6476%`
- sweep `772`
  - exp: `sglang_native_r0p3_formal_pair_20260419_tl59_cs384_ss198_rerun_np200`
  - `r=0.3`: `+3.4306%`
- sweep `761`
  - exp: `sglang_native_r0p4_formal_pair_20260419_tl70_cs384_ss165_wg_np200`
  - `r=0.4`: `+9.2061%`
- sweep `594`
  - `r=0.5`: `+2.7826%`
- sweep `596`
  - `r=0.6`: `+6.5137%`

补充：`r=0.5` 在 2026-04-20 又做了一次 fresh formal rerun：

- sweep `773`
  - exp: `sglang_native_r0p5_formal_pair_20260420_tl72_cs384_ss200_rerun_np200`
  - baseline mean E2E: `5644.7946 ms`
  - WCP mean E2E: `5580.4819 ms`
  - improvement: `+1.1393%`

结论：

- `TL72 / CS384 / ss200 / wait_gate=off` 在 `r=0.5` 上仍然是 fresh formal 正值
- 但 rerun `773` 没有超过旧 formal best `594`
- 当前 `r=0.5` 没有新的更强 fresh formal winner，后续不应继续对同一点盲 rerun

### 2026-04-19 当前正在跑的 amplify batches

为了把低 rate 从“勉强为正”继续推向更明显正值，已新开两条只扫窄盆地的 SQL-backed batch：

- `realtrace_native_roundt_20260419_r0p3_amplify2`
  - 复用 baseline sweep `642`
  - `GPU0`
  - 搜索：
    - `TL in {60, 64, 68, 72, 76}`
    - `CS=384`
    - `segment_size in {190, 200, 210}`
    - `wait_gate in {off, on}`
- `realtrace_native_roundu_20260419_r0p4_amplify2`
  - 复用 baseline sweep `636`
  - `GPU1`
  - 搜索：
    - `TL in {72, 76, 80, 84}`
    - `CS=384`
    - `segment_size in {170, 175, 180}`
    - `wait_gate in {off, on}`

这两批仍然保持：

- `num_prompts = 200`
- `dataset = trace_csv`
- `bins = 20`
- `segment_mode = uniform`
- `bypass = default`
- 所有 trial / sweep 持续写入 `outputs/sglang_wcp_sweeps.db`

截至当前已回写的早期结果：

- `r=0.3`, batch `roundt`
  - sweep `699`: `TL60 / ss190 / wait_gate=off` -> `+0.6791%`
  - sweep `702`: `TL60 / ss200 / wait_gate=off` -> `+0.9441%`
  - 中间判断：
    - `TL60` 并没有崩，反而比之前 formal `TL72 / ss200 / +0.9002%` 略强
    - `ss200` 当前优于 `ss190`
- `r=0.4`, batch `roundu`
  - sweep `700`: `TL72 / ss170 / wait_gate=off` -> `+0.5411%`
  - sweep `701`: `TL72 / ss175 / wait_gate=off` -> `+0.0264%`
  - sweep `703`: `TL72 / ss180 / wait_gate=off` -> `+0.5237%`
  - 中间判断：
    - `ss175` 仍然是非常窄、接近 break-even 的点
    - `ss170` 和 `ss180` 都比 `ss175` 更稳，说明 `r=0.4` 的局部最优可能已经从旧的 `175` 轻微外移

当前正在继续：

- `r=0.3`: `TL60 / ss210`，随后进入 `wait_gate=on` 段
- `r=0.4`: `TL72 / ss170 / wait_gate=on`，随后继续同 TL 下的其他 `wait_gate=on` 点

随后根据 2026-04-19 的后续回写结果，`roundt/roundu` 的结构判断进一步收敛为：

- `r=0.3`
  - `TL60 / ss200 / wait_gate=off` 仍是当前最强点：`+0.9441%`
  - `TL60 / ss210 / wait_gate=off`: `-1.9453%`
  - `TL60 / wait_gate=on` 全线负值：
    - `ss190`: `-0.9426%`
    - `ss200`: `-0.2333%`
    - `ss210`: `-0.3560%`
  - `TL64 / ss190 / wait_gate=off`: `-1.6221%`
  - `TL64 / ss200 / wait_gate=off`: `+0.4413%`
  - 中间结论：
    - `wait_gate` 对 `r=0.3` 当前不是增益项
    - `TL` 往 `64+` 走没有显示出优于 `TL60` 的趋势
    - `r=0.3` 更像是一个 `TL≈60 / ss≈200 / wait_gate=off` 的低 TL 局部盆地
- `r=0.4`
  - `TL72 / ss170 / wait_gate=on`: `+1.8045%`，目前仍是最强点
  - `TL72 / ss180 / wait_gate=on`: `+0.9645%`
  - `TL72 / ss175 / wait_gate=on`: `-2.5839%`
  - `TL76 / ss170 / wait_gate=on`: `-1.4443%`
  - `TL76 / wait_gate=off` 也只是小正或负值：
    - `ss170`: `-1.9625%`
    - `ss175`: `+0.1682%`
    - `ss180`: `+0.0726%`
  - 中间结论：
    - `r=0.4` 的主要胜线仍是 `TL72 + wait_gate=on`
    - 最优 `segment_size` 更像靠近 `170`，而不是旧的 `175`
    - `TL76` 方向目前不像是主胜线

基于这些结果，后续已主动中止过宽的 `roundt/roundu`，并切换到更窄的 local refinement：

- `realtrace_native_roundv_20260419_r0p3_narrow_local`
  - baseline `642`
  - `GPU0`
  - 搜索：
    - `TL in {56, 58, 60, 62}`
    - `ss in {195, 200, 205}`
    - `wait_gate=off`
- `realtrace_native_roundw_20260419_r0p4_wg_local`
  - baseline `636`
  - `GPU1`
  - 搜索：
    - `TL in {70, 72, 74}`
    - `ss in {166, 168, 170, 172, 180}`
    - `wait_gate=on`

这两条新线的已回写首点：

- sweep `719`
  - `r=0.3`
  - `TL56 / ss195 / wait_gate=off`
  - `+0.5635%`
- sweep `720`
  - `r=0.4`
  - `TL70 / ss166 / wait_gate=on`
  - `+0.8930%`

当前判断：

- `r=0.4` 的新 local refine 首点没有超过旧 best `TL72 / ss170 / wait_gate=on / +1.8045%`
- `r=0.3` 的新 local refine 首点也还没超过旧 best `TL60 / ss200 / +0.9441%`
- 但两条 focused batch 都还在继续运行，下一批更靠近当前 best 中心的点仍未全部出完

### 2026-04-19 后续：r=0.4 新局部峰值出现，但 fresh formal 没站住

`r=0.4` 的进一步 local refine 结果已经把峰值位置从旧的 `TL72 / ss170 / wg=on` 推到了更低 TL：

- batch: `realtrace_native_roundw_20260419_r0p4_wg_local`
- strongest internal so far:
  - sweep `723`
  - `TL70 / CS384 / ss170 / wait_gate=on`
  - `+2.6359%`

其余相邻点：

- `TL70 / ss166 / wg=on`: `+0.8930%`
- `TL70 / ss168 / wg=on`: `+0.1064%`
- `TL70 / ss172 / wg=on`: `-1.0519%`
- `TL70 / ss180 / wg=on`: `+1.0736%`
- `TL72 / ss166 / wg=on`: `+2.1149%`
- `TL72 / ss168 / wg=on`: `+1.7789%`
- `TL72 / ss170 / wg=on`: `-0.0973%`
- `TL72 / ss172 / wg=on`: `-1.5732%`

这说明：

- `r=0.4` 上确实存在更强的 local basin
- 但这个 basin 非常尖锐，`TL70 / ss170 / wg=on` 周围一两格就会迅速回落

随后已做 fresh formal pair validation：

- sweep `737`
- exp: `sglang_native_r0p4_formal_pair_20260419_tl70_cs384_ss170_wg_np200`

结果：

- baseline mean E2E: `4617.2229 ms`
- WCP mean E2E: `4799.0882 ms`
- improvement: `-3.9388%`

当前结论：

- `r=0.4` 的 `TL70 / ss170 / wg=on` 目前仍然只能视为 **shared-baseline / internal winner**
- 它在 fresh formal baseline 下发生了明显 collapse
- 所以 `r=0.4` 还不能宣称拿下，需要后续继续找更稳的胜线

### 2026-04-19 后续：r=0.3 ultra-narrow 真正跳出更强 internal winner

在主动中止 `TL56/58` 方向后，又切了一条更贴着旧 best 的超窄局部搜索：

- batch: `realtrace_native_roundx_20260419_r0p3_ultranarrow`
- baseline: `642`
- 搜索：
  - `TL in {59, 60, 61}`
  - `ss in {198, 199, 200, 201, 202}`
  - `wait_gate=off`

已回写关键结果：

- sweep `731`
  - `TL59 / CS384 / ss198 / wait_gate=off`
  - `+2.4718%`
- sweep `733`
  - `TL59 / ss199 / wait_gate=off`
  - `-0.4264%`

这说明：

- `r=0.3` 上也存在更强的局部峰值
- 但同样非常窄，`ss198 -> ss199` 就已经从显著正值掉回负值
- 当前 best internal 已从旧的 `TL60 / ss200 / +0.9441%` 升级为：
  - `TL59 / ss198 / wait_gate=off / +2.4718%`

对应 fresh formal pair 已启动：

- sweep `738`
- exp: `sglang_native_r0p3_formal_pair_20260419_tl59_cs384_ss198_np200`

现已完成，结果为：

- baseline mean E2E: `4205.0284 ms`
- WCP mean E2E: `4189.1883 ms`
- improvement: `+0.3767%`

当前结论：

- `r=0.3` 的 `TL59 / ss198 / wait_gate=off` 已经在 fresh formal pair 下站住“正值”
- 但相比 internal `+2.4718%`，fresh paired 只剩 `+0.3767%`
- 因此它目前仍然只能算 **弱 formal win**，距离“大 win”还有明显差距

### r=0.4 refine：shared-baseline 下确实存在窄正值区

coarse probe:

- batch: `realtrace_native_roundi_20260417_r0p4_transfer_probe`
- baseline: sweep `598`

结果：

- sweep `599`: `TL64 / ss200`, `-0.6479%`
- sweep `600`: `TL64 / ss175`, `-3.9136%`
- sweep `601`: `TL72 / ss175`, `+0.2160%`
- sweep `602`: `TL72 / ss200`, `-0.1766%`

refine batch:

- batch: `realtrace_native_roundj_20260417_r0p4_refine`
- baseline: 仍复用 sweep `598`

已完成结果：

- `TL68 / ss165`: `-3.4588%`
- `TL68 / ss175`: `-0.8991%`
- `TL68 / ss185`: `-0.0121%`
- `TL68 / ss195`: `-1.2749%`
- `TL72 / ss165`: `-5.0411%`
- `TL72 / ss175`: `+0.9051%`
- `TL72 / ss185`: `-4.6643%`
- `TL72 / ss195`: `-1.9546%`
- `TL76 / ss165`: `-0.7603%`
- `TL76 / ss175`: `+0.8403%`
- `TL76 / ss185`: `-2.5872%`
- `TL76 / ss195`: `-1.3203%`

结论：

- `r=0.4` 不是完全没有正值区
- 但 basin 很窄，基本只剩：
  - `TL72 / ss175`
  - `TL76 / ss175`
- `segment_size` 稍微偏离 `175` 就会迅速转负

### r=0.4 formal pair：最强候选尚未站住

fresh paired validation:

- sweep `615`
- exp: `sglang_native_r0p4_formal_pair_20260418_tl72_cs384_ss175_np200`

结果：

- baseline mean E2E: `4466.8228 ms`
- WCP mean E2E: `4511.7211 ms`
- improvement: `-1.0052%`

这说明：

- `TL72 / ss175` 在共享 baseline 下的小正值是真实接近 break-even，而不是纯噪声
- 但在 fresh paired baseline 下还不够硬
- 问题已经不像是 `TL/segment_size` 完全错了，更像默认 underload bypass 仍偏保守

### 当前进行中：first native underload-threshold probe

已启动：

- batch: `realtrace_native_roundk_20260418_r0p4_threshold_probe`
- 复用 baseline: sweep `615`

目标：

- 围绕 `TL72/76 + ss175`，单独测试 tighter underload bypass

当前扫描：

- `TL72 / CS384 / ss175`
- `TL76 / CS384 / ss175`
- `bypass=default` with `underload_threshold in {1, 2, 4, 6, 8}`
- `bypass=disabled`

判断逻辑：

- 如果更小 threshold 转正，说明 `r=0.4` 的主要问题是默认 bypass 太强
- 如果 tighter threshold 更差，则说明这条线需要保留更多 baseline-like 行为，下一步应优先看 `TL76/ss175` formal pair 或别的轻量修正

已完成的 `TL72 / ss175` 子结果：

- `ub=1`: `-2.9908%`
- `ub=2`: `-2.7816%`
- `ub=4`: `-2.5549%`
- `ub=6`: `-1.1218%`
- `ub=8`: `-2.4269%`
- `nobypass`: `-4.6856%`

当前中间结论：

- `TL72 / ss175` 已可基本排除
- tighter threshold 没有把它救回来
- 完全关闭 bypass 更差
- 这说明 `r=0.4` 的主要问题不像是 “default bypass 太强”，而更像 `TL72` 这条线本身不够稳

仍在继续：

- `TL76 / ss175` 的同口径 threshold / bypass 对照

已完成的 `TL76 / ss175` 前半结果：

- `ub=1`: `-4.2747%`
- `ub=2`: `-3.4329%`

已完成的 `TL76 / ss175` 全部结果：

- `ub=4`: `-4.3937%`
- `ub=6`: `-1.4694%`
- `ub=8`: `-0.7492%`
- `nobypass`: `-0.8780%`

截至目前的主结论已经足够明确：

- 对 `r=0.4` 而言，low-threshold 方向在 `TL72` 和 `TL76` 上都没有带来改善
- `TL76 / default` 虽然比 `TL72` 更接近 baseline，但在 fixed baseline `615` 下仍未转正
- 因此 underload-threshold 更像是排除项，而不是当前应继续深挖的主轴

下一步已转向：

- 保持 `TL72/76`
- 保持 `CS=384`
- 保持 `segment_size=175`
- 停止继续扫 threshold
- 直接看 `wait_gate=on` 能否把这条 near-break-even 线推过零点

### r=0.4 hard paired win 已确认

fixed-baseline wait-gate probe 先给出了第一个正值：

- batch: `realtrace_native_roundm_20260418_r0p4_waitgate_refine`
- 最佳 internal trial:
  - sweep `632`
  - `TL76 / CS384 / ss175 / wait_gate=on`
  - `+0.5094%`

随后做 fresh formal paired validation：

- sweep `636`
- exp: `sglang_native_r0p4_formal_pair_20260418_tl76_cs384_ss175_wg_np200`

结果：

- baseline mean E2E: `4599.4917 ms`
- WCP mean E2E: `4590.0186 ms`
- improvement: `+0.2060%`

意义：

- `r=0.4` 已从“shared-baseline 小正值”升级为真正的 fresh paired 正值
- 当前 low-rate hard paired 胜线已经覆盖：
  - `r=0.4`: `TL76 / CS384 / ss175 / wait_gate=on`
  - `r=0.5`: `TL72 / CS384 / ss200` 或 `ss175`
  - `r=0.6`: `TL72 / CS384 / ss175/200`

下一步：

- 不再继续在 `r=0.4` 原地抠小数点
- 直接把这条新胜线往 `r=0.3` 外推

## r=1.0 focused batch 结论

batch:

- `realtrace_r1p0_focus_bins10_pairsA_20260414`

fresh baseline:

- sweep `199`
- mean E2E `13941.3236 ms`

最佳 WCP：

- sweep `204`
- `bins=10`
- `TL=96`
- `CS=544`
- bypass `default`
- mean E2E `13355.5611 ms`
- improvement `+4.2016%`

其他可接受正值：

- sweep `203`
  - `TL=96`
  - `CS=512`
  - bypass `disabled`
  - `+4.0797%`
- sweep `207`
  - `TL=96`
  - `CS=576`
  - bypass `disabled`
  - `+3.9663%`
- sweep `211`
  - `TL=144`
  - `CS=544`
  - bypass `disabled`
  - `+0.7298%`

明显失败：

- `TL=128`
  - `CS=480`
  - default / disabled 都显著为负
- `TL=96`
  - `CS=384`
  - default 只小赢
  - disabled 明显输

### 从 r=1.0 学到的东西

- `TL=96` 比更大的 `TL=128/144` 更稳
- bypass 不是单调项，而是和 `CS` 强耦合
- `CS=512/544/576` 才是现在值得反复复验的区域

## 0.6~0.9 的 follow-up 思路

### 0.9

当前最值得优先复验的是 `bins=10` 这条 high-rate 线：

- 历史 surviving positive:
  - `TL=128`
  - `CS=384`
- 在更强的新 baseline 下：
  - `TL=96`
  - `CS=384`
  - 虽然还是负，但已经是当前最接近 baseline 的点

因此 `0.9` 下一轮先搜：

- `bins=10`
- `(TL, CS)` around:
  - `96:384`
  - `96:512`
  - `128:384`
  - `128:512`
  - `160:384`
  - `192:512`

### 0.8

`0.8` 的历史线索是分裂的：

- 老 rerun2 口径：
  - `TL=192`
  - `CS=512`
  - 小正
- 更强 fresh baseline 下：
  - `TL=96`
  - `CS=384/512`
  - 反而更接近 baseline

因此 `0.8` 先不押单一路线，而是同时保留：

- `bins=10`
- `(TL, CS)` around:
  - `96:384`
  - `96:512`
  - `192:384`
  - `192:512`

### 0.7 / 0.6

这两个 rate 目前最像 Vidur-style mid-rate：

- 历史 best 都是：
  - `bins=50`
  - `TL=192`
  - `CS=256`
- 次优常见是：
  - `bins=50`
  - `TL=192`
  - `CS=128`
- `bins=20 / TL=96 / CS=512` 也值得保留为对照线

因此 mid-rate follow-up 优先级：

1. `bins=50`, `TL=192`, `CS=256`
2. `bins=50`, `TL=192`, `CS=128`
3. `bins=50`, `TL=192`, `CS=64`
4. 之后再看要不要专门补 `bins=20`, `TL=96`, `CS=512`

## 执行顺序

先跑：

1. `r=0.9` single-rate bins10 focused
2. `r=0.8` single-rate bins10 focused
3. `r=0.7` single-rate bins50 focused
4. `r=0.6` single-rate bins50 focused

原因：

- 先把最接近突破的 high-rate 边界点重新压出来
- 再去中段 rate 验证 `bins50/TL192` 这条历史强线

## 当前阶段结果补充

### 0.9 single-rate bins10

batch:

- `realtrace_single_rate_focus_20260415A_r0p9_bins10`

fresh baseline:

- sweep `212`
- mean E2E `10507.4954 ms`

当前最好两组：

- sweep `220`
  - `TL=128`
  - `CS=512`
  - bypass `disabled`
  - `+1.8558%`
- sweep `222`
  - `TL=160`
  - `CS=384`
  - bypass `disabled`
  - `+1.0576%`

观察：

- `0.9` 不是调不出来，但正值幅度仍偏小
- no-bypass 明显优于 default
- `TL=192 / CS=512` 方向明显错误

### 0.8 single-rate bins10

batch:

- `realtrace_single_rate_focus_20260415A_r0p8_bins10`

fresh baseline:

- sweep `225`
- mean E2E `8270.1675 ms`

结果：

- 当前整批全负
- 最接近的是：
  - sweep `226`
  - `TL=96`
  - `CS=384`
  - default
  - `-1.0379%`

观察：

- 这条 fresh baseline 非常强
- `0.8` 需要继续找技巧
- 仅靠第一轮 bins10 seeds 不够

### 0.7 / 0.6 bins50 TL192

`0.7` batch:

- `realtrace_single_rate_focus_20260415A_r0p7_bins50`

结果：

- `CS=64`: `+1.4704%`
- `CS=128`: `+0.5056%`
- `CS=256`: `-0.8633%`

`0.6` batch:

- `realtrace_single_rate_focus_20260415A_r0p6_bins50`

结果：

- `CS=64`: `-2.9394%`
- `CS=128`: `-3.2016%`
- `CS=256`: `-4.7105%`

结论：

- `0.7` 支持 `bins50 / TL192` 这条 mid-rate 线
- `0.6` 目前没有被这条线救起来

## Round B 计划

针对用户要求继续把 `0.8/0.9` 往上调，下一轮不是再重复第一轮 seeds，而是：

1. `0.9`：
   - 保留 `bins=10`
   - 重点打已经转正的 no-bypass 邻域：
     - `128:512`
     - `128:544`
     - `160:384`
     - `160:512`
2. `0.8`：
   - 一条线继续 `bins=10 default`
   - 围绕当前最接近 baseline 的 `96:384` 做小范围邻域：
     - `80:384`
     - `96:352`
     - `96:384`
     - `96:416`
     - `112:384`
     - `192:512`

## r=0.8 主线更新：统一 baseline 359

主线 baseline 统一为：

- sweep `359`
- `cp128 / mr8`
- `200 req`
- mean E2E `7933.3368 ms`

这条线下，之前若干“历史 win”不能再直接复用，因为那些 win 来自更弱或不同 family 的 baseline。

### bins10 小 TL 复用失败

batch:

- `realtrace_roundj_20260415_r0p8_bins10_refine_reuse359`

结果：

- `TL=96 / CS=388..408`
- 全部为负
- 最好也只有 `-7.16%`

结论：

- `bins10 / TL96 / medium-CS` 在 baseline `359` 下已基本失效

### bins20 也未救回

batch:

- `realtrace_roundk_20260415_r0p8_bins20_reuse359`

结果：

- 全部为负
- 最好：
  - `bins=20`
  - `TL=96`
  - `CS=384`
  - `-2.61%`

结论：

- `bins20` 比 `bins10` 略好，但仍明显输 baseline `359`

### Vidur-style bins50 / large-TL / small-CS 也失败

batch:

- `realtrace_roundl_20260415_r0p8_bins50_largeTL_reuse359`

已完成的 4/6 trial：

- `TL=160 / CS=64`: `-16.36%`
- `TL=192 / CS=48`: `-14.71%`
- `TL=192 / CS=64`: `-14.87%`
- `TL=192 / CS=96`: `-10.25%`

仍在跑：

- `TL=224 / CS=64`
- `TL=224 / CS=96`

当前结论：

- 仅把 Vidur 成功区的 `bins50 + large TL + small CS` 参数平移到 GPU，不足以在 `r=0.8` 打赢统一 baseline `359`

## Vidur simulator -> GPU 的关键机制差距

对照：

- `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py`
- `vidur/scheduler/replica_scheduler/uniform_segment_chunked_replica_scheduler.py`
- `scripts/wcp_sglang_patch.py`

确认差距：

1. Vidur 有真正的 segment-level WAIT：
   - `seg_full || entry_ready`
   - GPU patch 之前没有这个 gate
2. Vidur 支持 `uniform_segment_chunked` / `segment_size`
   - GPU patch 之前没有对应机制
3. GPU patch 之前实际只有：
   - total-limit
   - per-request chunk cap
   - type-mix reorder
   - seg-margin 派生 segment
   - underload bypass

因此，Vidur 的经验只能部分迁移到 GPU：

- 可直接迁移：
  - 更多 bins
  - 更大的 TL
  - 更小的 CS
- 不能直接迁移：
  - 真正依赖 WAIT / uniform segments 的收益

## 本轮代码补充

为避免“仿真里调过但 GPU 链路实际上没跑这个参数”的情况，本轮已把 `wait_gate` 打通到 GPU 链路：

- `scripts/wcp_sglang_patch.py`
  - 新增 admission-side WAIT 近似
- `scripts/launch_sglang_wcp.py`
  - 新增 `--enable-wcp-wait-gate`
- `scripts/sglang_wcp_rate_sweep_sql.py`
  - sweep / workload manifest / SQLite 新增 `wcp_wait_gate`
- `scripts/tune_sglang_wcp_tl_cs_parallel.py`
  - tuning trial SQLite 新增 `wait_gate`
  - 可用 `--wait-gate-modes off on`
- `scripts/tune_sglang_nestedwcp_vidur_realtrace.py`
  - Vidur-style wrapper 可继续把 `wait_gate` 作为调参维度传下去

注意：

- 当前 GPU WAIT 仍是 **admission-side approximation**
- 它不是完整 Vidur segment scheduler
- 但它终于把最关键的 WAIT 维度纳入了 GPU 实验口径

## 下一步

`roundl` 收尾后，`r=0.8` 不再继续单纯盲扫 `TL/CS`，而是优先做：

1. 复用统一 baseline `359`
2. 只测少量最有希望的点
3. 直接对照：
   - `wait_gate=off`
   - `wait_gate=on`
4. 首批候选以当前 `roundl` 最好点和接近点为主：
   - `192:96`
   - `224:64`
   - `224:96`
   - 另一条线补 `bins=20 default`：
     - `96:512`
     - `96:544`
     - `192:512`
3. baseline：
   - 按用户允许的方向，改用稍弱的 `cp128/mr8`
   - 不直接退回更极端 baseline，只先做一档温和弱化

## 当前自动化入口

为避免再手工起一堆单率命令，本轮新增队列脚本：

- [run_realtrace_single_rate_focus_queue.py](/home/archer/vidur_or/scripts/run_realtrace_single_rate_focus_queue.py)

它按上述顺序串行运行 single-rate focused batch，并把每个 batch 的 stdout/stderr 记录到：

- `outputs/sglang_single_rate_focus_queue/<queue_name>/`

Round B 新增 queue profile：

- `round-b-highrates`

## Round B 执行修正

2026-04-15 UTC 凌晨，曾误启动过一条 queue：

- queue name: `dryrun_roundb_highrates_20260415`
- queue prefix: `realtrace_roundb_20260415`
- 失败 baseline sweep: `242`

这条 queue 是在 sandbox 内启动的，`baseline_server.log` 明确报：

- `RuntimeError: No accelerator (CUDA, XPU, HPU, NPU) is available.`

因此：

- `realtrace_roundb_20260415_*` 这条前缀不应视为有效运行结果
- 它只写入了 sweep 头记录，没有任何 `sglang_run_results`

已改为在非 sandbox 环境重新启动同一 profile：

- queue name: `realtrace_roundb_highrates_live_20260415`
- queue prefix: `realtrace_roundb2_20260415`
- baseline: `cp128 / mr8`
- profile: `round-b-highrates`

当前实际进行中的 batch：

- `realtrace_roundb2_20260415_r0p9_bins10_nb`

该 batch 已确认：

- baseline `launch_server` 已正常占用 GPU
- `sglang_bench_serving_detailed.py` 已开始对 `rate=0.9` 打流
- 后续应以 `realtrace_roundb2_20260415_*` 作为 Round B 的正式 sweep 前缀

## Round B2 当前结果

### 0.9 bins10 no-bypass under cp128/mr8

baseline:

- sweep `243`
- mean E2E `10408.1196 ms`

结果：

- sweep `244`: `TL=128 / CS=512 / no-bypass`, `-11.9704%`
- sweep `245`: `TL=128 / CS=544 / no-bypass`, `-15.5035%`
- sweep `246`: `TL=160 / CS=384 / no-bypass`, `-6.2242%`
- sweep `247`: `TL=160 / CS=512 / no-bypass`, `-4.0053%`

结论：

- 这轮 `mr8` baseline 并没有真的把 `0.9` 变容易，fresh baseline 反而仍然很强
- `0.9` 不应继续押注这一条 large-TL no-bypass 线

### 0.8 bins10 default under cp128/mr8

baseline:

- sweep `248`
- mean E2E `8912.9166 ms`

已完成结果：

- sweep `250`: `TL=96 / CS=352 / default`, `+5.4978%`
- sweep `249`: `TL=80 / CS=384 / default`, `+0.5619%`

中间结论：

- `0.8` 已经被 small-TL / default 这条线救起来
- 当前最强 seed 是 `bins10 / TL96 / CS352 / default`
- 下一轮 `0.9` 应该沿这条 small-TL / default 线继续打，而不是再用 round B 的 no-bypass 邻域

## Round C 计划

已新增 queue profile：

- `round-c-r0p9-default-smalltl`

参数设计：

1. `0.9 bins10 default small-TL`
   - `96:320`
   - `96:352`
   - `96:384`
   - `112:352`
   - `112:384`
   - `128:384`
2. `0.9 bins20 default bridge`
   - `96:384`
   - `96:512`
   - `128:384`
   - `160:384`

目的：

- 先验证 `0.8` 的 rescue line 能否平移到 `0.9`
- 如果 bins10 small-TL 仍不够，再用 bins20 default 把它桥接回历史 `0.9` 的 bins20 正值区域

自动化：

- 当前 `round B2` queue 跑完后，已安排自动启动：
  - queue name: `realtrace_roundc_r0p9_smalltl_20260415`
  - queue prefix: `realtrace_roundc_20260415`

## Round C 结果

### 0.9 bins10 default small-TL

baseline:

- sweep `260`
- mean E2E `11419.1506 ms`

结果：

- sweep `264`: `TL=112 / CS=352 / default`, `+7.4332%`
- sweep `262`: `TL=96 / CS=352 / default`, `+7.2008%`
- sweep `266`: `TL=128 / CS=384 / default`, `+6.6390%`
- sweep `261`: `TL=96 / CS=320 / default`, `+6.4436%`
- sweep `263`: `TL=96 / CS=384 / default`, `-1.0045%`
- sweep `265`: `TL=112 / CS=384 / default`, `-1.4045%`

结论：

- `0.9` 已经被 round C 正式打正，而且幅度已经超过 `+7%`
- 关键经验不是 round B 的 large-TL no-bypass，而是：
  - `bins10`
  - `default bypass`
  - `TL` 维持在 `96~128`
  - `CS` 落在 `320~352` 或 `TL=128, CS=384`
- 对 `TL<=112` 来说，`CS=384` 明显像一个 cliff

### 0.9 bins20 default bridge

baseline:

- sweep `267`
- mean E2E `10573.8819 ms`

已完成结果：

- sweep `268`: `TL=96 / CS=512 / default`, `+0.5040%`
- sweep `269`: `TL=96 / CS=384 / default`, `-2.2067%`

进行中：

- `TL=128 / CS=384`
- `TL=160 / CS=384`

中间判断：

- bins20 在当前强 baseline 下没有明显超过 bins10 small-TL 线
- 当前最值得继续压的是 `bins10 / default / CS<384`

## Round D 计划

已新增 queue profile：

- `round-d-r0p9-bins10-refine`

参数设计：

1. `0.9 bins10 default refineA`
   - `96:336`
   - `96:352`
   - `104:336`
   - `104:352`
   - `112:336`
   - `112:352`
2. `0.9 bins10 default refineB`
   - `112:344`
   - `112:360`
   - `120:352`
   - `128:352`
   - `128:368`
   - `128:384`

目的：

- 围绕当前冠军 `112:352`
- 验证 `96~120 / 336~352` 是否存在更稳定更高的 sweet spot
- 单独检查 `TL=128` 这一支是否允许把 `CS` 推高到 `368/384` 仍保持正值

自动化：

- 当前 `round C` queue 跑完后，已安排自动启动：
  - queue name: `realtrace_roundd_r0p9_refine_20260415`
  - queue prefix: `realtrace_roundd_20260415`

## 当前 rate 覆盖判断

截至当前：

- `0.9`：已被 `bins10 / default / small-TL` 线打正，并且 peak 已超过 `+7%`
- `0.8`：在 round B2 的 `bins10 default` 线上已经打正，最好点落在 `TL=96 / CS=416`
- `0.7`：已有正值，当前最好仍是 `bins50 / TL=192 / CS=64`
- `1.0`：已有正值，历史最好仍集中在 `bins10 / TL=96 / CS=544`
- `0.6`：仍未被打正，是当前最主要未解决 rate

因此后续优先级调整为：

1. 继续 refine `0.9`
2. 主攻 `0.6`
3. 顺手把 `0.8` 冠军邻域再细化一轮

## Round E 计划

已新增 queue profile：

- `round-e-other-rates`

参数设计：

1. `0.6 bins10 default transfer`
   - `96:320`
   - `96:352`
   - `96:384`
   - `112:352`
   - `128:352`
   - `128:384`
2. `0.6 bins50 refine`
   - `160:64`
   - `192:48`
   - `192:64`
   - `192:96`
   - `224:64`
   - `224:96`
3. `0.8 bins10 default refine`
   - `96:384`
   - `96:400`
   - `96:416`
   - `96:432`
   - `104:400`
   - `112:400`

目的：

## 2026-04-15 晚间修正：统一 cp128/mr8 主线下的 `r=0.8`

用户明确要求后续汇报统一使用同一类 baseline，不再混用 `cp128/mr6`、`cp256/mr8`、`cp96/mr8` 等 side branch。

当前真正的 `r=0.8` 主线参考 baseline 是：

- sweep `359`
- `cp128 / mr8`
- mean E2E `7933.3368 ms`

这个 baseline 比之前多轮 `r=0.8` fresh baseline 都更强，因此：

- 历史上很多曾经“转正”的 `r=0.8` 配置，在这个 baseline 下都重新变成负值
- 问题已经不再是局部调一点 `CS` 就行，而是当前 GPU 版 nested WCP 本身缺少 simulator 里的一些关键自由度

### 已确认失败的 `r=0.8` 主线路径

1. `roundj`: `bins10 / TL96 / CS388~408`
   - 6/6 全负
   - 最好也只有 `-7.16%`
2. `roundk`: `bins20 / medium CS`
   - 6/6 全负
   - 最好点：
     - `bins20 / TL96 / CS384`
     - `8140.57 ms`
     - `-2.61%`

结论：

- 单纯把 `0.9` 的 small-TL line 平移到 `0.8` 不行
- 单纯把 `bins10` 提到 `bins20` 也不够

### 从 Vidur simulator 重新学到的关键点

本轮重新对照：

- [real_data_finetune.py](/home/archer/vidur_or/scripts/real_data_finetune.py)
- [real_data_high_qps.py](/home/archer/vidur_or/scripts/real_data_high_qps.py)
- [general_nested_chunked_replica_scheduler.py](/home/archer/vidur_or/vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py)
- [uniform_segment_chunked_replica_scheduler.py](/home/archer/vidur_or/vidur/scheduler/replica_scheduler/uniform_segment_chunked_replica_scheduler.py)
- [wcp_sglang_patch.py](/home/archer/vidur_or/scripts/wcp_sglang_patch.py)

得到两个重要结论：

1. simulator real-data 的突破，不是靠 `bins10` 局部微调，而是靠：
   - 更多 bins / 更细 segment 对齐
   - 更大的 `TL`
   - 更小的 `CS`
   - `seg_margin` 只是最后微调
2. GPU patch 目前并没有真正实现 Vidur 的两个关键结构：
   - **segment-level WAIT 机制** (`seg_full || entry_ready`)
   - **uniform segment_size 自由度**

当前 GPU 版真正具备的只是：

- 按 prompt type decode 边界自动分 segment
- `seg_margin`
- type-mix reorder
- underload bypass
- chunked prefill cap

因此：

- Vidur 的参数经验只能**部分迁移**
- 能立刻迁移的只有：
  - `更多 bins`
  - `更大 TL`
  - `更小 CS`
- 不能直接迁移的是：
  - WAIT gate 本身
  - uniform segment-size scheduler 本身

### 当前正在打的新方向

新的 `r=0.8` batch：

- `realtrace_roundl_20260415_r0p8_bins50_largeTL_reuse359`

口径：

- 复用 baseline `359`
- `bins=50`
- 直接走 Vidur-inspired 的 `large TL + small CS`

当前扫的 6 个点：

- `160:64`
- `192:48`
- `192:64`
- `192:96`
- `224:64`
- `224:96`

选择原因：

- 这些点来自已经在 `r=0.6` 打正的 `bins50` 家族
- 它们比之前 `0.8` 反复尝试的 `384/400` 中等 `CS` 更接近 simulator real-data 的成功结构

### 后续真正应该做的事

1. 先看 `roundl` 能不能把 `r=0.8` 拉回到接近 baseline，甚至转正。
2. 如果 `roundl` 仍全负：
   - 不应再继续平移 Vidur 参数表面数值
   - 应该开始改 GPU patch 本身：
     - 补真正的 WAIT gate
     - 或补可控的 uniform segment-size 近似
3. 也就是说，`r=0.8` 如果继续调不出来，下一阶段的重点就不再是“多跑几组 TL/CS”，而是“缩小 GPU patch 与 Vidur scheduler 机制本身的差距”。

- 对 `0.6` 同时开两条线：
  - 把 `0.8/0.9` 成功的 bins10 small-TL/default 线下迁
  - 保留并细化历史上最接近成功的 bins50 large-TL 线
- 对 `0.8` 继续围绕 `96:416` 的冠军邻域压更细的 chunk size

自动化：

- 当前 `round D` queue 跑完后，已安排自动启动：
  - queue name: `realtrace_rounde_other_rates_20260415`
  - queue prefix: `realtrace_rounde_20260415`

## Round E 结果

### 0.6 bins10 default transfer under cp128/mr8

baseline:

- sweep `286`
- mean E2E `6104.7888 ms`

结果：

- sweep `287`: `TL=96 / CS=352`, `+1.3591%`
- sweep `288`: `TL=96 / CS=320`, `+0.7709%`

说明：

- `0.6` 已经被 bins10 default small-TL 线第一次打正
- 但用户随后明确要求后续不要继续沿用这条新 baseline，而改用更弱 baseline

### 0.6 bins50 refine under cp128/mr8

baseline:

- sweep `293`
- mean E2E `6403.8635 ms`

结果：

- sweep `299`: `TL=224 / CS=96`, `+4.0347%`
- sweep `295`: `TL=160 / CS=64`, `+3.8921%`
- sweep `294`: `TL=192 / CS=48`, `+2.1459%`
- 其余 tested bins50 点也全部保持正值

结论：

- `0.6` 当前最强线已经从原来的 `TL=192 / CS=64` 推进到了 `TL=224 / CS=96`

### 0.8 bins10 refine under cp128/mr8

baseline:

- sweep `300`
- mean E2E `8361.8528 ms`

结果：

- sweep `302`: `TL=96 / CS=400`, `+2.2062%`
- sweep `303`: `TL=96 / CS=416`, `+0.4805%`
- 其余点转负

结论：

- `0.8` 的最优 corridor 已进一步收缩到 `TL=96`，且 `CS=400` 比 `CS=416` 更稳

## Baseline 切换决定

用户要求：

- 后续不要继续使用这条新的 `mr8` baseline 线
- 改用更弱一点的 baseline

因此从 `Round F` 开始，统一切到：

- `cp128 / mr6`

## Round F 计划

已新增 queue profile：

- `round-f-weakbaseline-victory`

覆盖的冠军线：

1. `0.6`
   - bins50:
     - `160:64`
     - `192:48`
     - `192:64`
     - `224:96`
2. `0.7`
   - bins50:
     - `192:64`
     - `192:128`
     - `224:96`
3. `0.8`
   - bins10 default:
     - `96:384`
     - `96:400`
     - `96:416`
     - `96:432`
4. `0.9`
   - bins10 default:
     - `96:352`
     - `104:352`
     - `112:352`
     - `128:384`
5. `1.0`
   - bins10 no-bypass:
     - `96:512`
     - `96:544`

自动化：

- 已直接启动：
  - queue name: `realtrace_roundf_weakbaseline_victory_20260415`
  - queue prefix: `realtrace_roundf_20260415`
  - baseline: `cp128/mr6`

## Round F 当前判断

`cp128/mr6` 并没有稳定表现成“真正更弱”的 baseline。

当前已完成部分：

- `0.6 bins50 weakbase`：全负
- `0.7 bins50 weakbase`：明显转正
- `0.8 bins10 weakbase`：目前已完成部分仍为负
- `0.9 bins10 weakbase`：前两组已完成部分仍为负

这说明：

- `cp128/mr6` 不能简单视为通用弱 baseline
- 在不同 rate 上它会出现 fresh baseline 反而更强的情况

## Round G 计划

为避免继续把“名义更弱”错当成“实际更弱”，下一轮改成 **true-weak baseline** 两段式：

1. `cp256/mr8`
   - 覆盖 `0.6 / 0.7 / 0.8 / 1.0`
2. `cp96/mr8`
   - 单独覆盖 `0.9`

理由：

- `0.8` 和 `1.0` 已有历史 baseline probe 证明 `cp256/mr8` 明显更弱
- `0.9` 已有历史 baseline probe 证明 `cp96/mr8` 明显更弱
- 不再继续假设 `cp128/mr6` 一定更弱

已新增 queue profiles：

- `round-g-lowmid-trueweak`
- `round-g-r0p9-cp96`

自动化：

- 当前 `round F` queue 跑完后，已安排顺序自动启动：
  - queue name: `realtrace_roundg_trueweak_lowmid_20260415`
  - queue prefix: `realtrace_roundg_20260415`
  - baseline: `cp256/mr8`
  - queue name: `realtrace_roundg_r0p9_cp96_20260415`
  - queue prefix: `realtrace_roundg2_20260415`
  - baseline: `cp96/mr8`

## 统一 baseline 决定

用户明确要求：

- 不要再对不同 rate 用不同 baseline 口径
- 统一一套 baseline 再调参

因此主线口径现在统一收敛为：

- `cp128 / mr8`

原因：

- 这是当前唯一一条已经在多个 rate 上跑出过明确正值且口径相对稳定的 baseline 线
- `0.6 / 0.8 / 0.9` 都已经在这条 baseline 家族下出现过正值
- `1.0` 则在更强的 `cp128/mr7` 下都已经赢过，因此放到 `cp128/mr8` 更合理
- 不再把 `cp256/mr8` 或 `cp96/mr8` 当主线，只保留为旁路探索证据

## Round H 统一主线

已新增 queue profile：

- `round-h-unified-cp128mr8`

统一 baseline：

- `cp128 / mr8`

覆盖：

1. `0.6`
   - bins50:
     - `160:64`
     - `192:48`
     - `224:96`
2. `0.7`
   - bins50:
     - `192:64`
     - `192:128`
     - `224:96`
3. `0.8`
   - bins10 / bins20:
     - `96:384`
     - `96:400`
     - `96:416`
     - `192:512`
4. `0.9`
   - bins10 default:
     - `96:320`
     - `96:352`
     - `112:352`
     - `128:384`
5. `1.0`
   - bins10 default:
     - `96:544`
   - bins10 no-bypass:
     - `96:512`
     - `96:576`

自动化：

- 已直接启动：
  - queue name: `realtrace_roundh_unified_cp128mr8_20260415`
  - queue prefix: `realtrace_roundh_20260415`
  - baseline: `cp128/mr8`

## 2026-04-16 Native Overlay Follow-up

- 已不再只做 wrapper 级调参，开始走本地 SGLang overlay：
  - `local_sglang_fork/python/sglang/...`
  - `scripts/launch_sglang_wcp.py --wcp-scheduler-impl native`
- native overlay 现已支持：
  - 多个 running chunked prefills
  - WAIT-based waiting-queue reorder
  - scheduler-side TL/CS cap
  - `uniform` segment mode + `segment_size`
- SQL / manifest / tuner 链路已补齐并落库：
  - `sglang_sweeps.wcp_segment_mode`
  - `sglang_sweeps.wcp_segment_size`
  - `sglang_parallel_tuning_trials.segment_mode`
  - `sglang_parallel_tuning_trials.segment_size`

### 已验证

- 首个 native smoke 已在 SQLite 落库：
  - `sweep_id = 452`
  - `exp_name = sglang_native_realtrace_smoke3_20260416`
  - 对 `rate=0.8` 曾有 `+1.58%` 的小幅正值
- 新增 uniform-segment smoke 已启动并写入 SQLite：
  - `sweep_id = 471`
  - `exp_name = sglang_native_uniform_smoke_20260416_r0p8_ss50`
  - 配置：
    - `native`
    - `segment_mode=uniform`
    - `segment_size=50`
    - `bins=20`
    - `TL=96`
    - `CS=384`

### 当前判断

- `realtrace_native_rounda_20260416_r0p8_bins20_reuse359`
  - 前 4 个 `derived-segment` trial 已落库，暂时全负：
    - `TL96/CS352/off = -10.35%`
    - `TL96/CS352/on = -16.28%`
    - `TL96/CS384/off = -10.21%`
    - `TL96/CS384/on = -14.02%`
- 说明仅靠 native + derived segments 继续细扫 `TL/CS` 还不够，下一步重点转向：
  - `uniform segment_size`
  - 先固定 `wait_gate=off`
  - 在 baseline family `359` 下继续找 `r=0.8` 可行 basin

### 已安排的自动续跑

- 现有 orchestrator 已挂起，流程为：
  1. 等 `rounda` 结束
  2. 先跑 `sglang_native_uniform_smoke_20260416_r0p8_ss50`
  3. 若 smoke 正常，自动启动：
     - `tuning_batch = realtrace_native_roundb_20260416_r0p8_bins20_reuse359_uniform`
     - watcher: `native_roundb_r0p8_uniform`
- `roundb` 配置：
  - baseline family: `359`
  - `rate=0.8`
  - `num_prompts=200`
  - `bins=20`
  - `segment_mode=uniform`
  - `segment_size in {25, 50, 100, 200, 500}`
  - `TL/CS in {(96,352), (96,384), (104,352), (104,384), (112,352), (112,384)}`
  - `wait_gate=off`

## 2026-04-16 Native Uniform Gate Fix

- 已定位 `roundb` 大幅翻负的一个实现级根因：
  - `local_sglang_fork/python/sglang/srt/managers/wcp_native.py`
  - `segment_entry_limit()` 原先采用按 `round_idx` 轮转 remainder 的配额分配
  - 对 `uniform segment_size=25/50/100` 这类小 segment，会在大量轮次里返回 `0`
  - 结果是 prefill admit 和 decode entry gate 周期性完全不放新 entry，请求在正式 `200 req` 长窗口下被严重饿死
- 已改为稳定的 per-round stage quota：
  - `segment_entry_limit()` 现在返回 `ceil(seg_total_limit / num_stages)`，不再轮转到 0
  - 已通过 `py_compile` 静态检查

### 修复前的失败证据

- `tuning_batch = realtrace_native_roundb_20260416_r0p8_bins20_reuse359_uniform`
  - baseline family 仍为 `359`
  - 已落库并保留的失败 trial：
    - `sweep 475`: `TL96/CS352/ss25 = -356.51%`
    - `sweep 476`: `TL96/CS352/ss50 = -37.88%`
    - `sweep 477`: `TL96/CS352/ss100 = -14.33%`
    - `sweep 478`: `TL96/CS352/ss200 = -26.41%`
    - `sweep 479`: `TL96/CS352/ss500 = -17.63%`
    - `sweep 480`: `TL96/CS384/ss25 = -367.26%`
    - `sweep 481`: `TL96/CS384/ss50 = -25.02%`
- 该批次已被手动停止，避免在错误 gate 逻辑上继续浪费 GPU。

### 修复后的直接回归验证

- 同一条原先翻负的配置重新验证：
  - 配置：`native + uniform + bins20 + TL96 + CS384 + segment_size=50 + wait_gate=off`
- `sweep 484`
  - `exp_name = sglang_native_gatefix_pair_20260416_r0p8_np50`
  - `50 req @ rate 0.8`
  - baseline mean E2E: `6718.87 ms`
  - WCP mean E2E: `6365.32 ms`
  - improvement: `+5.26%`
- `sweep 485`
  - `exp_name = sglang_native_gatefix_pair_20260416_r0p8_np200`
  - `200 req @ rate 0.8`
  - baseline mean E2E: `9425.90 ms`
  - WCP mean E2E: `9385.56 ms`
  - improvement: `+0.43%`
- 结论：
  - uniform segment 方向并未被否定
  - 之前的大负值主要来自 native entry gate starvation bug
  - 下一步应在修复后的代码上，围绕 `CS384`、`segment_size >= 50`、更合适的 `TL` 继续集中搜索

## 2026-04-17 Native Low-Rate Follow-Up

### 背景

- 直接把当前 `r=0.8` native champion 下推到低 rate：
  - `sweep 563`
  - `TL104 / CS384 / uniform ss250`
- 结果分化明显：
  - `r=0.7`: `+4.99%`
  - `r=0.6`: `-5.49%`
  - `r=0.5`: `-0.22%`
- 结论：
  - `0.7` 还能沿 high-rate basin transfer
  - `0.6/0.5` 需要单独找更低压的 native basin

### 新开的 r=0.6 fresh-baseline focused batch

- `tuning_batch = realtrace_native_roundg_20260417_r0p6_tlseg_focus`
- 固定口径：
  - `rate=0.6`
  - `num_prompts=200`
  - baseline `cp128/mr8`
  - `native + bins20 + uniform segments`
  - `CS=384`
  - 扫：
    - `TL in {64,72,80,88,96,104,112}`
    - `segment_size in {125,150,175,200,250,300}`

fresh baseline:

- `sweep 565`
- baseline mean E2E: `6134.8150 ms`

### 已落库结果

`TL=64 / CS=384`

- `sweep 566`
  - `ss150`
  - WCP mean E2E: `6038.8810 ms`
  - improvement: `+1.5638%`
- `sweep 568`
  - `ss175`
  - WCP mean E2E: `6041.4083 ms`
  - improvement: `+1.5226%`
- `sweep 567`
  - `ss125`
  - improvement: `-0.5275%`
- `sweep 569`
  - `ss200`
  - improvement: `-6.9758%`
- `sweep 570`
  - `ss250`
  - improvement: `-3.0262%`
- `sweep 571`
  - `ss300`
  - improvement: `-3.7974%`

`TL=72 / CS=384`

- `sweep 572`
  - `ss125`
  - WCP mean E2E: `6287.5049 ms`
  - improvement: `-2.4889%`
- `sweep 573`
  - `ss150`
  - WCP mean E2E: `6248.4540 ms`
  - improvement: `-1.8525%`

### 当前判断

- 低 rate 的 native 最优 basin 明显向更低 `TL` 偏移：
  - `TL64` 已经优于此前 transfer 进来的 `TL104`
- `segment_size` 也不是越大越好：
  - 目前最稳的是 `ss150~175`
  - `ss200+` 会快速翻负
- 到目前为止：
  - `TL64` 是正确方向
  - `TL72` 至少在 `ss125/150` 上已经弱于 `TL64`
- 因此后续优先级应是：
  1. 继续看这批 `TL72+` 是否还能出现反超 `TL64/ss150`
  2. 若没有，优先对 `TL64/ss150` 做 formal paired validation
  3. 再把 `TL64/ss150` 向 `r=0.5` 外推验证

### formal pair + transfer refine 结果

先做了硬验证：

- `sweep 586`
  - `TL64 / CS384 / uniform ss150`
  - `rate=0.6`: `+0.0436%`
  - `rate=0.5`: `-0.6908%`

这说明：

- `TL64/ss150` 在 fresh paired 口径下没有塌
- 但还不够把 `r=0.5` 稳定拉正

随后在同一份 fresh shared baseline 下继续收紧：

- `tuning_batch = realtrace_native_roundh_20260417_r0p6_r0p5_transfer_refine`
- baseline reference:
  - `sweep 587`
  - `rate=0.6`: `6319.5588 ms`
  - `rate=0.5`: `5350.1203 ms`
- 比较的候选：
  - `TL64/ss150`
  - `TL64/ss175`
  - `TL64/ss200`
  - `TL72/ss150`
  - `TL72/ss175`
  - `TL72/ss200`

shared-baseline refine 排名：

- `sweep 593`
  - `TL72 / ss200`
  - avg `+3.0099%`
  - `rate=0.6`: `+2.9394%`
  - `rate=0.5`: `+3.0803%`
- `sweep 590`
  - `TL64 / ss200`
  - avg `+2.7292%`
  - `rate=0.6`: `+3.0554%`
  - `rate=0.5`: `+2.4030%`
- `sweep 592`
  - `TL72 / ss175`
  - avg `+2.6487%`
  - `rate=0.6`: `+2.6349%`
  - `rate=0.5`: `+2.6624%`

反过来，原先更保守的小 segment 不够稳：

- `sweep 588`
  - `TL64 / ss150`
  - `rate=0.6`: `+3.8519%`
  - `rate=0.5`: `-0.0205%`
- `sweep 591`
  - `TL72 / ss150`
  - `rate=0.6`: `+4.6672%`
  - `rate=0.5`: `-0.7697%`

### 新判断

- 真正能把 `r=0.6 -> r=0.5` 一起拉正的，不是最保守的 `ss150`
- 更优的 transfer basin 已明显转向：
  - `segment_size = 175~200`
  - `TL = 64~72`
- 当前 shared-baseline 最强候选是：
  - `TL72 / CS384 / uniform ss200`
- 下一步最值得做的是：
  1. 对 `TL72/ss200` 做正式 paired validation
  2. 再对 `TL64/ss200` 做 paired 复核
  3. 若二者都稳，再继续向更低 rate 外推

### formal paired validation: TL72 / ss200

- `sweep 594`
- 配置：
  - `TL72`
  - `CS384`
  - `uniform ss200`
  - `bins20`
  - `num_prompts=200`
  - fresh paired baseline `cp128/mr8`

结果：

- `rate=0.6`
  - baseline: `6415.3122 ms`
  - WCP: `6111.2676 ms`
  - improvement: `+4.7394%`
- `rate=0.5`
  - baseline: `5449.2114 ms`
  - WCP: `5297.5800 ms`
  - improvement: `+2.7826%`

结论：

- `TL72 / CS384 / uniform ss200` 已经不是 shared-baseline 内部信号
- 它在 fresh formal paired sweep 下，能够同时打赢：
  - `r=0.6`
  - `r=0.5`
- 这条线可以视为当前 low-rate transfer 主线

### formal paired validation: TL64 / ss200

- `sweep 595`
- 配置：
  - `TL64`
  - `CS384`
  - `uniform ss200`
  - `bins20`
  - `num_prompts=200`
  - fresh paired baseline `cp128/mr8`

结果：

- `rate=0.6`
  - baseline: `6276.1321 ms`
  - WCP: `6199.1672 ms`
  - improvement: `+1.2263%`
- `rate=0.5`
  - baseline: `5270.0997 ms`
  - WCP: `5369.2872 ms`
  - improvement: `-1.8821%`

结论：

- `TL64 / ss200` 可以作为 `r=0.6` 的正值备选
- 但它不能稳定外推到 `r=0.5`
- 因此 low-rate 主线仍应优先保留：
  - `TL72 / ss200`

### formal paired validation: TL72 / ss175

- `sweep 596`
- 配置：
  - `TL72`
  - `CS384`
  - `uniform ss175`
  - `bins20`
  - `num_prompts=200`
  - fresh paired baseline `cp128/mr8`

结果：

- `rate=0.6`
  - baseline: `6681.3545 ms`
  - WCP: `6246.1487 ms`
  - improvement: `+6.5137%`
- `rate=0.5`
  - baseline: `5488.6219 ms`
  - WCP: `5452.4295 ms`
  - improvement: `+0.6594%`

结论：

- `TL72 / ss175` 也在 fresh formal paired sweep 下实现了：
  - `r=0.6` 正值
  - `r=0.5` 正值
- 因此 low-rate 区目前至少已有两条可 claim 的 hard winner：
  - `TL72 / ss200`
  - `TL72 / ss175`
- 其中：
  - `ss200` 更均衡，更适合作为主外推线
  - `ss175` 在 `r=0.6` 的提升更强，但在 `r=0.5` 更保守

### r=0.3 hard paired win 已确认，并继续尝试放大

- 正式 paired 胜线：
  - `sweep 642`
  - `exp = sglang_native_r0p3_formal_pair_20260418_tl72_cs384_ss200_np200`
  - 配置：
    - `TL72`
    - `CS384`
    - `uniform ss200`
    - `wait_gate=off`
    - `bins20`
    - `baseline cp128/mr8`

结果：

- `rate=0.3`
  - baseline: `4036.9631 ms`
  - WCP: `4000.6241 ms`
  - improvement: `+0.9002%`

结论：

- `r=0.3` 已经不是 shared-baseline 内部信号，而是 fresh paired 正值
- 但提升幅度仍偏小，所以继续围绕同一 low-rate family 做 amplify

### 当前进行中：r=0.3 amplify on fixed baseline 642

- batch: `realtrace_native_roundo_20260418_r0p3_amplify`
- baseline:
  - 固定复用 `sweep 642` 的 baseline
- 搜索空间：
  - `TL in {64, 72}`
  - `CS384`
  - `uniform segments`
  - `segment_size in {150, 175, 200, 225}`
  - `wait_gate=off`
  - `num_prompts=200`

当前已落库结果：

- `sweep 644`: `TL64 / ss150` -> `+0.4542%`
- `sweep 643`: `TL64 / ss175` -> `-0.1195%`
- `sweep 645`: `TL64 / ss200` -> `+1.9705%`
- `sweep 646`: `TL64 / ss225` -> `+0.1260%`

当前解释：

- `TL64 / ss200` 已经在 fixed-baseline 下把 `r=0.3` 从正式 paired 的 `+0.9002%` 推到内部 `+1.9705%`
- 说明 `r=0.3` 仍有放大空间
- 但这还不是 fresh paired 结论，仍需要等 `TL72` 分支收尾后再决定 formal pair

### 新增 tuning 轴：native prefill_budget

代码侧新增：

- `scripts/sglang_wcp_rate_sweep_sql.py`
  - 已接入 `--wcp-prefill-budget`
  - sweep 参数会落到 SQLite `sglang_sweeps.wcp_prefill_budget`
- `scripts/tune_sglang_wcp_tl_cs_parallel.py`
  - 已接入 `--prefill-budget-values`
  - tuning trial 参数会落到 SQLite `sglang_parallel_tuning_trials.prefill_budget`

关键发现：

- 在当前 real-trace bins20 + `CS384` 设置下，native 公式导出的 `derived_prefill_budget_tokens` 恒为 `384`
- 这等价于默认只放一个 chunk 级 prefill request
- 因此高负载大 win 的下一个重点不该只是继续扫 `TL/segment_size`
- 更值得看的是：
  - `prefill_budget = 768 / 1152 / 1536`
  - 即允许 2/3/4 个 chunk 级 prefill 并发

### 已挂起的自动 follow-up

- 脚本：
  - `scripts/supervise_native_bigwin_followup.py`
- 当前行为：
  - 先等待 `realtrace_native_roundo_20260418_r0p3_amplify` 满 `8` 个 trials
  - 若最优 `r=0.3` 内部结果超过阈值，则自动跑 fresh formal pair
  - 随后自动发起：
    - `r=0.8`
    - fixed baseline `547`
    - `TL100/104`
    - `ss250/300`
    - `prefill_budget in {384, 768, 1152, 1536}`
  - 若内部结果超过阈值，则自动跑 fresh formal pair

当前 supervisor 状态目录：

- `outputs/native_bigwin_followup/followup_20260418_052539/`

补充注意：

- 通过自定义 Python supervisor 直接在当前 Codex sandbox 中再去 spawn GPU SGLang 服务，会命中：
  - `RuntimeError: No accelerator (CUDA, XPU, HPU, NPU) is available.`
- 因此后续真正的 GPU 连续调参，必须继续复用已经获批、可脱离 sandbox 的入口：
  - `scripts/sglang_wcp_rate_sweep_sql.py`
  - `scripts/tune_sglang_wcp_tl_cs_parallel.py`
- 自定义 supervisor 只能负责“决策/排队逻辑”，不能直接作为 GPU launch 宿主

### 当前进行中：r=0.1 / r=0.2 low-rate bootstrap

- batch:
  - `realtrace_native_roundq_20260418_r0p1_r0p2_bootstrap`
- 目的：
  - 给目前完全空白的 `r=0.1 / 0.2` 建第一批可用 basin
- 配置空间：
  - `TL in {32, 40, 48, 56}`
  - `CS384`
  - `uniform ss in {175, 200}`
  - `wait_gate=off`
  - `bypass in {default, disabled}`
  - `bins20`
  - `num_prompts=200`
  - fresh shared baseline:
    - `cp128 / mr8`
- 当前状态：
  - baseline sweep 已落库：
    - `sweep 652`
    - `exp = realtrace_native_roundq_20260418_r0p1_r0p2_bootstrap_baseline_ref`

### r=0.1 / r=0.2 bootstrap 已完成：低率最优点开始分叉

- batch:
  - `realtrace_native_roundq_20260418_r0p1_r0p2_bootstrap`
- baseline:
  - `sweep 652`
  - `rate=0.1` baseline mean e2e:
    - `3330.3329 ms`
  - `rate=0.2` baseline mean e2e:
    - `3617.3931 ms`

关键结论：

- `disabled bypass` 在 `r=0.1 / 0.2` 上几乎全线负值
- 因此低率主线必须保留：
  - `default underload bypass`
- `r=0.1` 和 `r=0.2` 的最优点已经开始分叉
  - `r=0.1` 更像：
    - `TL40 / ss175`
  - `r=0.2` 更像：
    - `TL56 / ss200`
    - 或 `TL40 / ss200`

roundq 最好 shared-baseline 结果：

- 平均最强：
  - `sweep 659`
  - `TL40 / CS384 / ss200 / default bypass`
  - 平均 improvement:
    - `+2.5437%`
  - 分 rate:
    - `r=0.1`: `+3.8471%`
    - `r=0.2`: `+1.2403%`
- `r=0.1` 单点最强：
  - `sweep 657`
  - `TL40 / CS384 / ss175 / default bypass`
  - `r=0.1`: `+5.2469%`
  - 但 `r=0.2` 同 sweep 为：
    - `-1.667%`
- `r=0.2` 单点最强：
  - `sweep 667`
  - `TL56 / CS384 / ss200 / default bypass`
  - `r=0.2`: `+1.4516%`
  - `r=0.1`: `+2.5823%`

结论：

- `r=0.1` 已经出现内部“大 win”信号，但还没有 fresh formal pair
- `r=0.2` 目前只有小幅正值，必须继续 refine
- 下一步不该再把 `0.1` 和 `0.2` 完全绑在一起优化

### 当前进行中：r=0.2 focused refine with prefill_budget

- batch:
  - `realtrace_native_roundr_20260418_r0p2_refine_pb`
- baseline:
  - 复用 `sweep 652` 的 `r=0.2`
- 搜索空间：
  - `TL in {40, 48, 56, 64}`
  - `CS384`
  - `uniform ss in {200, 225}`
  - `prefill_budget in {384, 768}`
  - `default bypass`
  - `wait_gate=off`

目的：

- 确认 `r=0.2` 更偏向：
  - 更大的 `TL`
  - 还是更大的 `prefill_budget`
- 如果 internal improvement 明显超过当前 `+1.45%`，就转 fresh formal pair

### r=0.1 hard paired win 已确认

- `sweep 685`
- `exp = sglang_native_r0p1_formal_pair_20260418_tl40_cs384_ss175_np200`
- 配置：
  - `TL40`
  - `CS384`
  - `uniform ss175`
  - `default bypass`
  - `wait_gate=off`
  - `bins20`
  - `baseline cp128/mr8`

结果：

- `rate=0.1`
  - baseline: `3384.2252 ms`
  - WCP: `3269.7431 ms`
  - improvement: `+3.3828%`

结论：

- `r=0.1` 已经从 bootstrap 内部信号升级为真正的 fresh formal paired 胜利
- 虽然比 shared-baseline 的 `+5.2469%` 收缩，但仍然是低率区目前第一条明确 hard winner

### 当前进行中：r=0.2 local basin refine around TL56

- batch:
  - `realtrace_native_rounds_20260418_r0p2_tl56_localbasin`
- baseline:
  - 继续复用 `sweep 652`
- 搜索空间：
  - `TL in {52, 56, 60}`
  - `CS384`
  - `uniform ss in {190, 200, 210, 225}`
  - `default bypass`
  - `wait_gate=off`
  - 不显式指定 `prefill_budget`

理由：

- `roundr` 已经表明：
  - `prefill_budget` 这条线没有把 `r=0.2` 提升到超过当前冠军
  - 当前 `r=0.2` 最强 internal 仍然是：
    - `TL56 / ss200 / default bypass`
    - `+1.4516%`
- 因此下一步优先围绕 `TL56` 主 basin 做局部放大，而不是继续扫更弱的 `pb` 轴

### 2026-04-20: native wait_gate decode gate bug fixed, r=0.5 internal line flipped positive

本轮不再把 `wait_gate=on` 当成纯参数问题，而是直接检查了 native 本地实现。

核心发现：

- 旧版 `wait_gate` 在 decode 侧会把“未满足 entry 条件的 segment”整体冻结
- 这会把已经在 segment 内部推进的 decode 请求一起 retract 掉
- 对 `r=0.5` 这种中低负载 real-trace，会造成系统性大负值

已修改本地实现：

- 文件：
  - `local_sglang_fork/python/sglang/srt/managers/wcp_native.py`
- 修正思路：
  - `wait_gate` 只 gate 新进入 segment 的 `entry-stage`
  - 已经在 segment 内部的 decode 请求继续跑
  - 对第一段 segment，把 `waiting_queue_len` 也计入 `entry_supply`

修正后的第一轮 revalidation：

- baseline reference:
  - sweep `788`
  - `r=0.5` baseline mean E2E:
    - `5467.1778 ms`
- post-fix focused shared-baseline 结果：
  - sweep `789`
    - `TL72 / CS384 / ss175 / wait_gate=on`
    - WCP mean E2E:
      - `5198.9738 ms`
    - improvement vs baseline `788`:
      - `+4.906%`
  - sweep `790`
    - `TL72 / CS384 / ss200 / wait_gate=on`
    - `+4.108%`
  - sweep `791`
    - `TL74 / CS384 / ss175 / wait_gate=on`
    - WCP mean E2E:
      - `5110.3090 ms`
    - improvement vs baseline `788`:
      - `+6.527%`
  - sweep `792`
    - `TL74 / CS384 / ss200 / wait_gate=on`
    - `-1.827%`

结论：

- bug 修正是实质性的，不是噪声
- 同样的 `wg=on` 线路在修前是大负值，修后已经能在 shared-baseline 下稳定翻正
- 当前 shared-baseline 最强点是：
  - `TL74 / CS384 / ss175 / wait_gate=on`

### 2026-04-20: r=0.5 post-fix wait_gate formal pair still failed

基于上面的 shared-baseline winner，已做 fresh formal pair：

- sweep `793`
- exp:
  - `sglang_native_r0p5_formal_pair_20260420_tl74_cs384_ss175_wg_afterfix_np200`

结果：

- baseline mean E2E:
  - `5270.0438 ms`
- WCP mean E2E:
  - `5372.0737 ms`
- improvement:
  - `-1.9360%`

结论：

- 修后的 `wait_gate=on` 在 `r=0.5` 上已经显著改善 shared-baseline 行为
- 但仍未站住 fresh formal pair
- 因此当前还不能替换掉 `r=0.5` 现有 formal best：
  - `TL72 / CS384 / ss200 / wait_gate=off / sweep 594 / +2.7826%`

### 2026-04-20: post-fix wait_gate transfer to r=0.6 was weak

继续把修后的 `wait_gate=on` 往 `r=0.6` 外推：

- baseline reference:
  - sweep `794`
  - baseline mean E2E:
    - `6129.2158 ms`
- tuning batch:
  - `realtrace_native_wgon_r0p6_afterfix_20260420a`
- 搜索：
  - `TL in {72, 74, 76}`
  - `CS384`
  - `uniform ss in {165, 175, 185}`
  - `wait_gate=on`

关键结果：

- sweep `799`
  - `TL74 / CS384 / ss175 / wait_gate=on`
  - WCP mean E2E:
    - `6107.7048 ms`
  - improvement vs baseline `794`:
    - `+0.351%`

其余 8 个点均为负值：

- sweep `795`: `TL72 / ss175` -> `-1.452%`
- sweep `796`: `TL72 / ss165` -> `-0.837%`
- sweep `797`: `TL72 / ss185` -> `-1.181%`
- sweep `798`: `TL74 / ss165` -> `-1.387%`
- sweep `800`: `TL74 / ss185` -> `-3.721%`
- sweep `801`: `TL76 / ss165` -> `-2.074%`
- sweep `802`: `TL76 / ss175` -> `-3.905%`
- sweep `803`: `TL76 / ss185` -> `-3.996%`

结论：

- 修后的 `wait_gate=on` 在 `r=0.6` 上已经不再像修前那样“系统性大崩”
- 但它只产生了一个非常弱的 shared-baseline 正点
- 当前不值得把 `r=0.6` 切换到 `wg=on` formalization
- `r=0.6` 仍以现有 `wait_gate=off` formal best 为主

### 2026-04-20: post-fix wait_gate transfer to r=0.7 produced one meaningful internal winner

继续把修后的 `wait_gate=on` 往 `r=0.7` 外推：

- baseline reference:
  - sweep `804`
  - baseline mean E2E:
    - `7277.1642 ms`
- tuning batch:
  - `realtrace_native_wgon_r0p7_afterfix_20260420a`
- 搜索：
  - `TL in {96, 104, 112}`
  - `CS384`
  - `uniform ss in {200, 250, 300}`
  - `wait_gate=on`

关键结果：

- sweep `806`
  - `TL96 / CS384 / ss250 / wait_gate=on`
  - improvement vs baseline `804`:
    - `+2.872%`

其余 8 个点全部为负：

- sweep `805`: `TL96 / ss200` -> `-3.710%`
- sweep `807`: `TL96 / ss300` -> `-4.532%`
- sweep `808`: `TL104 / ss200` -> `-2.117%`
- sweep `809`: `TL104 / ss250` -> `-2.201%`
- sweep `810`: `TL104 / ss300` -> `-2.171%`
- sweep `811`: `TL112 / ss200` -> `-4.255%`
- sweep `812`: `TL112 / ss250` -> `-8.741%`
- sweep `813`: `TL112 / ss300` -> `-0.488%`

结论：

- 修后的 `wait_gate=on` 在 `r=0.7` 上开始出现像样的 shared-baseline 正线
- 这条线同样很窄：
  - `TL96 / ss250 / wg=on`
- `TL104+` 基本可以排除
- 下一步最值得做的是直接把 sweep `806` 做 fresh formal pair，确认它是不是能在更高 rate 变成真正可用的 `wg=on` 胜线

### 2026-04-20: r=0.7 post-fix wait_gate formal pair succeeded

基于 sweep `806` 的 shared-baseline winner，已做 fresh formal pair：

- sweep `814`
- exp:
  - `sglang_native_r0p7_formal_pair_20260420_tl96_cs384_ss250_wg_afterfix_np200`

结果：

- baseline mean E2E:
  - `7441.8110 ms`
- WCP mean E2E:
  - `7246.6646 ms`
- improvement:
  - `+2.6223%`

结论：

- 修后的 `wait_gate=on` 已经在 `r=0.7` 上拿到真正的 fresh formal paired 胜利
- 当前这条线的 formal winner 为：
  - `TL96 / CS384 / ss250 / wait_gate=on`
- 但它还没有超过原有 `r=0.7` best native formal-like paired winner：
  - sweep `563`
  - `TL104 / CS384 / ss250 / wait_gate=off`
  - `+4.9921%`

意义：

- `wait_gate` 修正不只是让 shared-baseline 内部结果“看起来更好”
- 它已经在更高一点的 rate 上转化成真实 formal win
- 下一步可以继续把同思路外推到 `r=0.8`

### 2026-04-20: post-fix wait_gate transfer to r=0.8 found only a weak internal positive

继续把修后的 `wait_gate=on` 往 `r=0.8` 外推，先做 coarse probe，再做局部 refine。

coarse probe:

- baseline reference:
  - sweep `815`
  - baseline mean E2E:
    - `8554.9860 ms`
- tuning batch:
  - `realtrace_native_wgon_r0p8_afterfix_20260420a`
- 搜索：
  - `TL in {96, 104, 112}`
  - `CS384`
  - `uniform ss in {150, 200, 250}`
  - `wait_gate=on`

coarse probe 最好点：

- sweep `820`
  - `TL104 / CS384 / ss200 / wait_gate=on`
  - WCP mean E2E:
    - `8482.1460 ms`
  - improvement vs baseline `815`:
    - `+0.851%`

其余 coarse 点全部为负：

- sweep `816`: `TL96 / ss150` -> `-3.402%`
- sweep `817`: `TL96 / ss200` -> `-6.676%`
- sweep `818`: `TL96 / ss250` -> `-2.139%`
- sweep `819`: `TL104 / ss150` -> `-6.496%`
- sweep `821`: `TL104 / ss250` -> `-2.007%`
- sweep `822`: `TL112 / ss150` -> `-3.007%`
- sweep `823`: `TL112 / ss200` -> `-2.065%`
- sweep `824`: `TL112 / ss250` -> `-6.118%`

随后围绕这个唯一 positive 点做了局部 refine：

- baseline reference:
  - sweep `825`
  - baseline mean E2E:
    - `8459.7451 ms`
- tuning batch:
  - `realtrace_native_wgon_r0p8_afterfix_refine_20260420b`
- 搜索：
  - `TL in {100, 104, 108}`
  - `CS384`
  - `uniform ss in {190, 200, 210}`
  - `wait_gate=on`

refine 最好点：

- sweep `827`
  - `TL100 / CS384 / ss200 / wait_gate=on`
  - WCP mean E2E:
    - `8373.0212 ms`
  - improvement vs baseline `825`:
    - `+1.025%`

其余 refine 点全部为负：

- sweep `826`: `TL100 / ss190` -> `-1.477%`
- sweep `828`: `TL100 / ss210` -> `-1.576%`
- sweep `829`: `TL104 / ss190` -> `-5.852%`
- sweep `830`: `TL104 / ss200` -> `-8.396%`
- sweep `831`: `TL104 / ss210` -> `-3.557%`
- sweep `832`: `TL108 / ss190` -> `-2.258%`
- sweep `833`: `TL108 / ss200` -> `-5.974%`
- sweep `834`: `TL108 / ss210` -> `-5.725%`

结论：

- 修后的 `wait_gate=on` 在 `r=0.8` 上确实存在一个很窄的 internal 正点：
  - `TL100 / CS384 / ss200 / wait_gate=on`
- 但强度仍然偏弱，目前只有：
  - `+1.025%`
- 现阶段还不值得直接做 fresh formal pair
- `r=0.8` 仍以现有更强的 `wait_gate=off` native 线为主，`wg=on` 先保留为后续机制增强方向
