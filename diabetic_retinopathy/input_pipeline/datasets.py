import gin
import logging
import tensorflow as tf
import tensorflow_datasets as tfds
from input_pipeline.preprocessing import preprocess, augment
import numpy as np


@gin.configurable
def load(name, data_dir):
    if name == "idrid":
        logging.info(f"Preparing dataset {name}...")
        # 2classes
        train_filename = ["idrid-2train.tfrecord-00000-of-00001"]
        val_filename = ["idrid-2val.tfrecord-00000-of-00001"]
        test_filename = ["idrid-2test.tfrecord-00000-of-00001"]
        # train_filename = [data_dir + "/idrid-train.tfrecord-00000-of-00001"]
        # val_filename = [data_dir + "/idrid-val.tfrecord-00000-of-00001"]
        # test_filename = [data_dir + "/idrid-test.tfrecord-00000-of-00001"]
        ds_train = tf.data.TFRecordDataset(train_filename)

        ds_val = tf.data.TFRecordDataset(val_filename)
        ds_test = tf.data.TFRecordDataset(test_filename)
        ds_info = "idrid"
        feature_description = {
            'image': tf.io.FixedLenFeature([], tf.string),
            'label': tf.io.FixedLenFeature([], tf.int64, default_value=-1),
            'img_height': tf.io.FixedLenFeature([], tf.int64, default_value=-1),
            'img_width': tf.io.FixedLenFeature([], tf.int64, default_value=-1)
        }

        def _parse_function(exam_proto):
            temp = tf.io.parse_single_example(exam_proto, feature_description)
            img = tf.io.decode_jpeg(temp['image'], channels=3)
            img = tf.reshape(img, [4288, 2848, 3])
            label = temp['label']
            return (img, label)

        ds_train = ds_train.map(_parse_function, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds_val = ds_val.map(_parse_function, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds_test = ds_test.map(_parse_function, num_parallel_calls=tf.data.experimental.AUTOTUNE)

        # resamping imbalanced data
        nonref_ds = ds_train.filter(lambda features, label: label == 0)
        ref_ds = ds_train.filter(lambda features, label: label == 1)
        ds_train = tf.data.experimental.sample_from_datasets([nonref_ds, ref_ds], [0.5, 0.5])

        # #def count(counts, batch):
        #     features, labels = batch
        #     class_1 = labels == 1
        #     class_1 = tf.cast(class_1, tf.int32)
        #
        #     class_0 = labels == 0
        #     class_0 = tf.cast(class_0, tf.int32)
        #
        #     counts['class_0'] += tf.reduce_sum(class_0)
        #     counts['class_1'] += tf.reduce_sum(class_1)
        #
        #     return counts
        #
        # counts = ds_train.take(10).reduce(
        #     initial_state={'class_0': 0, 'class_1': 0},
        #     reduce_func=count)
        #
        # counts = np.array([counts['class_0'].numpy(),
        #                    counts['class_1'].numpy()]).astype(np.float32)
        #
        # fractions = counts / counts.sum()
        # tf.print("fractions: " + str(fractions))
        #
        # def class_func(features, label):
        #     return label
        # resampler = tf.data.experimental.rejection_resample(
        #     class_func, target_dist=[0.5, 0.5], initial_dist=fractions)
        # resample_ds = ds_train.apply(resampler)
        # ds_train = resample_ds.map(lambda extra_label, features_and_label: features_and_label)
        return prepare(ds_train, ds_val, ds_test, ds_info)

    elif name == "eyepacs":
        logging.info(f"Preparing dataset {name}...")
        (ds_train, ds_val, ds_test), ds_info = tfds.load(
            'diabetic_retinopathy_detection/btgraham-300:3.0.0',
            split=['train', 'validation', 'test'],
            shuffle_files=True,
            with_info=True,
            data_dir=data_dir
        )

        def _preprocess(img_label_dict):
            return img_label_dict['image'], img_label_dict['label']

        ds_train = ds_train.map(_preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds_val = ds_val.map(_preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)
        ds_test = ds_test.map(_preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)

        return prepare(ds_train, ds_val, ds_test, ds_info)

    elif name == "mnist":
        logging.info(f"Preparing dataset {name}...")
        (ds_train, ds_val, ds_test), ds_info = tfds.load(
            'mnist',
            split=['train[:90%]', 'train[90%:]', 'test'],
            shuffle_files=True,
            as_supervised=True,
            with_info=True,
            data_dir=data_dir
        )

        return prepare(ds_train, ds_val, ds_test, ds_info)

    else:
        raise ValueError


@gin.configurable
def prepare(ds_train, ds_val, ds_test, ds_info, batch_size, caching):
    # Prepare training dataset
    ds_train = ds_train.map(
        preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    if caching:
        ds_train = ds_train.cache()
    ds_train = ds_train.map(
        augment, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    ds_train = ds_train.shuffle(1000)
    # ds_train = ds_train.shuffle(ds_info.splits['train'].num_examples // 10)
    ds_train = ds_train.batch(batch_size)
    ds_train = ds_train.repeat(-1)
    ds_train = ds_train.prefetch(tf.data.experimental.AUTOTUNE)

    # Prepare validation dataset
    ds_val = ds_val.map(
        preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    ds_val = ds_val.batch(batch_size)
    if caching:
        ds_val = ds_val.cache()
    ds_val = ds_val.prefetch(tf.data.experimental.AUTOTUNE)

    # Prepare test dataset
    ds_test = ds_test.map(
        preprocess, num_parallel_calls=tf.data.experimental.AUTOTUNE)
    ds_test = ds_test.batch(103)
    if caching:
        ds_test = ds_test.cache()
    ds_test = ds_test.prefetch(tf.data.experimental.AUTOTUNE)

    return ds_train, ds_val, ds_test, ds_info
