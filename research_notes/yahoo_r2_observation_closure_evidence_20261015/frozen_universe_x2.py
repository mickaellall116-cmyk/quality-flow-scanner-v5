"""V5.4 forward-test universe, cohort 2 ("X2").

FROZEN 2026-09-15. Second cohort added on day 1 of the forward test to
accelerate out-of-sample evidence collection. Every symbol below was
verified to return clean data from the market-data feed on 2026-09-15
(dropped: SQ->renamed XYZ, PSTG, CTRA, CYBR, BITF, UNI-USD, SUI-USD,
HYPE-USD, TAO-USD, PEPE-USD -- no usable data).

Cohort 1 (UX51, 51 symbols) is unchanged and remains the primary cohort.
Cohort 2 is tagged "Forward-X2" in signal rows (theme field); cohort 1 is
"Forward-UX51". Analyze per-cohort and pooled. Never edit this list during
the forward test -- any future change is a new cohort, not an edit.
"""

from typing import List

# Index ETFs, rates, metals, energy commodities -- what traders actually trade.
_X2_MACRO: List[str] = [
    "QQQ", "DIA", "XLK", "XLE",
    "TLT", "GLD", "SLV", "USO", "UNG", "CPER", "PPLT",
]

# Top-traded crypto (spot pairs).
_X2_CRYPTO: List[str] = [
    "BNB-USD", "ADA-USD", "TRX-USD", "ONDO-USD", "NEAR-USD", "ARB-USD",
    "AAVE-USD", "RENDER-USD", "FET-USD", "HBAR-USD", "ICP-USD", "DOT-USD",
    "FIL-USD", "INJ-USD", "ATOM-USD", "SHIB-USD", "BONK-USD", "WIF-USD",
]

# Retail/Robinhood most-traded: meme, AI-hype, quantum, nuclear, space-adjacent.
_X2_RETAIL: List[str] = [
    "GME", "AMC", "DJT", "SOUN", "BBAI", "IONQ", "RGTI",
    "OKLO", "SMR", "APLD", "LCID", "OPEN",
]

# Liquid large-caps across sectors (S&P-500-type names only).
_X2_LARGE: List[str] = [
    # Big tech / enterprise
    "ORCL", "ADBE", "INTU", "NOW", "IBM", "CSCO", "TXN", "DELL", "ANET",
    # Semis / hardware
    "KLAC", "ASML", "NXPI", "MRVL", "ON", "CDNS", "SNPS", "WDC", "STX",
    # Software / cyber
    "PANW", "ZS", "OKTA", "MDB", "WDAY", "VEEV", "TEAM", "HUBS",
    "DOCU", "ZM",
    # Fintech
    "V", "MA", "XYZ", "FIS", "GPN",
    # Consumer / internet / travel
    "UBER", "ABNB", "BKNG", "EXPE", "DASH", "EBAY", "DKNG", "DIS", "LYFT",
    # Energy majors
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "FSLR",
    # Biotech / pharma
    "AMGN", "GILD", "REGN", "VRTX", "BIIB", "ILMN",
    # Banks
    "JPM", "BAC", "GS", "MS", "WFC", "SCHW",
    # Retail / staples
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD",
    # Industrials
    "CAT", "DE", "BA", "GE", "HON", "LMT", "RTX", "UNP",
]

# AI buildout: chips, servers, optical, AI cloud, AI power, AI software.
_X2_AI: List[str] = [
    "TSM",
    "VRT", "CLS", "JBL", "HPE",
    "LITE", "COHR", "CIEN",
    "NBIS", "CRWV",
    "VST", "CEG", "GEV", "CCJ",
    "S", "AI", "UPST", "PATH", "TEM", "RBRK",
    "RDDT",
]

# Energy: majors, E&P, services, midstream, refiners, uranium, solar, utilities.
_X2_ENERGY: List[str] = [
    "SHEL", "TTE", "BP", "DVN", "FANG", "EQT",
    "HAL", "BKR",
    "KMI", "WMB", "EPD", "ET", "OKE",
    "MPC", "VLO", "PSX",
    "NEE", "ENPH", "UUUU",
]

# Remaining sectors: cyber, healthcare, defense, telecom, REITs, materials,
# staples, consumer, airlines, Berkshire, quantum, CRISPR, logistics.
_X2_SECTORS: List[str] = [
    "FTNT",
    "LLY", "UNH", "JNJ", "ABBV", "ISRG", "TMO", "DHR", "CRSP",
    "NOC", "GD",
    "T", "VZ",
    "AMT", "EQIX", "DLR",
    "FCX", "NEM", "LIN", "ALB",
    "PG", "KO", "PEP",
    "CMG", "RBLX", "SNAP", "AFRM",
    "DAL", "UAL", "GM",
    "BRK-B", "QBTS", "FDX",
]

# Crypto-adjacent equities: miners, ETH-treasury cos, Galaxy.
_X2_CRYPTO_STOCKS: List[str] = [
    "MARA", "RIOT", "CLSK", "HUT", "WULF", "CORZ", "CIFR",
    "BMNR", "SBET", "GLXY",
]

UNIVERSE_X2: List[str] = (
    _X2_MACRO + _X2_CRYPTO + _X2_RETAIL + _X2_LARGE
    + _X2_AI + _X2_ENERGY + _X2_SECTORS + _X2_CRYPTO_STOCKS
)

EXPECTED_X2_SIZE = 199
