import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger



async def notify_customer_about_fuckup(s):
    await asyncio.sleep(2)
    logger.debug(s)

loop = asyncio.get_event_loop()
scheduler = AsyncIOScheduler(event_loop=loop)
# scheduler = AsyncIOScheduler()
scheduler.start()
scheduler.add_job(notify_customer_about_fuckup, 'date', kwargs={'s': '122'}, run_date=datetime.now()+timedelta(seconds=1) )
# scheduler.add_job(lambda x: logger.debug(x), 'interval', kwargs={'x': '22'}, seconds=2, )



loop.run_until_complete(asyncio.sleep(5))
