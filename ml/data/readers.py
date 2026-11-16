import os
from typing import Tuple, Dict, Any, Optional
import numpy as np
import rasterio
from rasterio.windows import Window
import h5py

class HSIReader:
    """Windowed reader for hyperspectral rasters (GeoTIFF and HDF5) with validation."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        self.ext = os.path.splitext(file_path)[1].lower()
        if self.ext not in [".tif", ".tiff", ".h5", ".hdf5"]:
            raise ValueError(f"Unsupported raster format: {self.ext}")

        self._validate_and_cache_metadata()

    def _validate_and_cache_metadata(self) -> None:
        if self.ext in [".tif", ".tiff"]:
            with rasterio.open(self.file_path) as src:
                if src.crs is None:
                    raise ValueError(f"Raster {self.file_path} is missing CRS metadata.")
                self.width: int = src.width
                self.height: int = src.height
                self.bands: int = src.count
                self.crs: str = str(src.crs)
                self.transform = src.transform
                self.nodata = src.nodata
                self.dtype = src.dtypes[0]
        else: # HDF5
            with h5py.File(self.file_path, "r") as hf:
                if "cube" not in hf:
                    raise ValueError(f"HDF5 {self.file_path} missing 'cube' dataset.")
                dset = hf["cube"]
                # Expected shape (H, W, B) or (B, H, W)
                shape = dset.shape
                if len(shape) != 3:
                    raise ValueError(f"Expected 3D dataset in {self.file_path}, got {shape}")
                # We check attribute or standard spatial chunking (H, W, B)
                layout = hf.attrs.get("layout", "")
                if layout == "HWB" or shape[2] >= shape[0]: # (H, W, B)
                    self.height, self.width, self.bands = shape[0], shape[1], shape[2]
                    self.hdf5_channel_last = True
                else:
                    self.bands, self.height, self.width = shape[0], shape[1], shape[2]
                    self.hdf5_channel_last = False

                self.crs = hf.attrs.get("crs", "EPSG:32643")
                self.nodata = hf.attrs.get("nodata", -9999.0)
                self.dtype = str(dset.dtype)
                self.transform = None

    def read_window(
        self,
        col_off: int,
        row_off: int,
        width: int,
        height: int,
        band_indices: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Reads a spatial window without ever loading the full cube.
        Returns:
            data: np.ndarray shape (B_sel, height, width) float32
            mask: np.ndarray shape (height, width) bool (True = valid, False = nodata/NaN)
        """
        # Ensure window is clamped to bounds
        col_end = min(self.width, col_off + width)
        row_end = min(self.height, row_off + height)
        actual_w = max(0, col_end - col_off)
        actual_h = max(0, row_end - row_off)

        if actual_w == 0 or actual_h == 0:
            raise ValueError(f"Window ({col_off}, {row_off}, {width}, {height}) is out of bounds.")

        if self.ext in [".tif", ".tiff"]:
            with rasterio.open(self.file_path) as src:
                window = Window(col_off, row_off, actual_w, actual_h)
                if band_indices is not None:
                    # rasterio 1-based indexes
                    b_list = [int(idx) + 1 for idx in band_indices]
                    arr = src.read(b_list, window=window)
                else:
                    arr = src.read(window=window)
        else: # HDF5
            with h5py.File(self.file_path, "r") as hf:
                dset = hf["cube"]
                if self.hdf5_channel_last:
                    # Slicing chunked array: [row_off:row_end, col_off:col_end, :]
                    if band_indices is not None:
                        slice_data = dset[row_off:row_end, col_off:col_end, :]
                        arr = np.transpose(slice_data[:, :, band_indices], (2, 0, 1))
                    else:
                        slice_data = dset[row_off:row_end, col_off:col_end, :]
                        arr = np.transpose(slice_data, (2, 0, 1))
                else:
                    if band_indices is not None:
                        arr = dset[band_indices, row_off:row_end, col_off:col_end]
                    else:
                        arr = dset[:, row_off:row_end, col_off:col_end]

        arr = arr.astype(np.float32)

        # Pad to requested width/height if at boundary
        if actual_w != width or actual_h != height:
            padded_arr = np.full((arr.shape[0], height, width), fill_value=np.nan, dtype=np.float32)
            padded_arr[:, :actual_h, :actual_w] = arr
            arr = padded_arr

        # Determine nodata mask (True = valid pixel)
        mask = ~np.isnan(arr).any(axis=0)
        if self.nodata is not None:
            mask = mask & ~(arr == self.nodata).any(axis=0)

        return arr, mask