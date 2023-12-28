"""Preparation (handling preprocessing) of data for the Tornado module."""
import logging

import abc
import six
import numpy as np
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from statsmodels.stats.outliers_influence import variance_inflation_factor
from itertools import combinations
from .preprocess import Preprocess
from typing import Tuple


_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt="%(message)s"))
handler.terminator = ""
_logger.addHandler(handler)


# @six.add_metaclass(abc.ABCMeta)
class TornadoDataModule():
    """
    TornadoDataModule is a class that handles data preprocessing.

    This class accepts the file path of a dataset and returns preprocessed
    training and validation data.

    By default, it automatically applies multiple preprocessing steps to each
    feature, creating new feature columns. Subsequently, it reduces features
    based on the values of VIF (Variance Inflation Factor), a measure of
    multicollinearity.

    The history of preprocessing is output as a pickle file. If the path of
    this output file is provided as an argument, the same preprocessing can be
    replicated.

    Parameters
    ----------
    path: str
        The path to the data. The dataset is generated by loading from this
        location. Accepts either a csv or xlsx file.

    save_dir: str
        The path where the generated dataset should be saved. Defaults to None.
        Accepts either a csv or xlsx file.

    auto_preprocess: bool
        Whether to execute automatic preprocessing. Defaults to True.
        Set to False if using a dataset that has already been preprocessed.

    log_path: str
        The path to the preprocessing history file. Defaults to None.
        If None, the same path as the dataset will be set. If there is a
        pickle file at this path, it will be loaded and the preprocessing
        according to it will be replicated. If no file is present, automatic
        preprocessing will be performed and the history will be saved to this
        path.

    params: dict
        A dictionary of special options for various feature engineering
        procedures that are performed as preprocessing. Defaults to {}. The
        contents of the dictionary should have feature engineering process
        names as keys and options as values.

    Notes
    -----
    The `params` dictionary provided to the fifth argument should have feature
    engineering process names as keys and options as values.
    These options should be provided as dictionaries with option names as keys
    and the values for each option as values.

    Example:
        params =
            {"clipping": {"q_l": 0.10, "q_u": 0.90},
            "label_encoding": {"unknown_value": 0}}

    For details on what options are available for each technique, refer to the
    `Preprocess` class in preprocess.py.

    Attributes
    ----------
    train: pandas.DataFrame
        The data used for training.

    valid: pandas.DataFrame
        The data used for validation.

    target: str
        The name of the target variable.

    is_time_series: bool
        Indicates whether the data is time series data or not.

    """

    def __init__(self, path, save_dir=None, auto_preprocess=True,
                 log_path=None, params={}) -> None:
        super().__init__()
        self.path_ds = path
        self.save_dir = save_dir
        self.auto_preprocess = auto_preprocess
        self.log_path = log_path
        self.params = params
        self.train = None
        self.valid = None
        self.target = None
        self.is_time_series = True
        self.set_log()

    def set_log(self) -> None:
        if self.log_path:
            try:
                with open(self.log_path, "rb") as p:
                    log = pickle.load(p)
                    self.preprocessors = log["preprocessors"]
                    self.features = log["features"]
            except FileNotFoundError:
                self.preprocessors = {}
                self.features = []
        else:
            self.log_path = self.path_ds[:self.path_ds.rfind(".")] + ".pickle"
            self.preprocessors = {}
            self.features = []

    def corr_based_removal(self) -> None:
        dataset = pd.concat([self.train.copy(), self.valid.copy()])
        try:
            dataset = dataset.drop(columns=["date"])
            has_date = True
        except KeyError:
            has_date = False

        corr_rl = 0.1
        corr_ul = 0.9
        corr = dataset.corr()
        features = corr.index

        for feature in features:
            if (abs(corr.loc[feature, self.target]) < corr_rl):
                features = features.drop(feature)

        droped_features = []
        for feature1, feature2 in combinations(features.drop(self.target), 2):
            if (abs(corr.loc[feature1, feature2]) > corr_ul):
                if not set([feature1, feature2]) & set(droped_features):
                    feature = corr.loc[[feature1, feature2], self.target].abs().idxmin()
                    features = features.drop(feature)
                    droped_features.append(feature)
        dataset = dataset[features]

        if has_date:
            self.train = self.train.loc[:, dataset.columns.tolist() + ["date"]]
            self.valid = self.valid.loc[:, dataset.columns.tolist() + ["date"]]

    def vif_based_removal(self) -> None:
        dataset = pd.concat([self.train.copy(), self.valid.copy()])
        try:
            dataset = dataset.drop(columns=["date"])
            has_date = True
        except KeyError:
            has_date = False
        dataset = dataset.drop(columns=[self.target])
        dataset = dataset.astype("float").dropna()

        c = 10
        vif_max = c
        while vif_max >= c:
            vif = pd.DataFrame()
            with np.errstate(divide="ignore"):
                vif["VIF Factor"] = [variance_inflation_factor(dataset.values, i)
                                     for i in range(dataset.shape[1])]
            vif["features"] = dataset.columns
            vif_max_idx = vif["VIF Factor"].idxmax()
            vif_max = vif["VIF Factor"].max()
            if vif_max >= c:
                dataset.drop(columns=vif["features"][vif_max_idx],
                             inplace=True)
                vif_max = vif["VIF Factor"].drop(vif_max_idx).max()

        if has_date:
            self.train = self.train.loc[:, dataset.columns.tolist() + ["date", self.target]]
            self.valid = self.valid.loc[:, dataset.columns.tolist() + ["date", self.target]]
        else:
            self.train = self.train.loc[:, dataset.columns.tolist() + [self.target]]
            self.valid = self.valid.loc[:, dataset.columns.tolist() + [self.target]]

    def remove_features(self) -> None:
        if not self.features:
            self.vif_based_removal()
            self.features = self.train.columns.tolist()
        else:
            self.train = self.train.loc[:, self.features]
            self.valid = self.valid.loc[:, self.features]

    def generate(self, target, is_time_series, test_size, seed) -> Tuple[pd.DataFrame, pd.DataFrame]:
        self.target = target
        self.is_time_series = is_time_series

        preprocess = Preprocess(self.params)
        dataset = preprocess.load_dataset(self.path_ds)

        if self.auto_preprocess:
            n_features_original = len(dataset.columns) - 1
            _logger.info(f"\rn_features: {n_features_original} ->")

            if self.preprocessors:
                preprocess.set_preprocessors(self.preprocessors)
            else:
                preprocess.check_data(dataset, self.is_time_series)

            self.train, self.valid = train_test_split(
                dataset,
                test_size=test_size,
                random_state=seed)

            self.train, self.valid = preprocess.apply(self.train,
                                                      self.valid,
                                                      self.target)

            n_features_preprocessed = len(self.train.columns) - 1
            _logger.info(f"\rn_features: {n_features_original} -> "
                         f"{n_features_preprocessed} ->")

            self.remove_features()

            n_features_selected = len(self.features) - 1
            _logger.info(f"\rn_features: {n_features_original} -> "
                         f"{n_features_preprocessed} -> "
                         f"{n_features_selected}\n")
            _logger.info(f"{self.features}\n")

            self.preprocessors = preprocess.get_preprocessors()
            with open(self.log_path, "wb") as p:
                log = {"preprocessors": self.preprocessors,
                       "features": self.features}
                pickle.dump(log, p)

        else:
            self.train, self.valid = train_test_split(
                dataset,
                test_size=test_size,
                random_state=seed)

            if self.is_time_series:
                self.preprocessors["todatetime"] = {}
                preprocess.set_preprocessors(self.preprocessors)
                self.train, self.valid = preprocess.apply(self.train,
                                                          self.valid,
                                                          self.target)

        return self.train, self.valid
