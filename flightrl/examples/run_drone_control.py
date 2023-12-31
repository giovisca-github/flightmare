#!/usr/bin/env python3
from ruamel.yaml import YAML, dump, RoundTripDumper

#
import os
import math
import argparse
import numpy as np
import time
import sys
import torch

#
from stable_baselines3.common import logger

#
from stable_baselines3.ppo.ppo import PPO
from rpg_baselines.ppo.ppo2_test import test_model
import rpg_baselines.common.util as U
from rpg_baselines.envs import vec_env_wrapper as wrapper
from scipy.spatial.transform import Rotation 
#
from flightgym import QuadrotorEnv_v1


def configure_random_seed(seed, env=None):
    if env is not None:
        env.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', type=int, default=1,
                        help="To train new model or simply test pre-trained model")
    parser.add_argument('--render', type=int, default=1,
                        help="Enable Unity Render")
    parser.add_argument('--save_dir', type=str, default=os.path.dirname(os.path.realpath(__file__)),
                        help="Directory where to save the checkpoints and training metrics")
    parser.add_argument('--seed', type=int, default=0,
                        help="Random seed")
    parser.add_argument('-w', '--weight', type=str, default='./saved/quadrotor_env.zip',
                        help='trained weight path')
    return parser


def main():
    args = parser().parse_args()
    cfg = YAML().load(open(os.environ["FLIGHTMARE_PATH"] +
                           "/flightlib/configs/vec_env.yaml", 'r'))
    if not args.train:
        cfg["env"]["num_envs"] = 1
        cfg["env"]["num_threads"] = 1

    if args.render:
        cfg["env"]["render"] = "yes"
    else:
        cfg["env"]["render"] = "no"

    env = wrapper.FlightEnvVec(QuadrotorEnv_v1(
        dump(cfg, Dumper=RoundTripDumper), False))
    if args.render:
        connectedToUnity = False 
        while not connectedToUnity:
            connectedToUnity = env.connectUnity()             
            if not connectedToUnity:  
                print("Couldn't connect to unity, will try another time.")
    
    print("env.num_envs : ", env.num_envs)

    max_ep_length = env.max_episode_steps

    if env.num_envs == 1:
        object_density_fractions = np.ones([env.num_envs], dtype=np.float32)
    else:
        object_density_fractions = np.linspace(0.0, 1.0, num=env.num_envs)

    env.set_objects_densities(object_density_fractions = object_density_fractions)   
    env.reset()
    
    time.sleep(2.5)    
    # set random seed
    configure_random_seed(args.seed, env=env)

    #
    if args.train:
        # save the configuration and other files
        rsg_root = os.path.dirname(os.path.abspath(__file__))
        log_dir = rsg_root + '/saved'
        saver = U.ConfigurationSaver(log_dir=log_dir)
        model = PPO('MlpPolicy', env, verbose=2,
                    tensorboard_log=saver.data_dir)

        # tensorboard
        # Make sure that your chrome browser is already on.
        # TensorboardLauncher(saver.data_dir + '/PPO2_1')

        # PPO run
        # Originally the total timestep is 5 x 10^8
        # 10 zeros for nupdates to be 4000
        # 1000000000 is 2000 iterations and so
        # 2000000000 is 4000 iterations.
        logger.configure(folder=saver.data_dir)
        model.learn(
            total_timesteps=int(25000000))
        model.save(saver.data_dir)

    # # Testing mode with a trained weight
    else:
        model = PPO.load(args.weight)
        test_model(env, model, render=args.render)


if __name__ == "__main__":
    main()
