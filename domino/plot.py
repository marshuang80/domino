SDM_PALETTE = {
    "domino.sdm.george.GeorgeSDM": "#9CBDE8",
    "domino.sdm.multiaccuracy.MultiaccuracySDM": "#EFAB79",
    "domino.sdm.spotlight.SpotlightSDM": "#1B6C7B",
    "domino.sdm.confusion.ConfusionSDM": "#19416E",
    "domino.sdm.gmm.MixtureModelSDM": "#53B7AE",
}
PALETTE = ["#9CBDE8", "#53B7AE", "#EFAB79", "#E27E51", "#19416E", "#1B6C7B"]


def coherence_metric(grouped_df):
    return (grouped_df["auroc"] > 0.85) & (grouped_df["precision_at_10"] > 0.5)


EMB_PALETTE = {
    "random": "#19416E",
    "bit": "#1B6C7B",
    "clip": "#E27E51",
    # "mimic_multimodal": "#9CBDE8",
}


def generate_group_df(run_sdms_id, score_sdms_id, slice_type):
    setting_dp = run_sdms.out(run_sdms_id).load()
    slice_df = score_sdms.out(score_sdms_id).load()
    slice_df = pd.DataFrame(slice_df)
    score_dp = mk.DataPanel.from_pandas(slice_df)
    results_dp = mk.merge(
        score_dp,
        setting_dp["config/sdm", "alpha", "run_sdm_run_id", "sdm_class"],
        on="run_sdm_run_id",
    )
    emb_col = results_dp["config/sdm"].map(lambda x: x["sdm_config"]["emb"][0])
    results_dp["emb_type"] = emb_col

    results_df = results_dp.to_pandas()
    grouped_df = results_df.iloc[
        results_df.reset_index()
        .groupby(["slice_name", "slice_idx", "sdm_class", "alpha", "emb_type"])["auroc"]
        .idxmax()
        .astype(int)
    ]
    grouped_df = grouped_df[grouped_df["emb_type"] != "mimic_imageonly"]
    grouped_df["alpha"] = grouped_df["alpha"].round(3)

    if slice_type == "correlation":
        grouped_df = grouped_df[grouped_df["alpha"] != 0.0]
    grouped_df["success"] = coherence_metric(grouped_df)
    grouped_df["slice_type"] = [slice_type] * len(grouped_df)
    return grouped_df
