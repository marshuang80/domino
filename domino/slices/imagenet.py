from itertools import combinations
from typing import Collection, Dict, Iterable, List, Mapping, Sequence, Union

import meerkat as mk
import numpy as np
import pandas as pd
import terra
from meerkat.contrib.gqa import read_gqa_dps
from nltk.corpus import wordnet as wn
from torchvision import transforms
from tqdm import tqdm

from domino.data.gqa import ATTRIBUTE_GROUPS, DATASET_DIR, split_gqa
from domino.slices.abstract import AbstractSliceBuilder

from . import CorrelationImpossibleError, induce_correlation, synthesize_preds


def _get_hypernyms(data_dp: mk.DataPanel):
    synsets = set(data_dp["synset"].unique())
    hypernyms = []
    for synset in synsets:
        synset = wn.synset(synset)
        for hypernym in synset.closure(lambda s: s.hypernyms()):
            hypernyms.append(
                {
                    "synset": synset.name(),
                    "hypernym": hypernym.name(),
                }
            )
    df = pd.DataFrame(hypernyms)
    return df


class ImageNetSliceBuilder(AbstractSliceBuilder):
    def build_rare_slice(
        self,
        data_dp: mk.DataPanel,
        target_synset: str,
        slice_synsets: Union[str, Iterable[str]],
        slice_frac: float,
        target_frac: float,
        n: int,
        **kwargs,
    ):
        data_dp = data_dp.view()
        hypernyms = _get_hypernyms(data_dp=data_dp)
        target_synsets = hypernyms["synset"][hypernyms["hypernym"] == target_synset]

        data_dp["target"] = data_dp["synset"].isin(target_synsets).astype(int).values

        if isinstance(slice_synsets, str):
            slice_synsets = [slice_synsets]

        n_slices = len(slice_synsets)
        slices = np.zeros((len(data_dp), n_slices))
        for slice_idx, slice_synset in enumerate(slice_synsets):
            slices[:, slice_idx] = (data_dp["synset"] == slice_synset).astype(int)
        data_dp["slices"] = slices

        data_dp["input"] = data_dp["image"]
        data_dp["id"] = data_dp["image_id"]

        n_pos = int(n * target_frac)
        dp = data_dp.lz[
            np.random.permutation(
                np.concatenate(
                    (
                        *(
                            np.random.choice(
                                np.where(data_dp["slices"][:, slice_idx] == 1)[0],
                                int(slice_frac * n_pos),
                                replace=False,
                            )
                            for slice_idx in range(n_slices)
                        ),
                        np.random.choice(
                            np.where(
                                (data_dp["target"] == 1)
                                & (data_dp["slices"].sum(axis=1) == 0)
                            )[0],
                            int((1 - n_slices * slice_frac) * n_pos),
                            replace=False,
                        ),
                        np.random.choice(
                            np.where(data_dp["target"] == 0)[0],
                            n - n_pos,
                            replace=False,
                        ),
                    )
                )
            )
        ]
        return dp

    def build_correlation_slices(self):
        raise NotImplementedError

    def build_noisy_label_slices(self):
        raise NotImplementedError

    def buid_noisy_feature_slices(self):
        raise NotImplementedError


@terra.Task
def collect_correlation_slices(
    dataset_dir: str = DATASET_DIR,
    min_dataset_size: int = 40_000,
    max_n: int = 50_000,
    min_corr: float = 0,
    max_corr: float = 0.8,
    num_corr: int = 5,
    subsample_frac: float = 0.3,
    count_threshold_frac: float = 0.002,
    run_dir: str = None,
):
    dps = read_gqa_dps(dataset_dir=dataset_dir)
    attr_dp, object_dp = dps["attributes"], dps["objects"]
    attr_dp = attr_dp.merge(object_dp[["object_id", "name"]], on="object_id")
    # attribute -> correlate, object -> target
    results = []
    for group_name, group in ATTRIBUTE_GROUPS.items():
        # get all objects for which at least one attribute in the group is annotated
        curr_attr_dp = attr_dp.lz[attr_dp["attribute"].isin(group)]
        curr_object_dp = object_dp.lz[
            np.isin(object_dp["object_id"], curr_attr_dp["object_id"])
        ]

        if len(curr_attr_dp) < min_dataset_size:
            continue

        df = curr_attr_dp[["attribute", "name"]].to_pandas()
        df = df[df["name"] != ""]  # filter out objects w/o name

        # only consider attribute-object pairs that have a prevalence above some
        # fraction of the entire dataset
        counts = df.value_counts()
        df = counts[counts > len(curr_attr_dp) * count_threshold_frac].reset_index()

        for attribute, name in tqdm(list(zip(df["attribute"], df["name"]))):
            dp = curr_object_dp.view()
            dp["target"] = (dp["name"] == name).values.astype(int)
            dp["correlate"] = np.isin(
                dp["object_id"],
                curr_attr_dp["object_id"][curr_attr_dp["attribute"] == attribute],
            ).astype(int)
            try:
                n = min(int(len(dp) * subsample_frac), max_n)
                for corr in [
                    min_corr,
                    max_corr,
                ]:
                    _ = induce_correlation(
                        dp=dp,
                        corr=corr,
                        attr_a="target",
                        attr_b="correlate",
                        match_mu=True,
                        n=n,
                    )

                results.extend(
                    [
                        {
                            "correlate": attribute,
                            "target": name,
                            "group": group_name,
                            "corr": corr,
                            "n": n,
                        }
                        for corr in np.linspace(min_corr, max_corr, num_corr)
                    ]
                )
            except CorrelationImpossibleError:
                pass
    return mk.DataPanel(results)

    # object -> correlate, object -> target