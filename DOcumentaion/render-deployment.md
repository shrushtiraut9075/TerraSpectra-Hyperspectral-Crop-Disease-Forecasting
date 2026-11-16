# 🚀 Render Deployment Guide — TerraSpectra

This guide walks you through deploying **TerraSpectra** to [Render](https://render.com) using your GitHub repository:
`https://github.com/shrushtiraut9075/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting`

---

## 🏗️ Architecture on Render

TerraSpectra is configured for **Unified Full-Stack Deployment**:
- **Stage 1 (Node 20)**: Automatically compiles TypeScript and bundles the React 18 + Deck.gl 9 + MapLibre GIS dashboard into optimized static assets (`web/dist`).
- **Stage 2 (Python 3.11)**: Runs the FastAPI backend with GDAL and PyTorch CPU, serving the REST API under `/api/v1`, health monitoring at `/health`, and mounting the React GIS dashboard at `/`.
- **Zero CORS Configuration**: Because frontend and backend are served together on your Render domain (e.g. `https://teraraspectra.onrender.com`), there are zero CORS conflicts.
- **Render Free Tier Compatible**: Fits comfortably within Render's Free Web Service tier (512 MB RAM, 15-minute build limit).

---

## ⚡ Method 1: 1-Click Blueprint Deployment (Recommended)

Render Blueprints read the root `render.yaml` file and configure everything automatically.

1. Sign in to **[dashboard.render.com](https://dashboard.render.com/)** with your account (`shrushtiraut9075@gmail.com`).
2. Click **New +** (top right) and select **Blueprint**.
3. Connect your GitHub account and select repository:
   **`shrushtiraut9075/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting`**
4. Render will detect `render.yaml`.
5. Click **Apply**.
6. Render will build the multi-stage Docker container and deploy your live URL (e.g., `https://teraraspectra.onrender.com`).

---

## 🛠️ Method 2: Manual Web Service Setup on Render

If you prefer setting up via the Render Dashboard UI:

1. In Render Dashboard, click **New +** ➔ **Web Service**.
2. Select **Build and deploy from a Git repository** ➔ Click **Next**.
3. Choose **`shrushtiraut9075/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting`**.
4. Configure the service settings:
   - **Name**: `teraraspectra`
   - **Region**: `Oregon (US West)` (or closest to your users)
   - **Branch**: `main`
   - **Root Directory**: *(Leave blank)*
   - **Runtime**: **`Docker`**
   - **Dockerfile Path**: `./Dockerfile`
   - **Instance Type**: **`Free`**
5. Under **Advanced** ➔ **Environment Variables**:
   | Key | Value | Notes |
   |---|---|---|
   | `DATA_ROOT` | `data` | Working directory for rasters |
   | `ARTIFACTS_ROOT` | `artifacts` | PCA & evaluation reports |
   | `SQLITE_DB_PATH` | `data/teraraspectra.db` | Job & farm registration SQLite store |
6. Health Check Path:
   - Set **Health Check Path** to: `/health`
7. Click **Create Web Service**.

---

## 🌐 Verifying Your Live Deployment

Once the build finishes (typically ~2-3 minutes), Render will display a green checkmark **Live** with your public URL:

1. **GIS 3D Dashboard**:  
   Open `https://<your-subdomain>.onrender.com/`  
   *The interactive Deck.gl 3D satellite viewer, timeline slider, and farm registration modal will load instantly.*

2. **Backend Health Check**:  
   Open `https://<your-subdomain>.onrender.com/health`  
   Expected JSON response:
   ```json
   {
     "status": "ok",
     "gpu": false,
     "model_loaded": false,
     "version": "1.0.0"
   }
   ```

3. **Interactive Swagger Documentation**:  
   Open `https://<your-subdomain>.onrender.com/docs`  
   *Test any of the 15+ REST endpoints (`/api/v1/fields`, `/api/v1/scenes`, `/api/v1/timeline`, etc.) directly from your browser.*

---

## 💡 Render Free Tier Best Practices & Tips

- **Spin-Down on Inactivity**: Free Render web services spin down after 15 minutes of inactivity. The first request after spin-down may take ~30–50 seconds to warm up. Once awake, response times are sub-second.
- **Automatic Redeployments**: Any commit pushed to the `main` branch of `shrushtiraut9075/TerraSpectra-Hyperspectral-Crop-Disease-Forecasting` will trigger an automated zero-downtime rolling build on Render.
