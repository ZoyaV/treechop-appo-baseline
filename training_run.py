import json
from argparse import Namespace
from pathlib import Path

import yaml

from sample_factory.utils.utils import log

import wandb
from sample_factory.envs.env_registry import global_env_registry
from sample_factory.run_algorithm import run_algorithm
import sys
from sample_factory.algorithms.appo.model_utils import register_custom_encoder
from model_with_target import ResnetEncoderWithTarget
from create_env import make_iglu, make_ray_iglu
from utils.config_validation import Experiment


def make_env(full_env_name, cfg=None, env_config=None):
    return make_iglu()
    #return make_treechop()


def register_custom_components():
    global_env_registry().register_env(
        env_name_prefix='IGLUSilentBuilder-v0',
        make_env_func=make_env,
    )
    register_custom_encoder('custom_env_encoder', ResnetEncoderWithTarget)


def validate_config(config):
    exp = Experiment(**config)
    flat_config = Namespace(**exp.async_ppo.dict(),
                            **exp.experiment_settings.dict(),
                            **exp.global_settings.dict(),
                            **exp.evaluation.dict(),
                            full_config=exp.dict()
                            )
    return exp, flat_config


def main():
    register_custom_components()

    import argparse

    parser = argparse.ArgumentParser(description='Process training config.')

    parser.add_argument('--config_path', type=str, action="store",
                        help='path to yaml file with single run configuration', required=False)

    parser.add_argument('--raw_config', type=str, action='store',
                        help='raw json config', required=False)

    parser.add_argument('--wandb_thread_mode', type=bool, action='store', default=False,
                        help='Run wandb in thread mode. Usefull for some setups.', required=False)

   # parser.add_argument('--with_wandb', action='store_true', default=True)

    params = parser.parse_args()

    if params.raw_config:
        config = json.loads(params.raw_config)
    else:
        if params.config_path is None:
            config = Experiment().dict()
        else:
            with open(params.config_path, "r") as f:
                config = yaml.safe_load(f)

    exp, flat_config = validate_config(config)
    log.debug(exp.global_settings.experiments_root)

    if exp.global_settings.use_wandb:
        import os
        if params.wandb_thread_mode:
            os.environ["WANDB_START_METHOD"] = "thread"
        wandb.login(key=os.environ.get('WANDB_APIKEY'))
        wandb.init(project=exp.name, config=exp.dict(), save_code=False, sync_tensorboard=True)

    status = run_algorithm(flat_config)
    if exp.global_settings.use_wandb:
        import shutil
        path = Path(exp.global_settings.train_dir) / exp.global_settings.experiments_root
        zip_name = str(path)
        shutil.make_archive(zip_name, 'zip', path)
        wandb.save(zip_name + '.zip')
    return status


if __name__ == '__main__':
    sys.exit(main())
