import aiohttp
import asyncio
import time
import random
import pandas as pd
import requests
import json


async def fetch(session, template_id, retries=10):
    url = "https://api.youpin898.com/api/homepage/es/commodity/GetCsGoPagedList"
    payload = {
        "hasSold": "true",
        "haveBuZhangType": 0,
        "listSortType": "1",
        "listType": 10,
        "pageIndex": 1,
        "pageSize": 20,
        "sortType": "1",
        "status": "20",
        "stickersIsSort": False,
        "templateId": str(template_id),
        "userId": ""
    }

    try:
        async with session.post(url, json=payload) as response:
            if (response.status == 429 or response.status == 504 or response.status == 500) and retries > 0:  # Rate limit hit
                retry_delay = random.uniform(4, 6)  # Adjust accordingly
                print(f"Rate limit hit for template ID {template_id}. Retrying in {retry_delay:.2f} seconds...")
                await asyncio.sleep(retry_delay)
                return await fetch(session, template_id, retries - 1)  # Retry with decreased retries count
            elif response.status == 200:
                return await response.json()
            else:
                print(f"Failed to fetch data for template ID {template_id}: {response.status}")
                return None
    except Exception as e:
        print(f"Error for template ID {template_id}: {e}")
        return None


async def process_template_id(session, template_id, results):
    result = await fetch(session, template_id)
    if result:
        try:
            cheapest = result['Data']['CommodityList'][0]
            cheapest['id'] = template_id
            print(f"Completed: {cheapest['id']}, {cheapest['CommodityName']},"
                  f" {cheapest['Price']}, {cheapest['UserNickName']}")
            results.append(cheapest)
        except Exception as e:
            print(f"No valid data for template ID {template_id}: {e}")
            cheapest = {"id": template_id, "Price": 1}  # Failed fetch will be marked by Price = 1
            results.append(cheapest)


async def main(template_ids, rate_limit=100):
    results = []  # Store all results here
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, template_id in enumerate(template_ids):
            task = asyncio.create_task(process_template_id(session, template_id, results))
            tasks.append(task)

            # Implement rate limiting
            if (i + 1) % rate_limit == 0:
                await asyncio.sleep(random.uniform(65, 70))  # Sleep duration every rate_limit requests (Adjust accordingly)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

    return results  # Return the results


def fix_doppler(name):
    if 'Doppler' in name:
        return name.replace('Phase 1 ', '')\
            .replace('Phase 2 ', '')\
            .replace('Phase 3 ', '')\
            .replace('Phase 4 ', '')\
            .replace('Emerald ', '')\
            .replace('Ruby ', '')\
            .replace('Black Pearl ', '')\
            .replace('Sapphire ', '')
    else:
        return name


def filtering(df, min_price, max_price, exclude):  # Dataframe, minimum price, maximum price, list of keywords to exclude
    df = df[(df['usd_price'] > min_price) & (df['usd_price'] < max_price)]
    for word in exclude:
        df = df[~df['name'].str.contains(word, case=False, na=False)]
    return df


# Send a GET request to the Waxpeer API
def get_waxpeer_price():
    url = "https://api.waxpeer.com/v1/prices"
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()

        if 'items' in data:
            # Convert the list of items to a pandas DataFrame
            df = pd.DataFrame(data['items'])
            # Drop unnecessary columns
            df.drop(columns=['count', 'img', 'rarity_color', 'steam_price'], inplace=True)
            # Fix doppler name
            df['name'] = df['name'].apply(fix_doppler)

            with open('730.json', 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # Convert the JSON dictionary into a pandas DataFrame
            ydf = pd.DataFrame.from_dict(json_data, orient='index', columns=['Value'])

            # Reset index to get the keys as a column
            ydf.reset_index(inplace=True)

            # Rename the columns
            ydf.columns = ['name', 'id']

            # Display the DataFrame
            final = pd.merge(df, ydf, on='name', how='left')
            # Remove not found id
            final = final[~final['id'].isna()]
            final = final[final['id'] != -1]

            final['id'] = final['id'].astype('int')
            final['min'] = round(final['min']/1000, 2)  # Convert Waxpeer pricing to USD
            final.rename(columns={"min": "usd_price"}, inplace=True)
            # Filtering (Comment everything out if not needed)
            final = filtering(final, 2, 1000, ['Well-Worn', 'Battle-Scarred', 'StatTrak',
                                               'Sticker', 'Sealed Graffiti', 'G3SG1',
                                               'Souvenir', 'XM1014', 'MAG-7', 'CZ75-Auto',
                                               'PP-Bizon', 'Patch', 'SCAR-20'])

            # Save the DataFrame to a CSV file
            final.to_csv('waxpeer_prices.csv', index=False)

        else:
            print("The 'items' key is not found in the response.")
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")


# Convert buy price to your currency
def convert_idr(waxpeer_price):
    return waxpeer_price * 15700  # Adjust accordingly


if __name__ == "__main__":
    get_waxpeer_price()
    # Get ids
    waxpeer_prices = pd.read_csv('waxpeer_prices.csv')#[:150]
    waxpeer_prices['id'] = waxpeer_prices['id'].astype('str')
    template_ids = waxpeer_prices['id'].to_list()
    print(template_ids)
    start_time = time.time()

    #Run the async main function and get the results
    results = asyncio.run(main(template_ids))
    end_time = time.time()
    seconds = end_time - start_time
    print(f"Completed in {seconds:.2f} seconds / {(seconds/60):.2f} minute(s)")
    print(f"Total results collected: {len(results)}")
    youpin_prices = pd.DataFrame(results)
    youpin_prices['Price'] = youpin_prices['Price'].astype('float')
    youpin_prices['id'] = youpin_prices['id'].astype('str')
    youpin_prices = youpin_prices[youpin_prices['Price'] > 1][['id', 'Price']]  # Remove unsuccessful fetch
    youpin_prices.rename(columns={"Price": "rmb_price"}, inplace=True)
    youpin_prices.to_csv('youpin_prices.csv', index=False)

    final = pd.merge(waxpeer_prices, youpin_prices, on='id', how='inner')
    final.to_csv('final.csv', index=False)
