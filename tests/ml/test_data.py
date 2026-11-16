import os
import shutil
import tempfile

import numpy as np
import pytest

from ml.data.pca import HSIPCATransformer
from ml.data.preprocess import get_bad_band_indices
from ml.data.readers import HSIReader
from ml.data.splits import assert_no_spatial_leakage
from ml.data.synth import generate_synthetic_scene, generate_wavelengths


@pytest.fixture(scope="session")
def temp_synth_scene():
    temp_dir = tempfile.mkdtemp()
    meta = generate_synthetic_scene(
        scene_id="test_scene",
        output_dir=temp_dir,
        height=32,
        width=32,
        bands=32,
        time_steps=2,
        seed=101,
        write_hdf5=True
    )
    yield temp_dir, meta
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_generator_determinism():
    """Verify same seed produces identical cube data."""
    t1 = tempfile.mkdtemp()
    t2 = tempfile.mkdtemp()
    try:
        generate_synthetic_scene("s1", t1, height=16, width=16, bands=16, time_steps=1, seed=999)
        generate_synthetic_scene("s2", t2, height=16, width=16, bands=16, time_steps=1, seed=999)

        r1 = HSIReader(os.path.join(t1, "t00.tif"))
        r2 = HSIReader(os.path.join(t2, "t00.tif"))

        d1, _ = r1.read_window(0, 0, 16, 16)
        d2, _ = r2.read_window(0, 0, 16, 16)

        assert np.array_equal(d1, d2), "Synthetic generator is not deterministic with same seed!"
    finally:
        shutil.rmtree(t1, ignore_errors=True)
        shutil.rmtree(t2, ignore_errors=True)

def test_readers_geotiff_and_hdf5(temp_synth_scene):
    temp_dir, meta = temp_synth_scene
    tif_path = os.path.join(temp_dir, "t00.tif")
    h5_path = os.path.join(temp_dir, "t00.h5")

    # GeoTIFF Windowed Read
    r_tif = HSIReader(tif_path)
    assert r_tif.width == 32
    assert r_tif.height == 32
    assert r_tif.bands == 32
    data_tif, mask_tif = r_tif.read_window(4, 4, 16, 16)
    assert data_tif.shape == (32, 16, 16)
    assert mask_tif.shape == (16, 16)

    # HDF5 Windowed Read
    r_h5 = HSIReader(h5_path)
    assert r_h5.width == 32
    assert r_h5.height == 32
    assert r_h5.bands == 32
    data_h5, mask_h5 = r_h5.read_window(4, 4, 16, 16)
    assert data_h5.shape == (32, 16, 16)
    assert np.allclose(data_tif, data_h5, atol=1e-4)

def test_bad_band_indices():
    wls = generate_wavelengths(bands=224, min_nm=400.0, max_nm=2500.0)
    good, bad = get_bad_band_indices(wls, edge_drop=4)
    assert len(good) + len(bad) == 224
    assert len(bad) > 8 # Edge drops + water vapor bands
    assert len(good) > 160

def test_no_spatial_leakage():
    # Coords that are separated by 20 px
    train_coords = [(10, 10), (12, 15)]
    test_coords = [(40, 40), (45, 50)]
    assert_no_spatial_leakage(train_coords, test_coords, min_dist=11.0)

    # Overlapping coords should trigger AssertionError
    leak_coords = [(15, 15)]
    with pytest.raises(AssertionError):
        assert_no_spatial_leakage(train_coords, leak_coords, min_dist=11.0)

def test_pca_variance_threshold():
    rng = np.random.RandomState(42)
    fake_pixels = rng.randn(1000, 32).astype(np.float32)
    pca = HSIPCATransformer(n_components=12, batch_size=256)
    report = pca.fit(fake_pixels)
    assert pca.is_fitted
    assert report["n_components"] == 12
    assert len(report["cumulative_variances"]) == 12

