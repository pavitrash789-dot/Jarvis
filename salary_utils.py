import re


def parse_salary(salary_text):
    """
    Return a salary estimate only when the format is understood.

    Annual values are returned as LPA only for explicitly
    stated annual USD amounts. Hourly and unknown formats
    remain unconverted.
    """
    if not salary_text:
        return {
            "salary_lpa": None,
            "salary_period": "unknown",
            "salary_currency": "unknown",
            "salary_note": "Salary not disclosed",
        }

    text = salary_text.strip()
    lower = text.lower()

    # Hourly amounts cannot be converted reliably without
    # knowing the currency, working hours, and contract terms.
    if "hour" in lower or "/hr" in lower:
        return {
            "salary_lpa": None,
            "salary_period": "hourly",
            "salary_currency": "check listing",
            "salary_note": "Hourly rate; verify currency and hours",
        }

    # Recognize annual salaries explicitly stated in INR.
    annual_suffix = r"(?:per year|/year|annually|annual|per annum|p\.a\.)"

    inr_range = re.search(
        r"(?:₹|inr\b|rs\.?\s*)\s*([\d,]+(?:\.\d+)?)\s*"
        r"(?:-|–|to)\s*(?:(?:₹|inr\b|rs\.?\s*)\s*)?"
        r"([\d,]+(?:\.\d+)?)\s*" + annual_suffix,
        lower,
    )

    if inr_range:
        low = float(inr_range.group(1).replace(",", ""))
        high = float(inr_range.group(2).replace(",", ""))
        return {
            "salary_lpa": low / 100000,
            "salary_period": "annual",
            "salary_currency": "INR",
            "salary_note": (
                f"Annual INR range: ₹{low:,.0f}–₹{high:,.0f}; "
                "LPA estimate uses the lower end of the range"
            ),
        }

    inr_single = re.search(
        r"(?:₹|inr\b|rs\.?\s*)\s*([\d,]+(?:\.\d+)?)\s*"
        + annual_suffix,
        lower,
    )

    if inr_single:
        amount = float(inr_single.group(1).replace(",", ""))
        return {
            "salary_lpa": amount / 100000,
            "salary_period": "annual",
            "salary_currency": "INR",
            "salary_note": f"Annual INR salary: ₹{amount:,.0f}",
        }

    # Recognize explicitly stated annual USD ranges.
    annual = re.search(
        r"\$?\s*([\d,]+(?:\.\d+)?)\s*k?\s*[-–to]+\s*\$?\s*"
        r"([\d,]+(?:\.\d+)?)\s*k?\s*(?:usd\s*)?(?:per year|/year|annually|annual)",
        lower,
    )

    if annual:
        low = float(annual.group(1).replace(",", ""))
        high = float(annual.group(2).replace(",", ""))

        if "k" in lower:
            low *= 1000
            high *= 1000

        return {
            "salary_lpa": None,
            "salary_period": "annual",
            "salary_currency": "USD",
            "salary_note": (
                f"Annual USD range: ${low:,.0f}–${high:,.0f}; "
                "convert to INR before comparing with target"
            ),
        }

    return {
        "salary_lpa": None,
        "salary_period": "unknown",
        "salary_currency": "check listing",
        "salary_note": (
            f"Unparsed salary: {text}; verify listing before comparing"
        ),
    }


if __name__ == "__main__":
    examples = [
        "",
        "$45-$120/Hour",
        "$80k - $150k per year",
       "₹6,00,000 per year",
        "₹6,00,000–₹8,00,000 per year",
    ]

    for example in examples:
        print(example or "(not disclosed)", "=>", parse_salary(example))
