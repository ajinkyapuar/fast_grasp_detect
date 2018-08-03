import tensorflow as tf
import datetime, os, time, random, argparse
import numpy as np
from fast_grasp_detect.networks.grasp_net_cs import GHNet
from fast_grasp_detect.core.data_manager import data_manager
from fast_grasp_detect.core.train_network import Solver
from fast_grasp_detect.configs.bed_grasp_config import CONFIG


def set_seed(s):
    tf.set_random_seed(s)
    np.random.seed(s)
    random.seed(s)


# Arguments, random seeds, etc.
parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=0)
parser.add_argument('--cv_idx', type=int)
parser.add_argument('--do_cv', action='store_true', default=False)
args = parser.parse_args()
bed_grasp_options = CONFIG(args)
set_seed(args.seed)

# Three major components, note `pascal` has reference to the 'yolo' network.
pascal = data_manager(bed_grasp_options)
yolo = GHNet(bed_grasp_options, pascal)
solver = Solver(bed_grasp_options, yolo, pascal)

print('\nJust before training, here is `tf.GraphKeys.TRAINABLE_VARIABLES`:')
variables = tf.trainable_variables()
for vv in variables:
    print(vv)
print('\nAnd here is `tf.GraphKeys.GLOBAL_VARIABLES`:')
variables = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES)
for vv in variables:
    print(vv)

print('\nStart training ...')
solver.train()
print('Done training.')
