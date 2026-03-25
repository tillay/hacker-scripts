import asyncio, aiohttp, ssl, time, sys
from aiohttp.resolver import AbstractResolver
from pathlib import Path

if len(sys.argv) < 4:
    print(
        f"Usage: {sys.argv[0]} <domain> <searchtext> <ip list file>\n"
        "Use masscan to get a valid list of alive IPs\n"
        "eg. masscan -iL <ranges.txt> -p 80,443 --rate=10000 -oL <iplist.txt>\n"
        "use ipinfo or smth to get proper ranges"
    )
    exit(1)

Path(sys.argv[1]).mkdir(exist_ok=True)

with open(sys.argv[3]) as f:
    ips = [line.split()[3] for line in f if line.strip()]

total, done, hits, lock = len(ips), 0, 0, asyncio.Lock()
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

class SingleIPResolver(AbstractResolver):
    def __init__(self, ip: str): self.ip = ip
    async def close(self): pass

    async def resolve(self, host, port=0, family=0):
        return [{"hostname": host, "host": self.ip, "port": port, "family": 2, "proto": 0, "flags": 0}]

async def scan_ip(ip):
    global done, hits

    connector = aiohttp.TCPConnector(ssl=ssl_ctx, resolver=SingleIPResolver(ip), limit=0)
    url = f"https://{sys.argv[1]}"

    try:
        async with aiohttp.ClientSession(connector=connector, connector_owner=True) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), headers={"Host": sys.argv[1], "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as resp:
                body = await resp.text(errors="ignore")
                async with lock:
                    done += 1
                    if sys.argv[2] in body:
                        hits += 1
                        print(f"\n[HIT] {ip}")
                        Path(f"{sys.argv[1]}/{ip}.html").write_text(body + str(resp.headers))
    except Exception:
        async with lock:
            done += 1

async def progress_printer():
    start = time.time()
    while done < total:
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        eta = (total - done) / rate if rate > 0 else 0
        print(f"\r[{done}/{total}] {rate:.0f} req/s | hits: {hits} | eta: {eta:.0f}s   ", end="", flush=True)
        await asyncio.sleep(1)

async def main():
    printer = asyncio.create_task(progress_printer())
    sem = asyncio.Semaphore(360)

    async def bounded(ip):
        async with sem:
            await scan_ip(ip)

    await asyncio.gather(*[bounded(ip) for ip in ips])
    printer.cancel()
    print(f"\n\nDone. {hits} hits from {total} IPs.")

asyncio.run(main())
