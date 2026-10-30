from . import hanpass, e9pay, gme, gmoney, hana

REGISTRY = {
    "hanpass": hanpass.fetch,
    "e9pay": e9pay.fetch,
    "gme": gme.fetch,
    "gmoney": gmoney.fetch,
    "hana": hana.fetch,
}
