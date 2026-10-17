"""Rule engine on synthetic records that deliberately differ from the dataset (other LOINC aliases,
linkIds, wording), so the rules are tested as generic concepts rather than tuned to P01–P06."""

import datetime as dt

from mdt_backend import rules
from mdt_backend.bundles import Bundle
from mdt_backend.concepts import Symptom, classify, facts
from mdt_backend.provenance import NOT_FOUND

MDT = dt.date(2026, 10, 21)


def obs(id_, date, *, loinc=None, title=None, value=None, unit="", low=None, high=None, text=None):
    o = {"resourceType": "Observation", "id": id_, "status": "final", "effectiveDateTime": date}
    o["code"] = {"text": title or id_}
    if loinc:
        o["code"]["coding"] = [{"system": "http://loinc.org", "code": loinc}]
    if value is not None:
        o["valueQuantity"] = {"value": value, "unit": unit}
    if text is not None:
        o["valueString"] = text
    if low is not None or high is not None:
        rr = {}
        if low is not None:
            rr["low"] = {"value": low}
        if high is not None:
            rr["high"] = {"value": high}
        o["referenceRange"] = [rr]
    return o


def qr(id_, date, **items):
    """items: linkId → (question, answer); int answers become valueInteger."""
    return {
        "resourceType": "QuestionnaireResponse",
        "id": id_,
        "authored": date,
        "item": [
            {
                "linkId": k,
                "text": q,
                "answer": [{"valueInteger": a} if isinstance(a, int) else {"valueString": a}],
            }
            for k, (q, a) in items.items()
        ],
    }


def condition(id_, icd):
    return {"resourceType": "Condition", "id": id_, "code": {"coding": [{"code": icd}]}}


def bundle(*resources):
    return Bundle({"entry": [{"resource": r} for r in resources]})


def flags(b, **kw):
    return rules.red_flags(b, MDT, **kw)


def texts(fs):
    return [f.statement.text for f in fs]


def test_lab_with_other_loinc_alias_and_renamed_prom_item_still_corroborates():
    b = bundle(
        condition("dg", "C18.7"),
        obs("hb", "2026-10-15", loinc="30313-1", title="Hgb", value=95, unit="g/l", low=120),
        qr("q", "2026-10-16", fatigue_q=("Jak moc vás trápí únava (0–10)?", 7)),
    )
    hb = [f for f in flags(b) if f.statement.model.endswith(":corroborated")]
    assert len(hb) == 1 and hb[0].severity == "high"
    assert "CTCAE stupeň 2" in hb[0].statement.text
    assert {s.reference for s in hb[0].statement.sources} >= {
        "Observation/hb",
        "QuestionnaireResponse/q#fatigue_q",
    }


def test_ctcae_grading_and_mild_aggregate():
    b = bundle(
        obs("plt", "2026-10-15", loinc="777-3", value=40, unit="10^9/l", low=150),
        obs("crp", "2026-10-15", loinc="1988-5", value=12, unit="mg/l", high=5),
    )
    fs = flags(b)
    plt = next(f for f in fs if "Observation/plt" in {s.reference for s in f.statement.sources})
    assert "stupeň 3" in plt.statement.text and plt.severity == "high"
    assert any("Mírně mimo" in t and "crp" in t.lower() for t in texts(fs))


def test_tnm_discordance_fires_on_t_change_but_not_on_progression_to_m1():
    discordant = bundle(
        obs("t1", "2026-10-06", title="TNM klinické", text="cT3 cN2 cM0, stadium IIIB"),
        obs("t2", "2026-10-07", title="TNM klinické", text="cT2b cN2 cM0, stadium IIIA"),
    )
    assert any("Nesoulad stagingu" in t for t in texts(flags(discordant)))
    progression = bundle(
        obs("t1", "2026-03-01", title="TNM klinické", text="cT2 cN1 cM0, stadium IIB"),
        obs("t2", "2026-10-07", title="TNM klinické", text="cT2 cN1 cM1, stadium IV"),
    )
    assert not any("Nesoulad stagingu" in t for t in texts(flags(progression)))


def test_lvef_drop_with_uncoded_title():
    b = bundle(
        obs("e1", "2026-04-01", title="Echokardiografie – ejekční frakce", value=64, unit="%"),
        obs("e2", "2026-10-01", title="Echokardiografie – ejekční frakce", value=48, unit="%"),
    )
    lvef = [f for f in flags(b) if f.statement.model.endswith(":lvef_drop")]
    assert len(lvef) == 1 and "64 → 48" in lvef[0].statement.text


def test_negated_new_symptom_is_not_an_alarm():
    assert classify("Nic nového, žádné bolesti kostí.") == []
    b = bundle(
        condition("dg", "C50.9"),
        qr("q", "2026-10-16", obtize=("Máte nějaké nové obtíže?", "Nic nového.")),
    )
    assert not any(f.statement.model.endswith(":alarm") for f in flags(b))


def test_llm_classified_symptoms_replace_keyword_fallback():
    b = bundle(
        condition("dg", "C50.9"),
        condition("met", "C79.5"),
        qr("q", "2026-10-16", obtize=("Máte nějaké nové obtíže?", "Hurts when I walk, left hip")),
    )
    # no Czech keyword: only the generic "new complaint" flag
    assert [f.severity for f in flags(b) if f.statement.model.endswith(":alarm")] == ["medium"]
    q = b.get("QuestionnaireResponse/q")
    sym = [Symptom("bone_pain", q, "obtize", "left hip", True)]
    alarm = [f for f in flags(b, symptoms=sym) if f.statement.model.endswith(":alarm")]
    assert alarm and alarm[0].severity == "high"  # escalated: bone pain with bone metastases


def test_missing_required_biomarkers_use_not_found_wording():
    b = bundle(condition("dg", "C18.7"), condition("met", "C78.7"))
    req = [f for f in flags(b) if f.statement.model.endswith(":required")]
    assert len(req) == 1 and "KRAS" in req[0].statement.text
    assert req[0].statement.text.endswith(NOT_FOUND)


def test_config_can_disable_and_retune_rules():
    b = bundle(
        obs("e1", "2026-04-01", loinc="10230-1", value=64, unit="%"),
        obs("e2", "2026-10-01", loinc="10230-1", value=58, unit="%"),
    )
    assert not any(f.statement.model.endswith(":lvef_drop") for f in flags(b))
    cfg = rules._merge(rules.load_config(), {"lvef_drop": {"drop_points": 5}})
    assert any(f.statement.model.endswith(":lvef_drop") for f in flags(b, config=cfg))
    off = rules._merge(cfg, {"lvef_drop": {"enabled": False}})
    assert not any(f.statement.model.endswith(":lvef_drop") for f in flags(b, config=off))


def test_every_flag_is_sourced():
    b = bundle(
        condition("dg", "C50.9"),
        obs("hb", "2026-10-15", loinc="718-7", value=85, unit="g/l", low=120),
        qr("q", "2026-10-16", unava=("Únava (0–10)", 9)),
    )
    f = facts(b, MDT)
    assert f.labs["hb"][0].value == 85
    for flag in flags(b):
        assert flag.statement.sources or flag.statement.text.endswith(NOT_FOUND)
