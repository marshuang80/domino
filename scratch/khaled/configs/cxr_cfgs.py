from configs.generate import flag, prod


def erm_sweep():

    sweep = prod(
        [
            flag("train.wd", [0, 1e-5, 1e-3, 1e-1]),
            flag("train.loss.gdro", [False]),
            flag("dataset.subgroup_columns", [["chest_tube"]]),
            flag("train.gaze_split", [True]),
        ]
    )

    return sweep


def gdro_sweep():

    sweep = prod(
        [
            flag("train.wd", [0, 1e-5, 1e-3, 1e-1]),
            flag("train.loss.gdro", [True]),
            flag("dataset.subgroup_columns", [["chest_tube"]]),
            flag("train.gaze_split", [True]),
        ]
    )

    return sweep


def multiclass_sweep():

    sweep = prod(
        [
            flag("train.wd", [0, 1e-5, 1e-3, 1e-1]),
            flag("train.multiclass", [True]),
            flag("train.loss.reweight_class", [True]),
            flag("train.loss.reweight_class_alpha", [1, 2, 4]),
            flag("train.gaze_split", [True]),
            flag("dataset.subgroup_columns", [["chest_tube"]]),
        ]
    )

    return sweep


def cnc_sweep():

    sweep = prod(
        [
            flag("train.wd", [1e-1]),
            flag("train.cnc", [True]),
            flag("train.cnc_config.contrastive_weight", [0.75, 0.9]),
            flag(
                "train.cnc_config.contrastive_dp_pth",
                ["/media/4tb_hdd/siim/contrastive_dp_na_-1_np_32_nn_32.dp"],
            ),
            flag("train.gaze_split", [True]),
            flag("dataset.subgroup_columns", [["chest_tube"]]),
            flag("train.epochs", [1]),
        ]
    )

    return sweep


def upsampling_sweep():

    sweep = prod(
        [
            flag("train.wd", [0, 1e-5, 1e-3, 1e-1]),
            flag("train.loss.robust_sampler", [True]),
            flag("train.loss.reweight_class_alpha", [1, 2, 4]),
            flag("train.gaze_split", [True]),
            flag("dataset.subgroup_columns", [["chest_tube"]]),
        ]
    )

    return sweep


def scribble_sweep():

    sweep = prod(
        [
            flag("train.wd", [1e-5, 1e-3, 1e-1]),
            flag("train.loss.gdro", [True, False]),
            flag(
                "dataset.datapanel_pth",
                ["/media/4tb_hdd/siim/tubescribble_dp_07-24-21.dp"],
            ),
            flag("dataset.subgroup_columns", [["tube"]]),
        ]
    )

    return sweep


def gazeslicer_time_sweep():

    sweep = prod(
        [
            flag("train.wd", [1e-5, 1e-3, 1e-1]),
            flag("train.loss.gdro", [True, False]),
            flag(
                "dataset.datapanel_pth",
                ["/media/4tb_hdd/siim/gazeslicer_dp_07-23-21.dp"],
            ),
            flag("dataset.subgroup_columns", [["gazeslicer_time"]]),
        ]
    )

    return sweep


def tubeclassification_sweep():

    sweep = prod(
        [
            flag("train.epochs", [150]),
            flag("train.lr", [5e-4, 1e-3]),
            flag("train.wd", [1e-6, 1e-5]),
            flag("train.gaze_split", [True]),
            flag(
                "dataset.datapanel_pth",
                ["/media/4tb_hdd/siim/tubescribble_dp_07-24-21.dp"],
            ),
            flag("dataset.target_column", ["chest_tube"]),
        ]
    )

    return sweep