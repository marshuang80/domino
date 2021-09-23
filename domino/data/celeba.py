import os
from functools import partial
from typing import List

import numpy as np
import pandas as pd
import torch
import torchvision.datasets.folder as folder
import torchvision.transforms as transforms
from meerkat import DataPanel, ImageColumn
from meerkat.contrib.celeba import build_celeba_df
from PIL import Image
from terra import Task

MASK_ATTRIBUTES = [
    "background",
    "skin",
    "nose",
    "eye_g",
    "l_eye",
    "r_eye",
    "l_brow",
    "r_brow",
    "l_ear",
    "r_ear",
    "mouth",
    "u_lip",
    "l_lip",
    "hair",
    "hat",
    "ear_r",
    "neck_l",
    "neck",
    "cloth",
]

PHRASE_TEMPLATES = [
    "a photo of a person {}",
    "a photo of a person {} [MASK]",
    "a photo of a person {} [MASK] [MASK]",
    "a photo of a person [MASK] {}",
    "a photo of a person [MASK] {} [MASK]",
    "a photo of a person [MASK] {} [MASK][MASK]",
    "a photo of a person [MASK] [MASK] {}",
    "a photo of a person [MASK] [MASK] {} [MASK]",
    "a photo of a person [MASK] [MASK] {} [MASK] [MASK]",
]


@Task
def get_celeba_dp(dataset_dir: str = "/home/common/datasets/celeba"):
    """Build the dataframe by joining on the attribute, split and identity CelebA CSVs."""
    df = build_celeba_df(dataset_dir=dataset_dir, save_csv=False)
    dp = DataPanel.from_pandas(df)
    dp["image"] = ImageColumn.from_filepaths(filepaths=dp["img_path"])
    return dp


@Task
def get_celeba_mask_dp(dataset_dir: str = "/home/common/datasets/celeba"):
    """Build the dataframe by joining on the attribute, split and identity CelebA CSVs."""
    df = build_celeba_mask_df(dataset_dir=dataset_dir)
    dp = DataPanel.from_pandas(df)
    dp["img"] = ImageColumn.from_filepaths(filepaths=dp["img_path"])
    dp["input"] = ImageColumn.from_filepaths(
        filepaths=dp["img_path"],
        transform=celeb_transform,
        loader=folder.default_loader,
    )

    for mask_attr in MASK_ATTRIBUTES:
        if f"{mask_attr}_mask_path" in dp.columns:
            dp[f"{mask_attr}_mask"] = ImageColumn.from_filepaths(
                filepaths=dp[f"{mask_attr}_mask_path"],
                transform=celeb_mask_transform,
                loader=celeb_mask_loader,
            )
    return dp


def celeb_mask_loader(filepath: str):
    if os.path.exists(filepath):
        return folder.default_loader(filepath)
    else:
        # some masks are missing
        return Image.new("RGB", (512, 512))


def celeb_mask_transform(img: Image.Image):
    transform = transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.Lambda(lambda x: torch.from_numpy(np.array(x))),
            transforms.Lambda(lambda x: x.max(dim=-1)[0] > 0),
        ]
    )
    return transform(img)


def build_celeba_mask_df(
    dataset_dir: str = "/home/common/datasets/celeba",
    run_dir: str = None,
):
    """Build the dataframe by joining on the attribute, split and identity CelebA CSVs."""
    celeb_df = build_celeba_df(dataset_dir=dataset_dir, save_csv=False)

    mask_dir = os.path.join(dataset_dir, "CelebAMask-HQ")
    mask_df = pd.read_csv(
        os.path.join(mask_dir, "CelebA-HQ-to-CelebA-mapping.txt"), delimiter=r"\s+"
    )[["idx", "orig_file"]]
    for mask_attr in MASK_ATTRIBUTES:
        mask_df[f"{mask_attr}_mask_path"] = mask_df.idx.apply(
            lambda idx: os.path.join(
                mask_dir,
                "CelebAMask-HQ-mask-anno",
                str(idx // 2000),
                f"{str(idx).zfill(5)}_{mask_attr}.png",
            )
        )
    celeb_df = celeb_df.merge(mask_df, left_on="file", right_on="orig_file")
    celeb_df["img_path"] = celeb_df.idx.apply(
        lambda x: os.path.join(dataset_dir, "CelebAMask-HQ/CelebA-HQ-img", f"{x}.jpg")
    )
    return celeb_df