import numpy as np
import tensorflow as tf
import sys, os, cv2
slim = tf.contrib.slim


class GHNet(object):

    def __init__(self, cfg, data_m, is_training=True):
        """
        data_m: Needs to contain `data_m.yc.conv_layer` so that we get the tensorflow variable
            representing the 26th layer of the YOLO network, in case we need to continue passing it
            through here if not fixing the 26 layers.
        """
        self.cfg = cfg
        self.classes = self.cfg.CLASSES
        self.num_class = len(self.classes)
        self.image_size = self.cfg.IMAGE_SIZE
        self.dist_size_w = self.cfg.T_IMAGE_SIZE_W/self.cfg.RESOLUTION
        self.dist_size_h = self.cfg.T_IMAGE_SIZE_H/self.cfg.RESOLUTION
        self.learning_rate = self.cfg.LEARNING_RATE
        self.batch_size = self.cfg.BATCH_SIZE
        self.alpha = self.cfg.ALPHA
        self.yolo_conv_layer = data_m.yc.conv_layer

        # 2-D output because we are predicting (x,y) pixel coords
        self.output_size = 2

        # In case we want to apply dropout. Training only! Currently confusing since there is
        # another `is_training` from earlier. This here helps to see _validation_ performance.
        self.training_mode = tf.placeholder(tf.bool, name='training_mode')
        self.keep_prob = cfg.DROPOUT_KEEP_PROB

        # Despite the name, `self.images` are features from YOLO stem.
        # Also, `logits` are not log prob of classes but simply the predicted pixels.
        if cfg.FIX_PRETRAINED_LAYERS:
            assert not cfg.SMALLER_NET
            self.images = tf.placeholder(tf.float32, [None, cfg.FILTER_SIZE, cfg.FILTER_SIZE, cfg.NUM_FILTERS], name='images')
            self.logits = self.build_network(self.images, self.output_size, self.alpha, self.training_mode)
        else:
            self.logits = self.build_network(self.yolo_conv_layer, self.output_size, self.alpha, self.training_mode)

        if is_training:
            # self.labels to be provided by the human user
            self.labels = tf.placeholder(tf.float32, [None, 2])
            self.loss_layer(self.logits, self.labels)
            self.total_loss = tf.losses.get_total_loss()
            tf.summary.scalar('total_loss', self.total_loss)


    def build_network(self, images, num_outputs, alpha, training_mode, scope='yolo'):
        """Extra layers built on _top_ of the YOLO stem (first 26 layers)."""
        with tf.variable_scope(scope):
            net = images

            if self.cfg.NET_TYPE == 3:
                assert self.cfg.SMALLER_NET
                with slim.arg_scope([slim.conv2d, slim.fully_connected],
                                    activation_fn=leaky_relu(alpha),
                                    weights_initializer=tf.truncated_normal_initializer(0.0,0.01),
                                    #weights_initializer=tf.contrib.layers.xavier_initializer(),
                                    weights_regularizer=slim.l2_regularizer(self.cfg.L2_LAMBDA)):
                    net = slim.conv2d(net, 64, [7, 7], 2, padding='SAME')
                    net = slim.conv2d(net, 128, [5, 5], 2, padding='SAME')
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.conv2d(net, 128, [5, 5])
                    net = slim.conv2d(net, 192, [3, 3], 2)
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.conv2d(net, 192, [3, 3])
                    net = slim.conv2d(net, 192, [3, 3])
                    net = slim.conv2d(net, 128, [3, 3])
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.flatten(net)
                    net = slim.fully_connected(net, 2000)
                    net = slim.dropout(net, keep_prob=self.keep_prob, is_training=training_mode)
                    net = slim.fully_connected(net, 2000)
                    net = slim.fully_connected(net, num_outputs, activation_fn=None)

            elif self.cfg.NET_TYPE == 4:
                # To reduce complexity, for now make this similar to the case above
                assert self.cfg.SMALLER_NET
                with slim.arg_scope([slim.conv2d, slim.fully_connected],
                                    activation_fn=leaky_relu(alpha),
                                    weights_initializer=tf.truncated_normal_initializer(0.0,0.01),
                                    #weights_initializer=tf.contrib.layers.xavier_initializer(),
                                    weights_regularizer=slim.l2_regularizer(self.cfg.L2_LAMBDA)):

                    net = slim.conv2d(net, 64, [7, 7], 1, padding='SAME')
                    net = slim.conv2d(net, 128, [5, 5], 2, padding='SAME')
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.conv2d(net, 128, [5, 5])
                    net = slim.conv2d(net, 192, [3, 3], 2)
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.conv2d(net, 192, [3, 3])
                    net = slim.conv2d(net, 192, [3, 3])
                    net = slim.conv2d(net, 128, [3, 3])
                    net = slim.max_pool2d(net, [2, 2], 2)

                    net = slim.flatten(net)
                    net = slim.fully_connected(net, 2000)
                    net = slim.dropout(net, keep_prob=self.keep_prob, is_training=training_mode)
                    net = slim.fully_connected(net, 2000)
                    net = slim.fully_connected(net, num_outputs, activation_fn=None)

            else:
                assert not self.cfg.SMALLER_NET
                assert self.cfg.NET_TYPE == 1 or self.cfg.NET_TYPE == 2
                with slim.arg_scope([slim.conv2d, slim.fully_connected],
                                    activation_fn=leaky_relu(alpha),
                                    weights_initializer=tf.truncated_normal_initializer(0.0,0.01),
                                    #weights_initializer=tf.contrib.layers.xavier_initializer(),
                                    weights_regularizer=slim.l2_regularizer(self.cfg.L2_LAMBDA)):
                    net = slim.conv2d(net, 256, 3, stride=2, scope='conv_29')
                    net = slim.conv2d(net, 256, 3, scope='conv_30')
                    net = tf.transpose(net, [0, 3, 1, 2], name='trans_31')
                    net = slim.flatten(net, scope='flat_32')

                    # The YOLO paper only did a dropout after the first FC layer.
                    net = slim.fully_connected(net, 1024, scope='fc_33')
                    net = slim.dropout(net, keep_prob=self.keep_prob, is_training=training_mode)
                    net = slim.fully_connected(net, 1024, scope='fc_34')
                    net = slim.fully_connected(net, num_outputs, activation_fn=None, scope='fc_36')
        get_variables()
        return net


    def loss_layer(self, predict_classes, classes, scope='loss_layer'):
        """Despite the names here, this should be standard mean square error (L2) loss."""
        with tf.variable_scope(scope):
            class_delta = (predict_classes - classes) # not `class` but just error
            self.class_loss = tf.reduce_mean(
                    tf.reduce_sum(tf.square(class_delta), axis=[1]), name='class_loss'
            )
            tf.losses.add_loss(self.class_loss)
            tf.summary.scalar('class_loss', self.class_loss)


def leaky_relu(alpha):
    def op(inputs):
        return tf.maximum(alpha * inputs, inputs, name='leaky_relu')
    return op


def get_variables():
    print("")
    variables = tf.trainable_variables()
    numv = 0
    for vv in variables:
        numv += np.prod(vv.shape)
        print(vv)
    print("\nNumber of parameters: {}".format(numv))
