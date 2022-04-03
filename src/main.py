import datetime
import json
import os

import requests

MULT = 1000000000000
NT_HOUR_START = datetime.time(20, 0, 0)
NT_HOUR_END = datetime.time(21, 10, 0)
LOG_FILE = 'f2pool.log'
CONFIG_FILE = 'test_config.json'


def write_log(msg):
    exec_time = datetime.datetime.now()
    with open(LOG_FILE, mode='a', encoding='utf-8') as fdesc:
        fdesc.write(f'{exec_time.strftime("%Y-%m-%d, %H:%M:%S")} - {msg}\n')
    return False


def get_user_stats(currency: str, username: str):
    f2p_url = f"https://api.f2pool.com/{currency}/{username}"
    try:
        resp = requests.get(f2p_url)
    except Exception as err:
        return err
    if resp.status_code == 200:
        return resp.json()
    return json.dumps({'error_code': resp.status_code})


def get_miners_stats(currency: str, username: str, worker_name: str):
    f2p_url = f'https://api.f2pool.com/{currency}/{username}/{worker_name}'
    try:
        resp = requests.get(f2p_url)
    except Exception as err:
        return err
    if resp.status_code == 200:
        return resp.json()
    return json.dumps({'error_code': resp.status_code})


def check_alarms(stats: json) -> str:
    resp = ""
    if stats['worker_length'] != stats['worker_length_online']:
        resp = 'Not all miners online! {0} of {1} online'.format(stats['worker_length'], stats['worker_length_online'])
    for wrk in stats['workers']:
        if wrk[1] == 0:
            resp += 'Alarm! Device {0} has 0 hashrate!\r\n'.format(wrk[0])
    return resp


def generate_daily_stats(stats: json) -> str:
    return f"Balance:{stats['balance']}, hashrate: {stats['hashrate']}, " \
            f"{stats['worker_length_online']} online from {stats['worker_length']} overall."


def send_tg_message(tg_msg: str, tg_bot_token: str, tg_group_ip: str) -> bool:
    headers = {"Content-type": "application/json"}
    tg_url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage"
    result = requests.post(tg_url, headers=headers, data={
        "chat_id": tg_group_ip,
        "text": tg_msg
    })
    if result.status_code != 200:
        write_log('Unable to send telegram message.')
        return False
    return True


def send_healthcheck(uuid: str) -> bool:
    print('healthcheck')
    try:
        requests.get(f"https://hc-ping.com/{uuid}", timeout=10)
    except requests.RequestException as e:
        write_log(f"- error occured. Unable connect to HealthCheck.io\r\n Error: {e}")
        return False
    return True


def load_config(config_file: str):
    if os.path.isfile(config_file):
        with open(config_file, 'r', encoding='utf-8') as fp:
            config_loaded = json.load(fp=fp)
            return config_loaded
    return None


if __name__ == '__main__':
    config_settings = load_config(CONFIG_FILE)
    if config_settings is None:
        exit(1)
    user_status = get_user_stats('bitcoin', 'genat0sha')
    for curr in config_settings['currency'].keys():
        for wrk_user in config_settings['currency'][curr]:
            user_stats = get_user_stats(curr, wrk_user)
            write_log(f"Stats collected for {wrk_user} - balance:{user_stats['balance']}, "
                      f"hashrate: {user_stats['hashrate']}, "
                      f"{user_stats['worker_length_online']} online from {user_stats['worker_length']} overall.")
            alarms = check_alarms(user_stats)
            if len(alarms) > 1:
                send_tg_message(alarms, config_settings['tg_bot_token'], config_settings['tg_group_id'])
            if (datetime.datetime.now().time() >= NT_HOUR_START) and (datetime.datetime.now().time() <= NT_HOUR_END):
                msg = generate_daily_stats(user_status)
                send_tg_message(f'Stats for:{wrk_user} - {msg}', config_settings['tg_bot_token'],
                                config_settings['tg_group_id'])
    if send_healthcheck(config_settings['healthcheck_uuid']):
        exit(0)
    else:
        exit(2)