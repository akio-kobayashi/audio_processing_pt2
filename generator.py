#!/usr/bin/python3

import numpy as np
import sys, os, re, gzip, struct
import random
import h5py
import copy
import tensorflow as tf

ASC_CLASS=5

'''
    DataGenerator
    学習や評価で用いるデータの読み出しと加工（正規化）を行うクラス
'''
class DataGenerator(tf.keras.utils.Sequence):

    '''
        *** 初期化 ***
        インスタンスが作成されるときによびだされる
        パラメータを設定する
    '''
    def __init__(self, file, batch_size=64, dim=(40,500), n_channels=1, shuffle=True):

        self.file=file
        self.batch_size=batch_size
        self.dim=dim
        self.n_classes=ASC_CLASS
        self.n_channels=n_channels
        self.shuffle=shuffle
        self.mean=0.0
        self.var=0.0
        self.keys=[]
        self.true_labels={"cat":0, "cow":1, "dog":2, "frog":3, "pig":4}

        self.h5fd = h5py.File(self.file, 'r')
        self.n_samples = len(self.h5fd.keys())
        for key in self.h5fd.keys():
            self.keys.append(key)

        if self.shuffle:
            random.shuffle(self.keys)

    '''
        *** データの総数を返す ***
    '''
    def __num_samples__(self):
        return len(self.keys)

    '''
        *** バッチ総数を返す ***
    '''
    def __len__(self):
        return int(np.ceil(self.n_samples)/self.batch_size)


    '''
        *** データからバッチを取り出す ***
    '''
    def __getitem__(self, index):
        list_keys_temp = [self.keys[k] for k in range(index*self.batch_size,
                                                      min( (index+1)*self.batch_size, len(self.keys) ) )]

        x, y = self.__data_generation(list_keys_temp)

        return x, y

    '''
        *** 1回の学習終了後に行う処理 ***
    '''
    def on_epoch_end(self):
        if self.shuffle == True:
            random.shuffle(self.keys)

    '''
        *** データの読み出しと前処理を行う ***
    '''
    def __data_generation(self, list_keys_temp):
        x = np.zeros((self.batch_size, *self.dim, self.n_channels))
        y = np.empty((self.batch_size), dtype=int)

        self.mean=np.reshape(self.mean, (self.dim[0],1))
        self.var=np.reshape(self.var, (self.dim[0],1))

        for i, key in enumerate(list_keys_temp):
            mat = self.h5fd[key+'/feature'][()]
            label = self.h5fd[key+'/label'][()]
            # 平均=0, 分散=1のガウス分布に従うように正規化する
            mat = mat - self.mean
            mat = np.divide(mat, self.var)

            if mat.shape[1] > self.dim[1]:
                mat=mat[:, 0:self.dim[1]]

            src = np.reshape(mat, (1, self.dim[0], self.dim[1], 1))
            x[i,:,0:src.shape[2],:] = src
            y[i] = label

        return x, tf.keras.utils.to_categorical(y, num_classes=self.n_classes)

    '''
        *** データの平均と標準偏差を計算する ***
        データの分布は正規分布であることを前提とする
    '''
    def compute_norm(self):
        mean=None
        sq_mean=None
        rows=0
        for key in self.keys:
            mat=self.h5fd[key+'/feature'][()]
            rows += mat.shape[1]
            if mean is None:
                mean=np.sum(mat, axis=1).astype(np.float64)
                sq_mean=np.sum(np.square(mat), axis=1).astype(np.float64)
            else:
                mean=np.add(np.sum(mat, axis=1).astype(np.float64), mean)
                sq_mean=np.add(np.sum(np.square(mat), axis=1).astype(np.float64), sq_mean)
        mean = mean/rows
        sq_mean = sq_mean/rows - np.square(mean)
        sq_mean=np.sqrt(sq_mean+1.0e-8)

        self.mean=mean.astype(np.float32)
        self.var=sq_mean.astype(np.float32)

    '''
        *** データの平均と標準偏差を返す ***
    '''
    def get_norm(self):
        return self.mean, self.var

    '''
        *** データの平均と標準偏差を設定する ***
        評価データの平均と分散は学習データの平均と分散に合わせておく
    '''
    def set_norm(self, mean, var):
        self.mean = mean
        self.var = var
