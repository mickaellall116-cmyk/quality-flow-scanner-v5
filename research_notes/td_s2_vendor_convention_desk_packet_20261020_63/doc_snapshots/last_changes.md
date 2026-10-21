# Last changes (New)

The last change endpoint provides the most recent updates to fundamental data for a specified dataset. It returns a timestamp indicating when the data was last modified, allowing users to efficiently manage API requests by only fetching new data when changes occur. This helps optimize data retrieval and reduce unnecessary API credit usage.

**API credits cost:** `1` per request

## Parameters

- `endpoint` (string, required)
  Endpoint name
  Example value: `statistics`
  Available values: `price_target`, `recommendations`, `statistics`, `insider_transactions`, `profile`, `mutual_funds_world_summary`, `mutual_funds_world`, `institutional_holders`, `analyst_rating`, `income_statement`, `income_statement_quarterly`, `cash_flow`, `cash_flow_quarterly`, `balance_sheet`, `balance_sheet_quarterly`, `mutual_funds_list`, `mutual_funds_world_sustainability`, `mutual_funds_world_summary`, `mutual_funds_world_risk`, `mutual_funds_world_purchase_info`, `mutual_funds_world_composition`, `mutual_funds_world_performance`, `mutual_funds_world`, `etfs_list`, `etfs_world`, `etfs_world_summary`, `etfs_world_performance`, `etfs_world_risk`, `etfs_world_composition`, `dividends`, `splits`, `money_market_funds_world`


- `start_date` (string, optional)
  The starting date and time for data selection, in `2006-01-02T15:04:05` format
  Example value: `2023-10-14T00:00:00`


- `symbol` (string, optional)
  Filter by symbol
  Example value: `AAPL`


- `exchange` (string, optional)
  Filter by exchange name
  Example value: `NASDAQ`


- `mic_code` (string, optional)
  Filter by market identifier code (MIC) under ISO 10383 standard
  Example value: `XNAS`


- `country` (string, optional)
  Filter by country name or alpha code, e.g., `United States` or `US`
  Example value: `United States`


- `page` (integer, optional)
  Page number
  Default value: `1`


- `outputsize` (integer, optional)
  Number of records in response
  Default value: `30`



## Response

- `pagination` (object)
  Pagination information
  - `current_page` (integer)
    Current page number
  - `per_page` (integer)
    Records per page

- `data` (array of object)
  Data contains the list of last changes
  - `symbol` (string)
    Ticker of the company
  - `mic_code` (string)
    Market Identifier Code (MIC) under ISO 10383 standard
  - `last_change` (string)
    The date and time of last changes, in `2006-01-02 15:04:05` format


## Example Request

```bash
curl "https://api.twelvedata.com/last_change/statistics?apikey=demo"
```

## Example Response

```json
{
    "pagination": {
        "current_page": 1,
        "per_page": 30
    },
    "data": [
        {
            "symbol": "AAPL",
            "mic_code": "XNAS",
            "last_change": "2023-10-14 12:22:48"
        }
    ]
}
```
