import gin
import tensorflow as tf
import numpy as np
import tensorflow_addons as tfa
from tensorflow.keras.utils import to_categorical


@gin.configurable
def preprocess(feature, label):
    """Dataset preprocessing: Normalizing and resizing"""

    return feature, label
