#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import cv2
import numpy as np
import sys
import os

# ヒストグラム均一化
def equalizeHistRGB(src):

    RGB = cv2.split(src)
    Blue   = RGB[0]
    Green = RGB[1]
    Red    = RGB[2]
    for i in range(3):
        cv2.equalizeHist(RGB[i])

    img_hist = cv2.merge([RGB[0],RGB[1], RGB[2]])
    return img_hist

# ガウシアンノイズ
def addGaussianNoise(src):
    row,col,ch= src.shape
    mean = 0
    var = 0.1
    sigma = 15
    gauss = np.random.normal(mean,sigma,(row,col,ch))
    gauss = gauss.reshape(row,col,ch)
    noisy = src + gauss

    return noisy

# salt&pepperノイズ
def addSaltPepperNoise(src):
    row,col,ch = src.shape
    s_vs_p = 0.5
    amount = 0.004
    out = src.copy()
    # Salt mode
    num_salt = np.ceil(amount * src.size * s_vs_p)
    coords = [np.random.randint(0, i-1 , int(num_salt))
                 for i in src.shape]
    out[tuple(coords[:-1])] = (255,255,255)

    # Pepper mode
    num_pepper = np.ceil(amount* src.size * (1. - s_vs_p))
    coords = [np.random.randint(0, i-1 , int(num_pepper))
             for i in src.shape]
    out[tuple(coords[:-1])] = (0,0,0)
    return out


# Daniel: uniform noise
def addUniformNoise(src):
    row,col,ch = src.shape
    low = -4.0
    high = 4.0
    unif_noise = np.random.uniform(low=low, high=high, size=(row,col,ch))
    noisy = src + unif_noise
    noisy = np.maximum(noisy, 0.0)
    return noisy

# Daniel: salt only
def addSaltOnlyNoise(src):
    row,col,ch = src.shape
    s_vs_p = 0.5
    amount = 0.004
    out = src.copy()
    # Salt mode
    num_salt = np.ceil(amount * src.size * s_vs_p)
    coords = [np.random.randint(0, i-1 , int(num_salt))
                 for i in src.shape]
    out[tuple(coords[:-1])] = (255,255,255)
    return out


# https://github.com/mdlaskey/fast_grasp_detect/commit/2f85441c86fa7eed089cafb638f0a5bb2fa1eddb
def get_depth_aug(img_src):
    """
    Use this (rather than `get_lighting`) for data augmentation with depth images.
    The depth images will need to have been pre-processed so that they are 3 channels.
    """
    trans_img = []
    trans_img.append(img_src)
    trans_img.append(addUniformNoise(img_src))
    trans_img.append(addGaussianNoise(img_src))
    trans_img.append(addSaltPepperNoise(img_src))
    trans_img.append(addSaltOnlyNoise(img_src))
    return trans_img


def get_lighting(img_src):
    # ルックアップテーブルの生成
    min_table = 50
    max_table = 205
    diff_table = max_table - min_table
    gamma1 = 0.75
    gamma2 = 1.5

    LUT_HC = np.arange(256, dtype = 'uint8' )
    LUT_LC = np.arange(256, dtype = 'uint8' )
    LUT_G1 = np.arange(256, dtype = 'uint8' )
    LUT_G2 = np.arange(256, dtype = 'uint8' )

    LUTs = []

    # 平滑化用
    average_square = (10,10)

    # ハイコントラストLUT作成
    for i in range(0, min_table):
        LUT_HC[i] = 0

    for i in range(min_table, max_table):
        LUT_HC[i] = 255 * (i - min_table) / diff_table

    for i in range(max_table, 255):
        LUT_HC[i] = 255

    # その他LUT作成
    for i in range(256):
        LUT_LC[i] = min_table + i * (diff_table) / 255
        LUT_G1[i] = 255 * pow(float(i) / 255, 1.0 / gamma1)
        LUT_G2[i] = 255 * pow(float(i) / 255, 1.0 / gamma2)

    LUTs.append(LUT_HC)
    LUTs.append(LUT_LC)
    LUTs.append(LUT_G1)
    LUTs.append(LUT_G2)

    # 画像の読み込み
    trans_img = []
    trans_img.append(img_src)

    # LUT変換
    for i, LUT in enumerate(LUTs):
        trans_img.append( cv2.LUT(img_src, LUT))
    return trans_img


if __name__ == '__main__':
    img_name = "frame_29.png"
    in_dir = "images"
    out_dir = "out_images"

    img_in = cv2.imread(in_dir + "/" + img_name, 1)
    imgs_out = get_lighting(img_in)
    for i, img in enumerate(imgs_out):
        cv2.imwrite(out_dir + "/" + img_name + str(i) + ".png" ,img)
