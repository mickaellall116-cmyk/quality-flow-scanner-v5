# Splits

The splits endpoint provides historical data on stock split events for a specified company. It returns details including the date of each split and the corresponding split factor.

**API credits cost:** `20` per symbol

> **Note:** This API endpoint is available on the <a href="https://twelvedata.com/pricing">Grow</a> plan (individual) and the <a href="https://twelvedata.com/pricing-business">Venture</a> plan (business) and above.

## Parameters

- `symbol` (string, optional, see notes)
  Symbol ticker of instrument. For preferred stocks use dot(.) delimiter. E.g. `BRK.A` or `BRK.B` will be correct
  Example value: `AAPL`


- `figi` (string, optional, see notes)
  Filter by financial instrument global identifier (FIGI). This parameter is available on the Ultra plan (individual) and the Enterprise plan (business) and above.
  Example value: `BBG000B9Y5X2`


- `isin` (string, optional, see notes)
  Filter by international securities identification number (ISIN). ISIN access is activating in the Data add-ons section
  Example value: `US0378331005`


- `cusip` (string, optional, see notes)
  The CUSIP of an instrument for which data is requested. CUSIP access is activating in the Data add-ons section
  Example value: `594918104`


- `exchange` (string, optional)
  Exchange where instrument is traded
  Example value: `NASDAQ`


- `mic_code` (string, optional)
  Market Identifier Code (MIC) under ISO 10383 standard
  Example value: `XNAS`


- `country` (string, optional)
  Country where instrument is traded, e.g., `United States` or `US`
  Example value: `United States`


- `range` (string, optional)
  Range of data to be returned
  Available values: `last`, `1m`, `3m`, `6m`, `ytd`, `1y`, `2y`, `5y`, `full`
  Default value: `last`


- `start_date` (string, optional)
  The starting date for data selection. Format `2006-01-02`
  Example value: `2020-01-01`


- `end_date` (string, optional)
  The ending date for data selection. Format `2006-01-02`
  Example value: `2020-12-31`


**Notes:**

 - At least one of the following parameters is required: `symbol`, `figi`, `isin`, `cusip`.

## Response

- `meta` (object)
  Metadata about the instrument
  - `symbol` (string)
    Ticker symbol of instrument
  - `name` (string)
    Name of the instrument
  - `currency` (string)
    Currency in which the instrument is denominated
  - `exchange` (string)
    Exchange where instrument is traded
  - `mic_code` (string)
    Market identifier code (MIC) under ISO 10383 standard
  - `exchange_timezone` (string)
    Timezone of the exchange

- `splits` (array of object)
  List of stock splits
  - `date` (string)
    Stands for the split date
  - `description` (string)
    Specification of the split event
  - `ratio` (number)
    The ratio by which the number of a company's outstanding shares of stock are increased following a stock split. For example, a `4-for-1 split` results in four times as many outstanding shares, with each share selling at one forth of its pre-split price
  - `from_factor` (number)
    From factor of the split
  - `to_factor` (number)
    To factor of the split


## Example Request

```bash
curl "https://api.twelvedata.com/splits?symbol=AAPL&apikey=demo"
```

## Example Response

```json
{
    "meta": {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "currency": "USD",
        "exchange": "NASDAQ",
        "mic_code": "XNAS",
        "exchange_timezone": "America/New_York"
    },
    "splits": [
        {
            "date": "2020-08-31",
            "description": "4-for-1 split",
            "ratio": 0.25,
            "from_factor": 4,
            "to_factor": 1
        }
    ]
}
```
