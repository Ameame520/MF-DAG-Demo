from __future__ import annotations

from mfdag.simulation.runner import SimulationRunner


def run_mean_field_llm(cfg, run_dir, **kwargs):
    runner = SimulationRunner(
        cfg,
        run_dir,
        method="mean_field_llm",
        use_memory=False,
        use_mean_field=True,
        use_follower=True,
        **kwargs,
    )
    return runner.run()
