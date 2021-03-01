#!/usr/bin/python
# -*- coding: utf-8 -*-

# Modified from https://gist.github.com/ageis/a0623ae6ec9cfc72e5cb6bde5754ab1f
# and https://github.com/jvstein/bitcoin-prometheus-exporter/blob/master/bitcoind-monitor.py
# requires pip install prometheus-client

import json
import time
import subprocess
import sys
from shutil import which

from prometheus_client import start_http_server, Gauge, Counter

# Create Prometheus metrics to track dogecoind stats.
DOGECOIN_BLOCKS = Gauge('dogecoin_blocks', 'Block height')
DOGECOIN_HEADERS = Gauge('dogecoin_headers', 'Number of synced headers')
DOGECOIN_SIZE_ON_DISK = Gauge('dogecoin_size_on_disk', 'Size of the Dogecoin blockchain on disk (blk and undo/rev files) in IEC bytes')
DOGECOIN_DIFFICULTY = Gauge('dogecoin_difficulty', 'Difficulty')
DOGECOIN_PEERS = Gauge('dogecoin_peers', 'Number of peers')
DOGECOIN_HASHPS = Gauge('dogecoin_hashps', 'Estimated network hash rate per second')

DOGECOIN_ERRORS = Counter('dogecoin_errors', 'Number of errors detected')
DOGECOIN_UPTIME = Gauge('dogecoin_uptime', 'Number of seconds the Bitcoin daemon has been running')

DOGECOIN_MEMPOOL_BYTES = Gauge('dogecoin_mempool_bytes', 'Size of mempool in bytes')
DOGECOIN_MEMPOOL_SIZE = Gauge('dogecoin_mempool_size', 'Number of unconfirmed transactions in mempool')

DOGECOIN_LATEST_BLOCK_SIZE = Gauge('dogecoin_latest_block_size', 'Size of latest block in bytes')
DOGECOIN_LATEST_BLOCK_TXS = Gauge('dogecoin_latest_block_txs', 'Number of transactions in latest block')

DOGECOIN_NUM_CHAINTIPS = Gauge('dogecoin_num_chaintips', 'Number of known blockchain branches')

DOGECOIN_TOTAL_BYTES_RECV = Gauge('dogecoin_total_bytes_recv', 'Total bytes received')
DOGECOIN_TOTAL_BYTES_SENT = Gauge('dogecoin_total_bytes_sent', 'Total bytes sent')

DOGECOIN_LATEST_BLOCK_INPUTS = Gauge('dogecoin_latest_block_inputs', 'Number of inputs in transactions of latest block')
DOGECOIN_LATEST_BLOCK_OUTPUTS = Gauge('dogecoin_latest_block_outputs', 'Number of outputs in transactions of latest block')

def find_dogecoin_cli():
    return which('dogecoin-cli')

DOGECOIN_CLI_PATH = str(find_dogecoin_cli())

def dogecoin(cmd):
    dogecoin = subprocess.Popen([DOGECOIN_CLI_PATH, cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = dogecoin.communicate()[0]
    return json.loads(output.decode('utf-8'))


def dogecoincli(cmd):
    dogecoin = subprocess.Popen([DOGECOIN_CLI_PATH, cmd], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    output = dogecoin.communicate()[0]
    return output.decode('utf-8')


def get_block(block_hash):
    try:
        block = subprocess.check_output([DOGECOIN_CLI_PATH, 'getblock', block_hash])
    except Exception as e:
        print(e)
        print('Error: Can\'t retrieve block with hash ' + block_hash + ' from dogecoind.')
        return None
    return json.loads(block.decode('utf-8'))


def get_raw_tx(txid):
    try:
        rawtx = subprocess.check_output([DOGECOIN_CLI_PATH, 'getrawtransaction', txid, '1'])
    except Exception as e:
        print(e)
        print('Error: Can\'t retrieve raw transaction ' + txid + ' from dogecoind.')
        return None
    return json.loads(rawtx.decode('utf-8'))


def refresh_metrics():
    info = dogecoin('getinfo')
    chaintips = len(dogecoin('getchaintips'))
    mempool = dogecoin('getmempoolinfo')
    nettotals = dogecoin('getnettotals')
    blockchaininfo = dogecoin('getblockchaininfo')
    latest_block = get_block(str(blockchaininfo['bestblockhash']))
    hashps = float(dogecoincli('getnetworkhashps'))

    DOGECOIN_BLOCKS.set(blockchaininfo['blocks'])
    DOGECOIN_HEADERS.set(blockchaininfo['headers'])
    DOGECOIN_SIZE_ON_DISK.set(blockchaininfo['size_on_disk'])  # Requires 1.14.3+
    DOGECOIN_PEERS.set(info['connections'])
    DOGECOIN_DIFFICULTY.set(info['difficulty'])
    DOGECOIN_HASHPS.set(hashps)

    if info['errors']:
        DOGECOIN_ERRORS.inc()

    DOGECOIN_NUM_CHAINTIPS.set(chaintips)

    DOGECOIN_MEMPOOL_BYTES.set(mempool['bytes'])
    DOGECOIN_MEMPOOL_SIZE.set(mempool['size'])

    DOGECOIN_TOTAL_BYTES_RECV.set(nettotals['totalbytesrecv'])
    DOGECOIN_TOTAL_BYTES_SENT.set(nettotals['totalbytessent'])

    if latest_block is not None:
        DOGECOIN_LATEST_BLOCK_SIZE.set(latest_block['size'])
        DOGECOIN_LATEST_BLOCK_TXS.set(len(latest_block['tx']))
        inputs, outputs = 0, 0
        # counting transaction inputs and outputs requires txindex=1
        # to be enabled, which may also necessitate reindex=1 in dogecoin.conf
        for tx in latest_block['tx']:

            rawtx = get_raw_tx(tx)
            if rawtx is not None:
                i = len(rawtx['vin'])
                inputs += i
                o = len(rawtx['vout'])
                outputs += o

        DOGECOIN_LATEST_BLOCK_INPUTS.set(inputs)
        DOGECOIN_LATEST_BLOCK_OUTPUTS.set(outputs)

def main():
    PORT = 8334
    TIMEOUT = 30  # Time between refreshes, in seconds

    # Start up the server to expose the metrics.
    start_http_server(PORT)
    print(f"Server started on port {PORT}.")
    while True:
        try:
            refresh_metrics()
        # Rare, but has been seen before, so make sure the server keeps running
        except TypeError as te:
            print(repr(te))

        time.sleep(TIMEOUT)

if __name__ == '__main__':
    main()
