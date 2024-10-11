# waxpeer-to-youpin
This program gets all unique CS item listings from waxpeer.com and their price in youpin898.com (both their cheapest listing)

## Credits
- This program uses 730.json which is template_id mapped for each item listing (more information can be found [here](https://github.com/EricZhu-42/SteamTradingSite-ID-Mapper/tree/main)).
- You can also use the alternative youpinDB.db provided [here](https://github.com/ShevonKuan/csgo_investment/tree/main).
- Information about Waxpeer API can be found [here](https://docs.waxpeer.com/).
NOTE: template ids provided may or may not cover 100% of available CS items.

## Limitations
- Unable to filter Doppler phases from Youpin API.
- Observed Youpin API rate limit is approximately 90/minute.
