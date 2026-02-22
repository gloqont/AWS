
// Approximate exchange rates for estimation
// In a real app, these would come from a live API
export const APPROX_FX_RATES: Record<string, number> = {
    USD: 1,
    INR: 83.5,
    EUR: 0.92,
    GBP: 0.79,
    CAD: 1.35,
    AUD: 1.54,
    JPY: 149.5,
    SGD: 1.35,
    HKD: 7.82,
    CNY: 7.24,
};

// Mapping of country codes to their default currencies
export const COUNTRY_CURRENCY: Record<string, string> = {
    "US": "USD", "IN": "INR", "CA": "CAD", "GB": "GBP",
    "DE": "EUR", "FR": "EUR", "NL": "EUR", "AU": "AUD",
    "JP": "JPY", "SG": "SGD", "HK": "HKD", "CN": "CNY",
};

/**
 * Formats a number as a currency string, performing approximate conversion if necessary.
 * 
 * @param n The amount in USD (default base) to be formatted
 * @param currency The target currency code (e.g., "USD", "INR", "EUR")
 * @param fromCurrency The source currency code (default "USD")
 * @returns Formatted currency string
 */
export function fmtMoney(n: number, currency: string = "USD", fromCurrency: string = "USD") {
    let value = n;

    // Convert if currencies differ
    if (currency !== fromCurrency) {
        // If not USD, convert to USD first (simplistic implementation)
        // Only supports USD as base for now or direct conversion from USD
        if (fromCurrency === "USD" && APPROX_FX_RATES[currency]) {
            value = n * APPROX_FX_RATES[currency];
        } else if (APPROX_FX_RATES[fromCurrency] && APPROX_FX_RATES[currency]) {
            // Convert to USD then to target
            const usdValue = n / APPROX_FX_RATES[fromCurrency];
            value = usdValue * APPROX_FX_RATES[currency];
        }
    }

    try {
        return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
            style: "currency",
            currency: currency,
            maximumFractionDigits: 2,
            minimumFractionDigits: 2
        }).format(value);
    } catch (e) {
        // Fallback if Intl fails or currency code is invalid
        return `${currency} ${value.toFixed(2)}`;
    }
}
