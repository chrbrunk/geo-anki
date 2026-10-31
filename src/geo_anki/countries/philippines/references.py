"""Curated Philippine reference cities and provincial centers.

Names and city/town status were checked against the pinned dataset's municipal
layers (PSGC 3Q 2026). These are geographic reference points, not a population
ranking; some associated cities are administratively independent.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ReferencePlace:
    """A prominent city or town associated with a province.

    Attributes:
        name: Display name of the reference place.
        kind: Whether the place is a city or town.
    """

    name: str
    kind: Literal["city", "town"] = "city"


REFERENCE_PLACES = {
    "Abra": ReferencePlace("Bangued", "town"),
    "Agusan del Norte": ReferencePlace("Butuan"),
    "Agusan del Sur": ReferencePlace("Bayugan"),
    "Aklan": ReferencePlace("Kalibo", "town"),
    "Albay": ReferencePlace("Legazpi"),
    "Antique": ReferencePlace("San Jose de Buenavista", "town"),
    "Apayao": ReferencePlace("Kabugao", "town"),
    "Aurora": ReferencePlace("Baler", "town"),
    "Basilan": ReferencePlace("Isabela City"),
    "Bataan": ReferencePlace("Balanga"),
    "Batanes": ReferencePlace("Basco", "town"),
    "Batangas": ReferencePlace("Lipa"),
    "Benguet": ReferencePlace("Baguio"),
    "Biliran": ReferencePlace("Naval", "town"),
    "Bohol": ReferencePlace("Tagbilaran"),
    "Bukidnon": ReferencePlace("Valencia"),
    "Bulacan": ReferencePlace("San Jose del Monte"),
    "Cagayan": ReferencePlace("Tuguegarao"),
    "Camarines Norte": ReferencePlace("Daet", "town"),
    "Camarines Sur": ReferencePlace("Naga"),
    "Camiguin": ReferencePlace("Mambajao", "town"),
    "Capiz": ReferencePlace("Roxas City"),
    "Catanduanes": ReferencePlace("Virac", "town"),
    "Cavite": ReferencePlace("Dasmariñas"),
    "Cebu": ReferencePlace("Cebu City"),
    "Cotabato": ReferencePlace("Kidapawan"),
    "Davao Occidental": ReferencePlace("Malita", "town"),
    "Davao Oriental": ReferencePlace("Mati"),
    "Davao de Oro": ReferencePlace("Nabunturan", "town"),
    "Davao del Norte": ReferencePlace("Tagum"),
    "Davao del Sur": ReferencePlace("Davao City"),
    "Dinagat Islands": ReferencePlace("San Jose", "town"),
    "Eastern Samar": ReferencePlace("Borongan"),
    "Guimaras": ReferencePlace("Jordan", "town"),
    "Ifugao": ReferencePlace("Lagawe", "town"),
    "Ilocos Norte": ReferencePlace("Laoag"),
    "Ilocos Sur": ReferencePlace("Vigan"),
    "Iloilo": ReferencePlace("Iloilo City"),
    "Isabela": ReferencePlace("Ilagan"),
    "Kalinga": ReferencePlace("Tabuk"),
    "La Union": ReferencePlace("San Fernando"),
    "Laguna": ReferencePlace("Calamba"),
    "Lanao del Norte": ReferencePlace("Iligan"),
    "Lanao del Sur": ReferencePlace("Marawi"),
    "Leyte": ReferencePlace("Tacloban"),
    "Maguindanao del Norte": ReferencePlace("Cotabato City"),
    "Maguindanao del Sur": ReferencePlace("Buluan", "town"),
    "Marinduque": ReferencePlace("Boac", "town"),
    "Masbate": ReferencePlace("Masbate City"),
    "Misamis Occidental": ReferencePlace("Ozamiz"),
    "Misamis Oriental": ReferencePlace("Cagayan de Oro"),
    "Mountain Province": ReferencePlace("Bontoc", "town"),
    "Negros Occidental": ReferencePlace("Bacolod"),
    "Negros Oriental": ReferencePlace("Dumaguete"),
    "Northern Samar": ReferencePlace("Catarman", "town"),
    "Nueva Ecija": ReferencePlace("Cabanatuan"),
    "Nueva Vizcaya": ReferencePlace("Bayombong", "town"),
    "Occidental Mindoro": ReferencePlace("San Jose", "town"),
    "Oriental Mindoro": ReferencePlace("Calapan"),
    "Palawan": ReferencePlace("Puerto Princesa"),
    "Pampanga": ReferencePlace("Angeles"),
    "Pangasinan": ReferencePlace("Dagupan"),
    "Quezon": ReferencePlace("Lucena"),
    "Quirino": ReferencePlace("Cabarroguis", "town"),
    "Rizal": ReferencePlace("Antipolo"),
    "Romblon": ReferencePlace("Odiongan", "town"),
    "Samar": ReferencePlace("Calbayog"),
    "Sarangani": ReferencePlace("Alabel", "town"),
    "Siquijor": ReferencePlace("Siquijor", "town"),
    "Sorsogon": ReferencePlace("Sorsogon City"),
    "South Cotabato": ReferencePlace("General Santos"),
    "Southern Leyte": ReferencePlace("Maasin"),
    "Sultan Kudarat": ReferencePlace("Tacurong"),
    "Sulu": ReferencePlace("Jolo", "town"),
    "Surigao del Norte": ReferencePlace("Surigao City"),
    "Surigao del Sur": ReferencePlace("Bislig"),
    "Tarlac": ReferencePlace("Tarlac City"),
    "Tawi-Tawi": ReferencePlace("Bongao", "town"),
    "Zambales": ReferencePlace("Olongapo"),
    "Zamboanga Sibugay": ReferencePlace("Ipil", "town"),
    "Zamboanga del Norte": ReferencePlace("Dipolog"),
    "Zamboanga del Sur": ReferencePlace("Pagadian"),
}
