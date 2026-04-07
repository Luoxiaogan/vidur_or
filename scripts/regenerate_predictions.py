#!/usr/bin/env python3
"""
Regenerate Vidur predictions and comparison results after adding new measurements.
"""

import sqlite3
import pandas as pd
import numpy as np

DB_PATH = 'outputs/validation_database/vidur_validation.db'


def regenerate_all():
    conn = sqlite3.connect(DB_PATH)

    # Get all real measurements
    df_real = pd.read_sql_query(
        "SELECT * FROM real_gpu_measurements ORDER BY batch_size",
        conn
    )

    print(f"Found {len(df_real)} real measurements")
    print(f"Regions: {df_real['region'].value_counts().to_dict()}")

    # Separate accurate region data for fitting
    accurate_data = df_real[df_real['region'].isin(['ACCURATE', 'ACCURATE_PLUS'])]

    # Refit linear model using only ACCURATE region
    z = np.polyfit(accurate_data['kv_cache_size'], accurate_data['mean_ms'], 1)
    d1, d0 = z[0], z[1]

    r_squared = 1 - np.sum((accurate_data['mean_ms'] - (d0 + d1 * accurate_data['kv_cache_size']))**2) / np.sum((accurate_data['mean_ms'] - accurate_data['mean_ms'].mean())**2)

    print(f"\n📊 Updated Linear Model (fitted on B≤128):")
    print(f"   τ = {d0:.2f} + {d1:.6f} × (KV-cache size)")
    print(f"   R² = {r_squared:.4f}")
    print(f"   Training samples: {len(accurate_data)}")

    # Recreate vidur_predictions table
    conn.execute('DROP TABLE IF EXISTS vidur_predictions')
    conn.execute('''
    CREATE TABLE vidur_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT,
        batch_size INTEGER,
        prefill_len INTEGER,
        decode_len INTEGER,
        kv_cache_size INTEGER,
        predicted_ms REAL,
        prediction_method TEXT,
        region TEXT,
        notes TEXT
    )
    ''')

    # Generate predictions for ALL batch sizes
    for _, row in df_real.iterrows():
        batch = int(row['batch_size'])
        kv_cache = int(row['kv_cache_size'])
        predicted = d0 + d1 * kv_cache

        region = row['region']

        conn.execute('''
        INSERT INTO vidur_predictions
        (model, batch_size, prefill_len, decode_len, kv_cache_size,
         predicted_ms, prediction_method, region, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Llama-2-7B', batch, int(row['prefill_len']), int(row['decode_len']),
              kv_cache, predicted, 'linear_model', region,
              'Updated model with extended validation data'))

    # Recreate comparison_results table
    conn.execute('DROP TABLE IF EXISTS comparison_results')
    conn.execute('''
    CREATE TABLE comparison_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT,
        batch_size INTEGER,
        prefill_len INTEGER,
        decode_len INTEGER,
        kv_cache_size INTEGER,
        real_ms REAL,
        predicted_ms REAL,
        error_ms REAL,
        error_percent REAL,
        abs_error_percent REAL,
        region TEXT,
        accuracy_assessment TEXT
    )
    ''')

    # Insert comparison results
    for _, row in df_real.iterrows():
        batch = int(row['batch_size'])
        prefill = int(row['prefill_len'])
        decode = int(row['decode_len'])

        # Get prediction for this specific configuration
        pred_row = pd.read_sql_query(
            f"SELECT predicted_ms FROM vidur_predictions WHERE batch_size={batch} AND prefill_len={prefill} AND decode_len={decode}",
            conn
        )

        if len(pred_row) == 0:
            continue

        pred_ms = pred_row.iloc[0]['predicted_ms']
        real_ms = row['mean_ms']
        error = real_ms - pred_ms
        error_percent = (error / real_ms) * 100
        abs_error = abs(error_percent)

        # Assessment based on region
        region = row['region']
        if region == 'ACCURATE':
            if abs_error < 5:
                assessment = 'EXCELLENT'
            elif abs_error < 10:
                assessment = 'GOOD'
            else:
                assessment = 'MODERATE'
        elif region == 'ACCURATE_PLUS':
            if abs_error < 10:
                assessment = 'GOOD'
            elif abs_error < 20:
                assessment = 'MODERATE'
            else:
                assessment = 'POOR'
        else:  # EXTRAPOLATION
            if abs_error < 20:
                assessment = 'MODERATE'
            elif abs_error < 50:
                assessment = 'POOR'
            else:
                assessment = 'VERY_POOR'

        conn.execute('''
        INSERT INTO comparison_results
        (model, batch_size, prefill_len, decode_len, kv_cache_size,
         real_ms, predicted_ms, error_ms, error_percent, abs_error_percent,
         region, accuracy_assessment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Llama-2-7B', batch, prefill, decode,
              int(row['kv_cache_size']), real_ms, pred_ms, error, error_percent,
              abs_error, region, assessment))

    conn.commit()

    # Statistics by region
    comparison = pd.read_sql_query('SELECT * FROM comparison_results', conn)

    print(f"\n📈 Comparison Results by Region:")
    for region in comparison['region'].unique():
        region_data = comparison[comparison['region'] == region]
        mape = region_data['abs_error_percent'].mean()
        max_err = region_data['abs_error_percent'].max()
        print(f"   {region}: {len(region_data)} samples, MAPE={mape:.2f}%, Max Error={max_err:.2f}%")

    # Export CSV
    df_export = pd.read_sql_query('''
        SELECT
            c.batch_size,
            c.kv_cache_size,
            c.prefill_len,
            c.decode_len,
            c.real_ms,
            c.predicted_ms,
            c.error_percent,
            c.abs_error_percent,
            c.region,
            c.accuracy_assessment,
            r.description as region_description
        FROM comparison_results c
        LEFT JOIN region_definitions r ON c.region = r.region_name
        ORDER BY c.batch_size, c.prefill_len
    ''', conn)

    df_export.to_csv('outputs/validation_database/validation_data_for_plotting.csv', index=False)

    print(f"\n✅ CSV exported with {len(df_export)} rows")
    print(f"   Location: outputs/validation_database/validation_data_for_plotting.csv")

    conn.close()

    return comparison


if __name__ == '__main__':
    print("="*80)
    print("Regenerating Vidur Predictions and Comparison Results")
    print("="*80)
    regenerate_all()
    print("="*80)
