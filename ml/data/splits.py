from typing import Dict, List, Tuple

import numpy as np


def create_scene_splits(
    scene_ids: List[str],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[str]]:
    """Splits full scenes across train, validation, and test sets."""
    rng = np.random.RandomState(seed)
    shuffled = scene_ids.copy()
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = max(1, int(round(n * train_ratio)))
    n_val = max(1, int(round(n * val_ratio))) if (n - n_train) >= 2 else (1 if n > 1 else 0)
    # Remaining for test
    train_scenes = shuffled[:n_train]
    val_scenes = shuffled[n_train : n_train + n_val]
    test_scenes = shuffled[n_train + n_val :]
    if not test_scenes and len(train_scenes) > 1:
        test_scenes = [train_scenes.pop()]

    return {"train": train_scenes, "val": val_scenes, "test": test_scenes}


def create_spatial_block_splits(
    height: int,
    width: int,
    buffer_gap: int = 11,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> Dict[str, Dict[str, int]]:
    """
    Partitions a single scene into spatially separated rectangular blocks with a buffer gap.
    Guarantees no spatial overlap or border proximity leakage.
    """
    # Divide along columns (x-axis)
    # Train | buffer | Val | buffer | Test
    total_effective_width = width - 2 * buffer_gap
    w_train = int(total_effective_width * train_ratio)
    w_val = int(total_effective_width * val_ratio)
    _w_test = total_effective_width - w_train - w_val

    splits = {
        "train": {"col_start": 0, "col_end": w_train, "row_start": 0, "row_end": height},
        "val": {
            "col_start": w_train + buffer_gap,
            "col_end": w_train + buffer_gap + w_val,
            "row_start": 0,
            "row_end": height,
        },
        "test": {
            "col_start": w_train + buffer_gap + w_val + buffer_gap,
            "col_end": width,
            "row_start": 0,
            "row_end": height,
        },
    }
    return splits


def assert_no_spatial_leakage(
    train_coords: List[Tuple[int, int]], test_coords: List[Tuple[int, int]], min_dist: float = 11.0
) -> None:
    """Verifies that no coordinate in test_coords is within min_dist of any coordinate in train_coords."""
    if not train_coords or not test_coords:
        return
    train_arr = np.array(train_coords)
    test_arr = np.array(test_coords)

    # Subsample if large for test speed
    if len(train_arr) > 500:
        idx_train = np.random.choice(len(train_arr), 500, replace=False)
        train_arr = train_arr[idx_train]
    if len(test_arr) > 500:
        idx_test = np.random.choice(len(test_arr), 500, replace=False)
        test_arr = test_arr[idx_test]

    diff = train_arr[:, None, :] - test_arr[None, :, :]  # (N_tr, N_te, 2)
    dist = np.sqrt(np.sum(diff**2, axis=-1))  # (N_tr, N_te)
    min_observed_dist = np.min(dist)
    if min_observed_dist < min_dist:
        raise AssertionError(
            f"Spatial leakage detected! Minimum distance between train and test is {min_observed_dist:.2f}px, "
            f"expected >= {min_dist}px."
        )
