import asyncio
import ctypes
import random
import sys
import traceback

from art import text2art
from termcolor import colored, cprint

from better_proxy import Proxy

from core import Grass
from core.autoreger import AutoReger
from core.utils import logger, file_to_list
from core.utils.accounts_db import AccountsDB
from core.utils.exception import EmailApproveLinkNotFoundException
from data.config import ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, THREADS, REGISTER_DELAY, \
    CLAIM_REWARDS_ONLY, MINING_MODE, WALLETS_FILE_PATH


def bot_info(name: str = ""):
    cprint(text2art(name), 'green')

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")

    print(
        f"{colored('EnJoYeR <crypto/> moves:', color='light_yellow')} "
        f"{colored('https://t.me/+tdC-PXRzhnczNDli', color='light_green')}"
    )


async def worker_task(_id, account: str, proxy: str = None, db: AccountsDB = None):
    email, password = account.split(":")[:2]
    grass = None

    try:
        grass = Grass(_id, email, password, proxy, db)

        await asyncio.sleep(random.uniform(*REGISTER_DELAY))
        logger.info(f"Starting №{_id} | {email} | {proxy}")

        if MINING_MODE:
            await grass.start()
        elif CLAIM_REWARDS_ONLY:
            await grass.claim_rewards()

        return True
    except EmailApproveLinkNotFoundException as e:
        logger.warning(e)
    except Exception as e:
        logger.error(f"{_id} | not handled exception | error: {e} {traceback.format_exc()}")
    finally:
        if grass:
            await grass.session.close()


async def main():
    accounts = file_to_list(ACCOUNTS_FILE_PATH)
    proxies = [Proxy.from_str(proxy).as_url for proxy in file_to_list(PROXIES_FILE_PATH)]

    db = AccountsDB('data/proxies_stats.db')
    await db.connect()

    for i, account in enumerate(accounts):
        account = account.split(":")[0]
        proxy = proxies[i] if len(proxies) > i else None

        if await db.proxies_exist(proxy) or not proxy:
            continue

        await db.add_account(account, proxy)

    await db.delete_all_from_extra_proxies()
    await db.push_extra_proxies(proxies[len(accounts):])

    autoreger = AutoReger.get_accounts(
        (ACCOUNTS_FILE_PATH, PROXIES_FILE_PATH, WALLETS_FILE_PATH),
        with_id=True,
        static_extra=(db, )
    )

    threads = THREADS

    if MINING_MODE:
        msg = "__MINING__ MODE"
        threads = len(autoreger.accounts)
    elif CLAIM_REWARDS_ONLY:
        msg = "__CLAIM__ MODE"

    logger.info(msg)

    await autoreger.start(worker_task, threads)

    await db.close_connection()


if __name__ == "__main__":
    bot_info("GRASS_AUTO")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    else:
        asyncio.run(main())
