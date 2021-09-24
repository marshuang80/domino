from typing import List

import meerkat as mk
import meerkat.contrib.mimic.gcs
import numpy as np
import ray
import terra
from ray import tune

from domino.data.mimic import get_mimic_dp, split_dp_preloaded
from domino.emb.clip import embed_images, embed_words, get_wiki_words
from domino.evaluate import run_sdms, score_sdm_explanations, score_sdms
from domino.sdm import MixtureModelSDM, SpotlightSDM
from domino.slices import collect_settings
from domino.train import score_settings, synthetic_score_settings, train_settings

NUM_GPUS = 1
NUM_CPUS = 8
# ray.init(num_gpus=NUM_GPUS, num_cpus=NUM_CPUS)

data_dp = get_mimic_dp(skip_terra_cache=False)

split = split_dp_preloaded(dp=data_dp, skip_terra_cache=False)

setting_dp = collect_settings(
    dataset="mimic",
    slice_category="correlation",
    data_dp=data_dp,
    num_corr=5,
    n=30_000,
    skip_terra_cache=False,
)

setting_dp = setting_dp.load()
setting_dp = setting_dp.lz[np.random.choice(len(setting_dp), 3)]

if True:
    setting_dp = synthetic_score_settings(
        setting_dp=setting_dp,
        data_dp=data_dp,
        split_dp=split,
        synthetic_kwargs={
            "sensitivity": 0.8,
            "slice_sensitivities": 0.4,
            "specificity": 0.8,
            "slice_specificities": 0.4,
        },
        skip_terra_cache=False,
    )
else:
    pass
    """
    setting_dp, _ = p.run(
        parent_tasks=["collect_settings"],
        task=train_settings,
        setting_dp=setting_dp,
        data_dp=data_dp,
        split_dp=split,
        model_config={},  # {"pretrained": False},
        batch_size=256,
        val_check_interval=50,
        max_epochs=15,
        ckpt_monitor="valid_auroc",
        num_cpus=NUM_CPUS,
        num_gpus=NUM_GPUS,
    )

    setting_dp, _ = p.run(
        parent_tasks=["train_settings"],
        task=score_settings,
        model_dp=setting_dp,
        layers={"layer4": "model.layer4"},
        batch_size=512,
        reduction_fns=["mean"],
        num_cpus=NUM_CPUS,
        num_gpus=NUM_GPUS,
        split=["test", "valid"],
    )
    """

emb_dp = embed_images(
    dp=data_dp,
    split_dp=split,
    splits=["valid", "test"],
    img_column="cxr_jpg_1024",
    num_workers=7,
    mmap=True,
    skip_terra_cache=False,
)

words_dp = get_wiki_words(top_k=10_000, eng_only=True, skip_terra_cache=False)
words_dp = embed_words(words_dp=words_dp, skip_terra_cache=False)
# words_dp = embed_words.out(6537).load()
# words_dp = words_dp.lz[:int(1e4)]

common_config = {
    "n_slices": 5,
    "emb": tune.grid_search([("clip", "emb")]),
}
setting_dp = run_sdms(
    setting_dp=setting_dp,
    id_column="dicom_id",
    emb_dp={
        "clip": emb_dp,  # terra.out(5145),
        # "imagenet": emb_dp,
        # "bit": terra.out(5796),
    },
    word_dp=words_dp,
    sdm_config=[
        # {
        #     "sdm_class": SpotlightSDM,
        #     "sdm_config": {
        #         "learning_rate": tune.grid_search([1e-2, 1e-3]),
        #         **common_config,
        #     },
        # },
        {
            "sdm_class": MixtureModelSDM,
            "sdm_config": {
                "weight_y_log_likelihood": tune.grid_search([1, 5, 10, 20]),
                **common_config,
            },
        },
    ],
    skip_terra_cache=False,
)


slices_df = score_sdms(setting_dp=setting_dp, skip_terra_cache=False)
slices_df = score_sdm_explanations(setting_dp=setting_dp, skip_terra_cache=False)
