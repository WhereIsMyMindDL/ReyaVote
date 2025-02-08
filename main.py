import time
import asyncio
import aiohttp
import pandas as pd
from sys import stderr
from loguru import logger
from eth_account.account import Account
from eth_account.messages import encode_typed_data

logger.remove()
logger.add(stderr,
           format="<lm>{time:HH:mm:ss}</lm> | <level>{level}</level> | <blue>{function}:{line}</blue> "
                  "| <lw>{message}</lw>")


class ReyaVote:
    def __init__(self, private_key: str, proxy: str, number_acc: int) -> None:
        self.private_key = private_key
        self.account = Account().from_key(private_key=private_key)
        self.proxy: str = f"http://{proxy}" if proxy is not None else None
        self.id: int = number_acc
        self.client = None

    async def create_message(self) -> str and int:

        deadline: int = int(time.time() + 600000)

        message = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                "CastVoteBySig": [
                    {"name": "verifyingChainId", "type": "uint256"},
                    {"name": "voter", "type": "address"},
                    {"name": "yesVote", "type": "bool"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"}
                ]
            },
            "domain": {
                "name": "Reya",
                "version": "1",
                "verifyingContract": "0xce0c48b15a305f4675ced41ccebdc923d03b9b81"
            },
            "primaryType": "CastVoteBySig",  # This needs to match the type being signed
            "message": {
                "verifyingChainId": 1729,
                "voter": self.account.address,
                "yesVote": True,
                "nonce": 1,
                "deadline": deadline
            }
        }

        signature = Account.sign_message(encode_typed_data(full_message=message), self.private_key).signature.hex()

        return signature, deadline

    async def vote(self) -> None:
        async with aiohttp.ClientSession(headers={
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Connection': 'keep-alive',
            'Origin': 'https://app.reya.network',
            'Referer': 'https://app.reya.network/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/126.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }) as client:
            self.client = client

            response: aiohttp.ClientResponse = await self.client.get(
                f'https://api.reya.xyz/api/vote/rnip3/user/{self.account.address}',
                proxy=self.proxy,
            )
            response_json: dict = await response.json()
            if response_json['votingPower'] > 0 and not response_json['hasVoted']:
                signature, deadline = await ReyaVote.create_message(self)
                response: aiohttp.ClientResponse = await self.client.put(
                    f'https://api.reya.xyz/api/vote/0xce0c48b15a305f4675ced41ccebdc923d03b9b81/vote',
                    json={
                        'voter': self.account.address,
                        'isYesVote': 'yes',
                        'signature': f'0x{signature}',
                        'signatureDeadline': deadline,
                    },
                    proxy=self.proxy,
                )
                response_json: dict = await response.json()
                if 'txHash' in response_json:
                    logger.success(f'{self.account.address} Success Vote')
            else:
                logger.info(f'{self.account.address} no have votingPower or already Voted')


async def start_follow(account: list, id_acc: int, semaphore) -> None:
    async with semaphore:
        acc = ReyaVote(private_key=account[0], proxy=account[1],
                       number_acc=id_acc)

        try:

            await acc.vote()

        except Exception as e:
            logger.error(f'ID account:{id_acc} Failed: {str(e)}')


async def main() -> None:
    semaphore: asyncio.Semaphore = asyncio.Semaphore(10)

    tasks: list[asyncio.Task] = [
        asyncio.create_task(coro=start_follow(account=account, id_acc=idx, semaphore=semaphore))
        for idx, account in enumerate(accounts, start=1)
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    with open('accounts_data.xlsx', 'rb') as file:
        exel = pd.read_excel(file)
    accounts: list[list] = [
        [
            row["Private key"],
            row["Proxy"] if isinstance(row["Proxy"], str) else None
        ]
        for index, row in exel.iterrows()
    ]
    logger.info(f'My channel: https://t.me/CryptoMindYep')
    logger.info(f'Total wallets: {len(accounts)}\n')

    asyncio.run(main())

    logger.success('The work completed')
    logger.info('Thx for donat: 0x5AfFeb5fcD283816ab4e926F380F9D0CBBA04d0e')
