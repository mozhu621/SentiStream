#!/usr/bin/env python3
import random
import copy
import re
import numpy as np
import argparse

from pyflink.datastream.execution_mode import RuntimeExecutionMode

from batch_inferrence import batch_inference
from evaluation import evaluation
from supervised_model import supervised_model
from utils import load_and_augment_data

np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)

import logging
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream import CheckpointingMode
import pandas as pd
import sys
from modified_PLStream import unsupervised_stream
from classifier import clasifier
from time import time

logger = logging.getLogger('PLStream')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('plstream.log', mode='w')
formatter = logging.Formatter('PLStream:%(thread)d %(lineno)d: %(levelname)s: %(asctime)s %(message)s',
                              datefmt='%m/%d/%Y %I:%M:%S %p', )
fh.setFormatter(formatter)
logger.addHandler(fh)

PSEUDO_DATA_COLLECTION_THRESHOLD = 0
ACCURACY_THRESHOLD = 0.9
parallelism = 1
train_data_size = 0

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")

    start_time = time()

    # input_path = './yelp_review_polarity_csv/test.csv'
    # if input_path is not None:
    f = pd.read_csv('./exp_train.csv', header=None)  # , encoding='ISO-8859-1'
    f.columns = ["label", "review"]

    f.loc[f['label'] == 1, 'label'] = 0
    f.loc[f['label'] == 2, 'label'] = 1

    true_label = f.label
    yelp_review = f.review
    data_stream = []
    for i in range(len(yelp_review)):
        data_stream.append((i, int(true_label[i]), yelp_review[i]))
        # print((i, int(true_label[i]), yelp_review[i]))

    print("unsupervised stream,classifier and evaluation")
    print('Coming Stream is ready...')
    print('===============================')
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.get_checkpoint_config().set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
    ds = env.from_collection(collection=data_stream)

    #  always specify output_type when writing to file

    ds1 = unsupervised_stream(ds)
    ds1.print()
    ds2 = clasifier(ds)
    ds2.print()
    ds = evaluation(ds1, ds2, to_file=False)
    # .key_by(lambda x: x[0])
    ds.print()
    env.execute()

    # data source for batch_inferrence and supervised_model
    pseudo_data_folder = './senti_output'
    test_data_file = './exp_test.csv'
    train_data_file = './exp_train.csv'

    # data sets
    pseudo_data_size, test_df = load_and_augment_data(pseudo_data_folder, test_data_file)
    test_data_size = len(test_df)
    true_label = test_df.label
    yelp_review = test_df.review
    data_stream = []
    for i in range(len(yelp_review)):
        data_stream.append((int(true_label[i]), yelp_review[i]))

    print("batch_inference")
    print('Coming Stream is ready...')
    print('===============================')

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_runtime_mode(RuntimeExecutionMode.BATCH)
    env.set_parallelism(1)
    env.get_checkpoint_config().set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
    ds = env.from_collection(collection=data_stream)
    accuracy = batch_inference(ds, test_data_size)
    print(accuracy)

    print("supervised_model_train")
    pseudo_data_size, train_df = load_and_augment_data(pseudo_data_folder, train_data_file)
    train_data_size = len(train_df)

    supervised_model(parallelism, train_df, train_data_size, pseudo_data_size, PSEUDO_DATA_COLLECTION_THRESHOLD,
                     accuracy,
                     ACCURACY_THRESHOLD)

    logging.info("time taken for execution is: " + str(time() - start_time))