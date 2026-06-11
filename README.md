# MF-DAG — Bluesky Blacksky Experiment

基于 Bluesky Social Dataset 2024 的 MF-DAG 完整实验框架（Blacksky / condition_2）。

## 快速开始

```bash
cd /Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG
pip install -r requirements.txt
export DEEPSEEK_API_KEY=your_key

# 1. 构建 processed 数据
python scripts/build_blacksky_dataset.py --config configs/mfdag_blacksky.yaml

# 2. Debug 闭环（20 threads / 20 agents / 2 cohorts）
python scripts/run_mfdag_blacksky.py --config configs/mfdag_blacksky.yaml --debug

# 3. 正式 Full MF-DAG（全部 988 threads）
python scripts/run_mfdag_blacksky.py --config configs/mfdag_blacksky.yaml

# 4. Baselines
python scripts/run_baselines_blacksky.py --config configs/mfdag_blacksky.yaml --baseline mean_field_llm
python scripts/run_baselines_blacksky.py --config configs/mfdag_blacksky.yaml --baseline rule_based_agent
python scripts/run_baselines_blacksky.py --config configs/mfdag_blacksky.yaml --baseline full_llm_agent

# 5. 评估
python scripts/evaluate_blacksky.py --run_dir outputs/runs/<run_id>
```

详细需求见 `需求文档.md`。
