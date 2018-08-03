import os, sys
import numpy as np


class CONFIG(object):

    def __init__(self, args):
        """Some manual work needed for CV to put groupings here.

        But external code can loop through the CV indices.
        To find 10-fold CV for a group of N rollouts, do:

            [list(x) for x in np.array_split( np.random.permutation(N) , 10) ]

        and paste the result in `CV_GROUPS`.
        """
        self.args = args
        self.PERFORM_CV = args.do_cv
        self.PRINT_PREDS = args.print_preds

        self.CONFIG_NAME = 'grasp_net'
        self.ROOT_DIR    = '/nfs/diskstation/seita/bed-make/'   # Tritons
        self.DATA_PATH   = self.ROOT_DIR+''                     # Tritons
        self.NET_NAME    = '08_28_01_37_11save.ckpt-30300'

        if self.PERFORM_CV:
            assert args.cv_idx is not None
            self.ROLLOUT_PATH = self.DATA_PATH+'rollouts_white_v01/'
            self.CV_GROUPS = [
                [24, 22, 30,  2],
                [10, 21,  5, 15],
                [36, 32, 17,  7],
                [ 6, 11, 34,  1],
                [12, 19, 28, 29],
                [23,  0, 35, 27],
                [18, 13, 16, 14],
                [20, 33, 25],
                [ 3, 31,  4],
                [ 9, 26,  8]
            ]
            self.CV_HELD_OUT_INDEX = args.cv_idx
        else:
            # Now do this if I have a fixed held-out directory, as with Michael's data.
            # Note: BC_HELD_OUT is not used if PERFORM_CV=True.
            self.ROLLOUT_PATH = self.DATA_PATH+'rollouts_nytimes/'
            self.BC_HELD_OUT  = self.DATA_PATH+'held_out_nytimes/'

        # Other paths now.
        self.IMAGE_PATH   = self.DATA_PATH+'images/'
        self.LABEL_PATH   = self.DATA_PATH+'labels/'
        self.CACHE_PATH   = self.DATA_PATH+'cache/'
        self.OUTPUT_DIR   = self.DATA_PATH+'output/'

        # Based on transitions (NOTE: is this used at all?)
        self.TRAN_OUTPUT_DIR   = self.DATA_PATH+'transition_output/'
        self.TRAN_STATS_DIR    = self.TRAN_OUTPUT_DIR+'stats/'
        self.TRAIN_STATS_DIR_T = self.TRAN_OUTPUT_DIR+'train_stats/'
        self.TEST_STATS_DIR_T  = self.TRAN_OUTPUT_DIR+'test_stats/'

        # If training grasp net, info goes here. Order matters, OUTPUT_DIR is updated.
        self.OUTPUT_DIR        = self.DATA_PATH+'grasp_output/'
        self.STAT_DIR          = self.OUTPUT_DIR+'stats/'
        self.TRAIN_STATS_DIR_G = self.OUTPUT_DIR+'train_stats/'
        self.TEST_STATS_DIR_G  = self.OUTPUT_DIR+'test_stats/'

        # Weights
        self.WEIGHTS_DIR = self.DATA_PATH+'weights/'
        self.PRE_TRAINED_DIR = '/nfs/diskstation/seita/yolo_tensorflow/data/pascal_voc/weights/'
        self.WEIGHTS_FILE = None
        # WEIGHTS_FILE = os.path.join(DATA_PATH, 'weights', 'YOLO_small.ckpt')

        # Classes, labels, data augmentation
        self.CLASSES = ['success_grasp','fail_grasp']
        self.NUM_LABELS = len(self.CLASSES)
        ## self.FLIPPED = False
        ## self.LIGHTING_NOISE = True
        ## self.QUICK_DEBUG = True

        # Model parameters. The USE_DEPTH is a critical one to test!
        self.T_IMAGE_SIZE_H = 480
        self.T_IMAGE_SIZE_W = 640
        self.IMAGE_SIZE = 448
        self.CELL_SIZE = 7
        self.BOXES_PER_CELL = 2
        self.ALPHA = 0.1
        self.DISP_CONSOLE = True
        self.RESOLUTION = 10
        self.USE_DEPTH = True # False means RGB

        # solver parameter
        # Careful, if fixing, this means our images effectively turn into (fs,fs,channels),
        # e.g., could be (14,14,1024). If False, TRAIN FROM NORMAL (480,640,3)-SIZE IMAGES.
        self.FIX_PRETRAINED_LAYERS = True # Technically call it pre-'initialized' layers.
        self.OPT_ALGO = 'ADAM'
        if self.OPT_ALGO == 'ADAM':
            self.LEARNING_RATE = 0.00010
            self.USE_EXP_MOV_AVG = False
        elif self.OPT_ALGO == 'SGD':
            self.LEARNING_RATE = 0.01
            self.USE_EXP_MOV_AVG = True
        else:
            raise ValueError(self.OPT_ALGO)
        self.DECAY_STEPS = 10000 # Decay every k steps
        self.DECAY_RATE = 0.1
        self.STAIRCASE = True
        self.BATCH_SIZE = 64
        self.MAX_ITER = args.max_iters
        self.SUMMARY_ITER = 1
        self.TEST_ITER = 1
        self.SAVE_ITER = 100
        self.VIZ_DEBUG_ITER = 400

        ## # test parameter
        ## self.PICK_THRESHOLD = 0.4
        ## self.THRESHOLD = 0.4
        ## self.IOU_THRESHOLD = 0.5

        # fast params
        self.FILTER_SIZE = 14
        self.NUM_FILTERS = 1024
        self.FILTER_SIZE_L1 = 7
        self.SIZE_L2 = 50176


    def compute_label(self,datum):
        """Labels scaled in [-1,1], as described in paper.

        Actually, [-0.5, 0.5]. I thought we needed to further adjust for the re-sizing
        of the image to (448,448), but turns out this is still valid ... since the re-
        sized value cancels out. Huh, interesting.
        """
        pose = datum['pose']
        label = np.zeros((2))
        x = (float(pose[0]) / self.T_IMAGE_SIZE_W) - 0.5
        y = (float(pose[1]) / self.T_IMAGE_SIZE_H) - 0.5
        label = np.array([x,y])
        return label


    def compare_preds_labels(self, preds, labels, doprint=False):
        """Try to get losses in the original pixel space for interpretability."""
        xx = np.array([self.T_IMAGE_SIZE_W, self.T_IMAGE_SIZE_H])
        raw_preds  = (0.5 + preds) * xx
        raw_labels = (0.5 + labels) * xx
        assert np.min(raw_labels) > 0.0
        delta = raw_preds - raw_labels # shape (batchsize,2)
        test_loss_raw = np.mean( np.linalg.norm(delta, axis=1) )
        if doprint:
            print("grasp test preds:\n{}".format(preds))
            print("grasp test labels:\n{}".format(labels))
            print("(raw) grasp test preds:\n{}".format(raw_preds))
            print("(raw) grasp test labels:\n{}".format(raw_labels))
        return test_loss_raw


    def get_empty_state(self, batchdim=None):
        """Each time we call a batch during training/testing, initialize with this."""
        bs = self.BATCH_SIZE
        if batchdim is not None:
            bs = batchdim

        if self.FIX_PRETRAINED_LAYERS:
            return np.zeros((bs, self.FILTER_SIZE, self.FILTER_SIZE, self.NUM_FILTERS))
        else:
            assert self.IMAGE_SIZE == 448
            return np.zeros((bs, self.IMAGE_SIZE, self.IMAGE_SIZE, 3))


    def get_empty_label(self, batchdim=None):
        """Each time we call a batch during training/testing, initialize with this."""
        if batchdim is not None:
            return np.zeros((batchdim, 2))
        else:
            return np.zeros((self.BATCH_SIZE, 2))


    def break_up_rollouts(self,rollout):
        """I changed it to a way that makes more sense, a list of one-item lists."""
        grasp_rollout = []
        for data in rollout:
            if type(data) is list:
                continue
            if data['type'] == 'grasp':
                grasp_rollout.append( [data] )
        return grasp_rollout
