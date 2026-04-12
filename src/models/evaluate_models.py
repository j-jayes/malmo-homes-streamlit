"""Model benchmarking and hyperparameter tuning configurations.

Defines algorithms (ElasticNet, Random Forest, LightGBM, CatBoost)
and runs HalvingRandomSearchCV along with training/inference timings.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Protocol

import catboost as cb
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.experimental import enable_halving_search_cv  # noqa: F401
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import HalvingRandomSearchCV

logger = logging.getLogger(__name__)

def get_model_configs(random_state: int = 42) -> dict[str, dict[str, Any]]:
    """Get the base estimators and parameter grids for tuning."""
    return {
        "ElasticNet": {
            "estimator": ElasticNet(random_state=random_state, max_iter=2000),
            "param_grid": {
                "alpha": [0.01, 0.1, 1.0, 10.0, 100.0],
                "l1_ratio": [0.1, 0.5, 0.7, 0.9, 0.99, 1.0],
            },
        },
        "RandomForest": {
            "estimator": RandomForestRegressor(random_state=random_state, n_jobs=-1),
            "param_grid": {
                "n_estimators": [50, 100, 200, 300],
                "max_depth": [5, 10, 15, 20, None],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            },
        },
        "LightGBM": {
            "estimator": lgb.LGBMRegressor(random_state=random_state, verbose=-1, n_jobs=-1),
            "param_grid": {
                "n_estimators": [100, 300, 500, 1000],
                "learning_rate": [0.01, 0.05, 0.1],
                "max_depth": [4, 6, 8, 12],
                "num_leaves": [15, 31, 63, 127],
                "subsample": [0.6, 0.8, 1.0],
                "colsample_bytree": [0.6, 0.8, 1.0],
            },
        },
        "CatBoost": {
            "estimator": cb.CatBoostRegressor(
                random_state=random_state, verbose=False, thread_count=-1
            ),
            "param_grid": {
                "iterations": [100, 300, 500, 1000],
                "learning_rate": [0.01, 0.05, 0.1, 0.2],
                "depth": [4, 6, 8, 10],
                "l2_leaf_reg": [1, 3, 5, 10],
                "subsample": [0.6, 0.8, 1.0],
            },
        },
    }

def evaluate_model(
    name: str,
    estimator: Any,
    param_grid: dict[str, list[Any]],
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    random_state: int = 42,
    cv_folds: int = 5,
) -> dict[str, Any]:
    """Tune, train, and evaluate a single model.
    Returns metrics, training/inference time, feature importances, and best estimator.
    """
    logger.info(f"Starting tuning and evaluation for {name}")
    
    # 1. Hyperparameter Tuning
    search = HalvingRandomSearchCV(
        estimator=estimator,
        param_distributions=param_grid,
        scoring="neg_mean_absolute_error",
        cv=cv_folds,
        random_state=random_state,
        n_jobs=-1,
        factor=3,
        verbose=0
    )
    
    start_train = time.perf_counter()
    search.fit(X_train, y_train)
    end_train = time.perf_counter()
    train_time = end_train - start_train
    
    best_model = search.best_estimator_
    
    # 2. Inference
    start_infer = time.perf_counter()
    preds = best_model.predict(X_test)
    end_infer = time.perf_counter()
    
    infer_time = end_infer - start_infer
    infer_time_per_sample = infer_time / len(X_test)

    # 3. Evaluation
    mae = mean_absolute_error(y_test, preds)
    mape = mean_absolute_percentage_error(y_test, preds) * 100
    r2 = r2_score(y_test, preds)
    
    # 4. Feature Importances
    importances = None
    if hasattr(best_model, "feature_importances_"):
        importances = dict(zip(X_train.columns, best_model.feature_importances_))
    elif hasattr(best_model, "coef_"):
        importances = dict(zip(X_train.columns, np.abs(best_model.coef_)))
        
    logger.info(f"{name} Results: MAE={mae:.0f}, R2={r2:.3f}, MAPE={mape:.1f}%")
    
    return {
        "model_name": name,
        "best_params": search.best_params_,
        "mae": mae,
        "mape": mape,
        "r2": r2,
        "train_time_sec": train_time,
        "infer_time_sec": infer_time,
        "infer_time_per_1k_ms": infer_time_per_sample * 1000 * 1000,
        "feature_importances": importances,
        "best_estimator": best_model,
        "test_predictions": preds,
    }
