EGX_STOCKS = {
    "Banking & Finance": [
        {"ticker": "COMI", "name": "Commercial International Bank (CIB)", "keywords": ["bank", "banking", "interest rate", "central bank", "CBE", "lending", "credit", "dollar", "currency", "pound", "EGP"]},
        {"ticker": "QNBA", "name": "QNB Alahli Bank", "keywords": ["bank", "banking", "interest rate", "Qatar", "QNB"]},
        {"ticker": "ADIB", "name": "Abu Dhabi Islamic Bank Egypt", "keywords": ["bank", "islamic finance", "Abu Dhabi", "UAE"]},
        {"ticker": "FWRY", "name": "Fawry Banking Technology", "keywords": ["fintech", "digital payment", "e-payment", "technology", "banking tech"]},
        {"ticker": "CIEB", "name": "Credit Agricole Egypt", "keywords": ["bank", "french", "credit", "agriculture"]},
        {"ticker": "ALEXB", "name": "Alexandria Bank", "keywords": ["bank", "Alexandria"]},
        {"ticker": "AAIB", "name": "Arab African International Bank", "keywords": ["bank", "african", "arab"]},
    ],
    "Oil & Gas": [
        {"ticker": "AMOC", "name": "Alexandria Mineral Oils Company", "keywords": ["oil", "gas", "petroleum", "fuel", "crude", "OPEC", "refinery", "energy", "LNG", "Iran", "Saudi", "Trump", "sanctions"]},
        {"ticker": "SDPC", "name": "Sidi Kerir Petrochemicals", "keywords": ["petrochemical", "oil", "gas", "chemical", "refinery", "petroleum"]},
        {"ticker": "EGAZ", "name": "Egyptian Gas Company", "keywords": ["gas", "natural gas", "LNG", "pipeline", "energy"]},
        {"ticker": "EGPC", "name": "Egyptian Petroleum", "keywords": ["oil", "petroleum", "crude", "barrel", "OPEC", "drilling"]},
    ],
    "Real Estate & Construction": [
        {"ticker": "EMFD", "name": "Emaar Misr", "keywords": ["real estate", "construction", "housing", "development", "property", "mortgage"]},
        {"ticker": "MNHD", "name": "Madinet Nasr Housing", "keywords": ["housing", "real estate", "property", "construction"]},
        {"ticker": "PHDC", "name": "Palm Hills Developments", "keywords": ["real estate", "development", "luxury", "housing", "property"]},
        {"ticker": "TMGH", "name": "Talaat Moustafa Group", "keywords": ["real estate", "city", "housing", "new city", "development"]},
        {"ticker": "HELI", "name": "Heliopolis Housing", "keywords": ["housing", "real estate", "Heliopolis"]},
        {"ticker": "OCDI", "name": "Orascom Development Egypt", "keywords": ["tourism", "real estate", "resort", "development", "El Gouna"]},
        {"ticker": "ARCO", "name": "Arab Contractors", "keywords": ["construction", "infrastructure", "government contract", "roads", "bridges"]},
    ],
    "Telecom & Technology": [
        {"ticker": "ETEL", "name": "Telecom Egypt (WE)", "keywords": ["telecom", "internet", "5G", "fiber", "broadband", "communication", "technology"]},
        {"ticker": "ORTE", "name": "Orascom Telecom Media", "keywords": ["telecom", "media", "mobile", "internet", "Orascom"]},
    ],
    "Food & Beverages": [
        {"ticker": "JUFO", "name": "Juhayna Food Industries", "keywords": ["food", "dairy", "juice", "consumer", "inflation", "wheat", "agriculture"]},
        {"ticker": "DOMTY", "name": "Arab Dairy Products (Domty)", "keywords": ["dairy", "cheese", "food", "consumer goods"]},
        {"ticker": "OLFI", "name": "Olympic Group", "keywords": ["consumer", "appliances", "manufacturing"]},
        {"ticker": "BINV", "name": "Bisco Misr", "keywords": ["food", "biscuits", "snacks", "consumer"]},
    ],
    "Fertilizers & Chemicals": [
        {"ticker": "ABUK", "name": "Abu Qir Fertilizers", "keywords": ["fertilizer", "agriculture", "nitrogen", "ammonia", "natural gas", "farming", "food security"]},
        {"ticker": "EFIC", "name": "Egyptian Financial Industrial", "keywords": ["industrial", "chemical", "manufacturing"]},
        {"ticker": "MICH", "name": "Misr Chemical Industries", "keywords": ["chemical", "fertilizer", "industrial", "chlorine"]},
        {"ticker": "KIMA", "name": "Egyptian Chemical Industries (Kima)", "keywords": ["chemical", "fertilizer", "Aswan", "industrial"]},
    ],
    "Steel & Manufacturing": [
        {"ticker": "ESRS", "name": "Ezz Steel", "keywords": ["steel", "iron", "construction", "infrastructure", "manufacturing", "metal", "tariff", "trade war"]},
        {"ticker": "IRON", "name": "Ezz Rolling Mills", "keywords": ["steel", "rolling", "metal", "manufacturing"]},
        {"ticker": "SWDY", "name": "El Sewedy Electric", "keywords": ["electric", "cables", "energy", "infrastructure", "renewable", "solar", "wind"]},
        {"ticker": "ACGC", "name": "Alexandria Container", "keywords": ["shipping", "container", "port", "logistics", "trade", "Suez Canal"]},
    ],
    "Tourism & Hospitality": [
        {"ticker": "EGTS", "name": "Egyptian Tourism Resorts", "keywords": ["tourism", "hotel", "resort", "travel", "Red Sea", "Sharm", "Hurghada"]},
        {"ticker": "HRHO", "name": "El Arabia Group", "keywords": ["retail", "entertainment", "tourism"]},
        {"ticker": "PRTM", "name": "Port Said Tourism", "keywords": ["tourism", "Suez Canal", "port"]},
    ],
    "Pharmaceuticals & Healthcare": [
        {"ticker": "ISPH", "name": "Ibnsina Pharma", "keywords": ["pharma", "medicine", "healthcare", "drug", "hospital"]},
        {"ticker": "EIPCO", "name": "Egyptian International Pharma (EIPICO)", "keywords": ["pharma", "drug", "medicine", "healthcare", "generic"]},
        {"ticker": "PHAR", "name": "Pharco Pharmaceuticals", "keywords": ["pharma", "drug", "hepatitis", "medicine"]},
    ],
    "Mining & Metals": [
        {"ticker": "MNCO", "name": "Mining & Metallurgical Co", "keywords": ["mining", "gold", "mineral", "metal", "iron ore"]},
        {"ticker": "CENT", "name": "Centamin Egypt (Gold)", "keywords": ["gold", "mining", "Sukari", "precious metal", "inflation hedge"]},
    ],
    "Suez Canal & Logistics": [
        {"ticker": "SCFN", "name": "Suez Canal Bank", "keywords": ["Suez Canal", "shipping", "logistics", "trade route", "container", "freight"]},
        {"ticker": "ALCN", "name": "Alexandria Containers", "keywords": ["port", "container", "shipping", "logistics", "trade"]},
    ],
}


def get_all_stocks():
    all_stocks = []
    for sector, stocks in EGX_STOCKS.items():
        for stock in stocks:
            all_stocks.append({**stock, "sector": sector})
    return all_stocks


def get_stocks_summary():
    """Compact summary for AI prompt"""
    lines = []
    for sector, stocks in EGX_STOCKS.items():
        tickers = ", ".join([f"{s['ticker']} ({s['name']})" for s in stocks])
        lines.append(f"[{sector}]: {tickers}")
    return "\n".join(lines)
