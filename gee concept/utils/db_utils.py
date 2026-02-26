import mysql.connector
import json
import hashlib
import streamlit as st


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="heritage_monitor"
    )


def generate_params_hash(config):
    """Generate unique code based on parameters"""
    hash_input = f"{config['site_name']}_{config['center_lat']}_{config['center_lon']}_{config['buffer_km']}_{config['start_date']}_{config['end_date']}_{config['cloud_cover']}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def save_analysis_to_db(config, stats):
    conn = get_db_connection()
    cursor = conn.cursor()
    params_hash = generate_params_hash(config)

    query = """
    INSERT INTO sites_history (site_name, latitude, longitude, buffer_km, start_date, end_date, cloud_cover, stats_json, params_hash)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE analysis_date = CURRENT_TIMESTAMP
    """
    values = (
        config['site_name'], config['center_lat'], config['center_lon'],
        config['buffer_km'], config['start_date'], config['end_date'],
        config['cloud_cover'], json.dumps(stats), params_hash
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()


def get_analysis_from_db(config):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    params_hash = generate_params_hash(config)

    cursor.execute("SELECT stats_json FROM sites_history WHERE params_hash = %s", (params_hash,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return json.loads(result['stats_json']) if result else None