#!/usr/bin/env bash
# ==============================================================================
# hdfs_ingest.sh - Big Data Hadoop HDFS Ingestion & Cluster Job Execution
# ==============================================================================

set -e

HADOOP_HOME=${HADOOP_HOME:-"/usr/local/hadoop"}
HDFS_RAW_DIR="/user/hadoop/stock_analytics/raw"
HDFS_OUTPUT_DIR="/user/hadoop/stock_analytics/processed"
LOCAL_DATASET_DIR="../../dataset"

echo "=========================================================="
echo "    Big Data Hadoop Pipeline - Stock Analytics Ingest"
echo "=========================================================="

echo "[1] Creating HDFS Cluster directories..."
hdfs dfs -mkdir -p ${HDFS_RAW_DIR} || echo "HDFS directory ready"
hdfs dfs -mkdir -p /user/hadoop/stock_analytics/checkpoints || true

echo "[2] Uploading Multi-Year Historical Stock Dataset to HDFS Cluster..."
hdfs dfs -put -f ${LOCAL_DATASET_DIR}/historical_stocks_raw.csv ${HDFS_RAW_DIR}/

echo "[3] Verifying HDFS Cluster Ingestion & Block Replication..."
hdfs dfs -ls -h ${HDFS_RAW_DIR}/

echo "[4] Executing Hadoop Distributed MapReduce Streaming Job..."
# Clean previous output
hdfs dfs -rm -r -f ${HDFS_OUTPUT_DIR} || true

hadoop jar ${HADOOP_HOME}/share/hadoop/tools/lib/hadoop-streaming-*.jar \
    -files mapper.py,reducer.py \
    -mapper "python3 mapper.py" \
    -reducer "python3 reducer.py" \
    -input ${HDFS_RAW_DIR}/historical_stocks_raw.csv \
    -output ${HDFS_OUTPUT_DIR} \
    -numReduceTasks 4

echo "[5] Job Complete! Previewing Output from HDFS Cluster:"
hdfs dfs -cat ${HDFS_OUTPUT_DIR}/part-00000 | head -n 25

echo "=========================================================="
echo "    Hadoop Job Finished. Results available in HDFS."
echo "=========================================================="
