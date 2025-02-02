import os
import pytest
import torch
from torchbenchmark.util.machine_config import get_machine_config, check_machine_configured


def pytest_addoption(parser):
    parser.addoption("--fuser", help="fuser to use for benchmarks")
    parser.addoption("--ignore_machine_config",
                     action='store_true',
                     help="Disable checks/assertions for machine configuration for stable benchmarks")
    parser.addoption("--disable_nograd", action='store_true',
                    help="Disable no_grad for eval() runs")
    parser.addoption("--check_opt_vs_noopt_jit",
                     action='store_true',
                     help="The best attempt to check results for inference runs. Not all models support this!")
    parser.addoption("--cpu_only", action='store_true',
                    help="Run benchmarks on cpu only and ignore machine configuration checks")

def set_fuser(fuser):
    if fuser == "old":
        torch._C._jit_set_profiling_executor(False)
        torch._C._jit_set_profiling_mode(False)
        torch._C._jit_override_can_fuse_on_gpu(True)
        torch._C._jit_set_texpr_fuser_enabled(False)
    elif fuser == "te":
        torch._C._jit_set_profiling_executor(True)
        torch._C._jit_set_profiling_mode(True)
        torch._C._jit_set_bailout_depth(20)
        torch._C._jit_set_num_profiled_runs(2)
        torch._C._jit_override_can_fuse_on_cpu(False)
        torch._C._jit_override_can_fuse_on_gpu(True)
        torch._C._jit_set_texpr_fuser_enabled(True)

def pytest_sessionstart(session):
    try:
        check_machine_configured()
    except Exception as e:
        if not session.config.getoption('ignore_machine_config'):
            pytest.exit(f"{e}\nSee README.md for machine tuning script usage, or use --ignore_machine_config")

def pytest_configure(config):
    set_fuser(config.getoption("fuser"))

def pytest_benchmark_update_machine_info(config, machine_info):
    machine_info['pytorch_version'] = torch.__version__
    machine_info['pytorch_git_version'] = torch.version.git_version
    machine_info['cuda_version'] = torch.version.cuda

    try:
        import torchtext
        machine_info['torchtext_version'] = torchtext.__version__
    except ImportError:
        machine_info['torchtext_version'] = '*not-installed*'

    try:
        import torchvision
        machine_info['torchvision_version'] = torchvision.__version__
    except ImportError:
        machine_info['torchvision_version'] = '*not-installed*'

    machine_info['circle_build_num'] = os.environ.get("CIRCLE_BUILD_NUM")
    machine_info['circle_project_name'] = os.environ.get("CIRCLE_PROJECT_REPONAME")

    try:
        # if running on unexpected machine/os, get_machine_config _may_ not work
        machine_info['torchbench_machine_config'] = get_machine_config()
    except Exception:
        if not config.getoption('ignore_machine_config'):
            raise
