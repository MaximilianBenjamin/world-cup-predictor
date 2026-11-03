"""National team → FIFA confederation map.

Used as a covariate by the Zeileis/Groll model (confederation strength differs
systematically, and cross-confederation matchups behave differently than intra).
Covers the main competitive nations; anything unmapped falls back to "Other".
"""

from __future__ import annotations

CONFEDERATIONS: dict[str, list[str]] = {
    "UEFA": [
        "Spain", "France", "England", "Germany", "Italy", "Portugal",
        "Netherlands", "Belgium", "Croatia", "Denmark", "Switzerland",
        "Poland", "Austria", "Ukraine", "Sweden", "Wales", "Serbia",
        "Czech Republic", "Turkey", "Russia", "Scotland", "Norway",
        "Hungary", "Republic of Ireland", "Romania", "Greece", "Slovakia",
        "Slovenia", "Iceland", "Finland", "Albania", "Northern Ireland",
        "Bosnia and Herzegovina", "Bulgaria", "Montenegro", "North Macedonia",
        "Georgia", "Israel", "Belarus", "Luxembourg", "Kosovo", "Armenia",
        "Azerbaijan", "Cyprus", "Estonia", "Latvia", "Lithuania", "Kazakhstan",
        "Moldova", "Malta", "Andorra", "Faroe Islands", "Gibraltar",
        "Liechtenstein", "San Marino",
    ],
    "CONMEBOL": [
        "Brazil", "Argentina", "Uruguay", "Colombia", "Chile", "Peru",
        "Ecuador", "Paraguay", "Venezuela", "Bolivia",
    ],
    "CAF": [
        "Senegal", "Morocco", "Nigeria", "Egypt", "Algeria", "Tunisia",
        "Cameroon", "Ghana", "Ivory Coast", "Mali", "Burkina Faso",
        "South Africa", "DR Congo", "Cape Verde", "Guinea", "Zambia",
        "Gabon", "Uganda", "Benin", "Angola", "Kenya", "Madagascar",
        "Mauritania", "Mozambique", "Namibia", "Sudan", "Togo", "Zimbabwe",
        "Equatorial Guinea", "Congo", "Sierra Leone", "Comoros", "Gambia",
        "Guinea-Bissau", "Libya", "Malawi", "Niger", "Tanzania", "Ethiopia",
        "Rwanda", "Botswana", "Liberia", "Central African Republic", "Burundi",
        "Eswatini", "Lesotho", "South Sudan", "Chad", "Somalia", "Djibouti",
        "Eritrea", "São Tomé and Príncipe", "Seychelles", "Mauritius",
    ],
    "AFC": [
        "Japan", "South Korea", "Iran", "Australia", "Saudi Arabia", "Qatar",
        "Iraq", "United Arab Emirates", "Uzbekistan", "China PR", "Oman",
        "Jordan", "Bahrain", "Syria", "Vietnam", "Thailand", "Lebanon",
        "India", "Kuwait", "Palestine", "Kyrgyzstan", "Tajikistan",
        "Turkmenistan", "North Korea", "Philippines", "Indonesia", "Malaysia",
        "Myanmar", "Hong Kong", "Yemen", "Singapore", "Afghanistan",
        "Maldives", "Nepal", "Cambodia", "Bangladesh", "Pakistan", "Bhutan",
        "Sri Lanka", "Laos", "Mongolia", "Brunei", "Macau", "Timor-Leste",
        "Guam", "Chinese Taipei",
    ],
    "CONCACAF": [
        "Mexico", "United States", "Costa Rica", "Canada", "Jamaica",
        "Panama", "Honduras", "El Salvador", "Trinidad and Tobago",
        "Guatemala", "Haiti", "Curaçao", "Nicaragua", "Suriname",
        "Cuba", "Guadeloupe", "Martinique", "Grenada", "Antigua and Barbuda",
        "St Kitts and Nevis", "Saint Lucia", "Dominican Republic", "Belize",
        "Guyana", "Bermuda", "Barbados", "Aruba", "Puerto Rico",
        "Saint Vincent and the Grenadines", "Dominica", "Bahamas",
        "Cayman Islands", "Montserrat", "Turks and Caicos Islands",
        "British Virgin Islands", "US Virgin Islands", "Anguilla",
    ],
    "OFC": [
        "New Zealand", "Fiji", "Papua New Guinea", "New Caledonia",
        "Solomon Islands", "Tahiti", "Vanuatu", "Samoa", "Tonga",
        "Cook Islands", "American Samoa",
    ],
}

# Reverse index: team → confederation.
_TEAM_TO_CONF: dict[str, str] = {
    team: conf for conf, teams in CONFEDERATIONS.items() for team in teams
}


def confederation_of(team: str) -> str:
    """Return the confederation for a national team, or 'Other' if unmapped."""
    return _TEAM_TO_CONF.get(team, "Other")
