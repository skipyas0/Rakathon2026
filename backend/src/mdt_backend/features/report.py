"""A source-backed report prepared before consensus, then exported without live reads or AI."""

import datetime as dt
import hashlib
import json
import re
from html import escape
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from mdt_backend import agent, fhir
from mdt_backend.briefing import Case
from mdt_backend.bundles import date_of, src, text_of, value_of
from mdt_backend.config import settings
from mdt_backend.features import cases, records
from mdt_backend.provenance import Statement

router = APIRouter(prefix="/api/cases")
VERSION = "mdt-report-r4-v1"


class ReportSection(BaseModel):
    title: str
    items: list[Statement]


class Report(BaseModel):
    revision: str
    created: dt.datetime
    case_id: str
    patient: str
    label: str
    board: str | None
    mdt_date: dt.date | None
    record: records.CaseRecord
    sections: list[ReportSection]
    resources: list[dict]
    warnings: list[str]


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def clinical_record(record: records.CaseRecord) -> dict:
    data = record.model_dump(mode="json")
    for key in ("confirmed_by", "confirmed_at", "report_revision"):
        data["decision"].pop(key)
    # Display preferences are not clinical content.
    for key in ("layout", "visibility"):
        data.pop(key)
    return data


def _path(case_id: str, revision: str) -> Path:
    records._path(case_id)
    if not re.fullmatch(r"[a-f0-9]{64}", revision):
        raise HTTPException(422, "Neplatná revize zprávy")
    return records.RECORDS / "reports" / f"{case_id}-{revision}.json"


def load(case_id: str, revision: str) -> Report:
    path = _path(case_id, revision)
    if not path.exists():
        raise HTTPException(409, "Zpráva nebyla připravena. Otevřete ji před potvrzením.")
    return Report.model_validate_json(path.read_text("utf-8"))


def _evidence(patient: str) -> list[dict]:
    record = agent.Record(patient)
    resources = list(record.bundle.by_ref.values())
    # The agent restores dataset ids; normalize references to those ids as well.
    aliases = {actual: original for original, actual in record.iris_ids.items()}

    def restore(value):
        if isinstance(value, dict):
            return {
                key: aliases.get(item, item)
                if key == "reference" and isinstance(item, str)
                else restore(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [restore(item) for item in value]
        return value

    resources = restore(resources)
    known = {f"{r['resourceType']}/{r['id']}" for r in resources}
    for response in [r for r in resources if r["resourceType"] == "QuestionnaireResponse"]:
        canonical = response.get("questionnaire")
        if not canonical or any(r.get("url") == canonical.split("|")[0] for r in resources):
            continue
        url, _, version = canonical.partition("|")
        params = {"url": url}
        if version:
            params["version"] = version
        found = fhir._all_resources("Questionnaire", **params)
        definition = settings.dataset_dir / "dotaznik" / "dotaznik_PROMs_Questionnaire.json"
        if not found and definition.is_file():
            questionnaire = json.loads(definition.read_text("utf-8"))
            if questionnaire.get("url") == url and (
                not version or questionnaire.get("version") == version
            ):
                found = [questionnaire]
        if not found:
            raise HTTPException(422, f"Chybí definice dotazníku: {canonical}")
        for resource in found:
            ref = f"{resource['resourceType']}/{resource['id']}"
            if ref not in known:
                resources.append(resource)
                known.add(ref)
    return sorted(resources, key=lambda r: (r["resourceType"], r["id"]))


def _sections(case: Case, record: records.CaseRecord, resources: list[dict]) -> list[ReportSection]:
    from mdt_backend.bundles import Bundle

    bundle = Bundle({"entry": [{"resource": r} for r in resources]})
    sections = []
    for kind, label in (
        ("Condition", "Diagnózy a původní staging"),
        ("Observation", "Výsledky, biomarkery a výkonnostní stav"),
        ("QuestionnaireResponse", "Původní odpovědi pacienta (PROMs)"),
    ):
        sections.append(
            ReportSection(
                title=label,
                items=[
                    Statement(
                        text=f"{date_of(r) or 'datum neuvedeno'} · {evidence_text(r)}",
                        origin="record",
                        sources=[src(bundle, r)],
                    )
                    for r in bundle.all(kind)
                ],
            )
        )
    sections.append(ReportSection(title="Souhrn podkladů", items=case.summary))
    sections.append(
        ReportSection(
            title="Zobrazení, patologie a provedená léčba",
            items=[
                Statement(
                    text=f"{date_of(r) or 'datum neuvedeno'} · {text_of(r)}",
                    origin="record",
                    sources=[src(bundle, r)],
                )
                for kind in ("DiagnosticReport", "Procedure", "MedicationAdministration")
                for r in bundle.all(kind)
            ],
        )
    )
    sections.append(
        ReportSection(
            title="Průběh onemocnění",
            items=[
                e.statement.model_copy(update={"text": f"{e.date} · {e.statement.text}"})
                for e in case.timeline
            ],
        )
    )
    sections.extend(ReportSection(title=s.title, items=s.items) for s in case.sections)
    sections.append(
        ReportSection(
            title="Upozornění a chybějící údaje", items=[f.statement for f in case.red_flags]
        )
    )
    sections.append(ReportSection(title="Preference pacienta", items=case.preference))
    sections.append(
        ReportSection(title="Stanoviska komise", items=list(record.stanoviska.values()))
    )
    sections.append(
        ReportSection(
            title="Poznámky odborníků",
            items=[
                Statement(
                    text=f"{specialty}: {note.text}",
                    origin="human",
                    confirmed_by=note.by,
                    confirmed_at=note.at,
                )
                for specialty, note in record.notes.items()
            ],
        )
    )
    d = record.decision
    human = []
    for label, value in (
        ("Otázka pro MDT", record.prep.question or (case.question.text if case.question else "")),
        ("Léčebný záměr", d.intent),
        ("Zvolený postup", d.plan),
        ("Zdůvodnění", d.rationale),
        ("Zvažované možnosti", d.options_considered),
        ("Důvod odchylky", d.deviation_reason),
        ("Odlišná stanoviska", d.dissent),
        ("Klinická studie (záznam komise, nikoli AI screening)", d.trial),
        ("Re-evaluace", d.reevaluation),
        ("Postoj pacienta", record.patient_stance and record.patient_stance.model_dump_json()),
        ("Dohodnutý plán", record.agreed_plan),
    ):
        if value:
            human.append(
                Statement(text=f"{label}: {value}", origin="human", confirmed_by="Koordinátor/ka")
            )
    human.append(
        Statement(
            text="Soulad s postupy: "
            + {True: "ano", False: "odchylka", None: "nerozhodnuto"}[d.guideline_compliant],
            origin="human",
            confirmed_by="Koordinátor/ka",
        )
    )
    sections.append(ReportSection(title="Závěr MDT", items=human))
    if d.guideline_assessment:
        sections.append(
            ReportSection(title="AI hodnocení souladu", items=[d.guideline_assessment.statement])
        )
    sections.append(
        ReportSection(
            title="Akční plán",
            items=[
                Statement(
                    text=f"{t.what} · Odpovídá: {t.who or 'nepřiřazeno'} · "
                    f"Termín: {t.due or 'neurčen'} · "
                    f"{'dokončeno' if t.done else 'dosud nedokončeno'}",
                    origin="human",
                    confirmed_by="Koordinátor/ka",
                )
                for t in record.tasks
            ],
        )
    )
    return sections


def evidence_text(resource: dict) -> str:
    if resource["resourceType"] == "Condition":
        details = [text_of(resource)]
        details.extend(
            stage.get("summary", {}).get("text", "") for stage in resource.get("stage", [])
        )
        details.extend(site.get("text", "") for site in resource.get("bodySite", []))
        details.extend(
            f"{name}: " + json.dumps(resource[name], ensure_ascii=False)
            for name in ("clinicalStatus", "verificationStatus", "extension")
            if name in resource
        )
        return "\n".join(part for part in details if part)
    if resource["resourceType"] == "QuestionnaireResponse":
        lines = [f"Dotazník: {resource.get('questionnaire', 'neuveden')}"]

        def items(values):
            for item in values:
                prefix = f"{item.get('text', '')} [{item['linkId']}]"
                for answer in item.get("answer", []):
                    lines.append(f"{prefix}: {value_of(answer)}")
                    items(answer.get("item", []))
                items(item.get("item", []))

        items(resource.get("item", []))
        return "\n".join(lines)
    return text_of(resource)


def build(case_id: str, record: records.CaseRecord) -> Report:
    with cases.fhir_server():
        case = cases.get_case(case_id)
        resources = _evidence(case.patient.split("/")[-1])
    assessment = record.decision.guideline_assessment
    if assessment and (
        assessment.compared_plan != record.decision.plan
        or assessment.compared_rationale != record.decision.rationale
        or assessment.compared_intent != record.decision.intent
    ):
        raise HTTPException(409, "Hodnocení souladu neodpovídá aktuálnímu závěru")
    revision = digest(
        {
            "version": VERSION,
            "case": case.model_dump(mode="json"),
            "record": clinical_record(record),
            "resources": resources,
        }
    )
    known = {f"{r['resourceType']}/{r['id']}" for r in resources}

    if case.patient not in known:
        raise HTTPException(422, "Podklady neobsahují pacienta tohoto případu")

    def check_references(value, contained: set[str]):
        if isinstance(value, dict):
            contained = contained | {
                f"#{r['id']}" for r in value.get("contained", []) if r.get("id")
            }
            ref = value.get("reference")
            if isinstance(ref, str) and ref not in known and ref not in contained:
                raise HTTPException(422, f"Podklad odkazuje na nedostupný zdroj: {ref}")
            for item in value.values():
                check_references(item, contained)
        elif isinstance(value, list):
            for item in value:
                check_references(item, contained)

    check_references(resources, set())
    warnings = [
        "Demo: potvrzuje role Koordinátor/ka; identita a oprávnění lékaře nejsou ověřovány.",
        (
            "Export FHIR R4: zdrojová data nejsou certifikována jako mCODE. "
            "Neprovádí se automatické domýšlení kódů, TNM ani léčby."
        ),
    ]
    if not record.tasks:
        warnings.append("Akční plán nemá strukturované úkoly; z volného textu se úkoly neodvozují.")
    for r in resources:
        if r["resourceType"] == "Patient" and not any(
            n.get("given") or n.get("family") for n in r.get("name", [])
        ):
            warnings.append("Chybí strukturované jméno pacienta požadované profilem mCODE.")
        if r["resourceType"] == "Observation":
            if "tnm" in str(r.get("code", {})).lower() and not r.get("method"):
                warnings.append(f"{r['id']}: TNM nemá kódovanou metodu; zachován původní text.")
            if not r.get("code", {}).get("coding"):
                warnings.append(f"{r['id']}: název vyšetření není kódován; zachován původní text.")
    return Report(
        revision=revision,
        created=dt.datetime.now(dt.UTC),
        case_id=case_id,
        patient=case.patient,
        label=case.label,
        board=case.board,
        mdt_date=case.mdt_date,
        record=record.model_copy(deep=True),
        sections=_sections(case, record, resources),
        resources=resources,
        warnings=warnings,
    )


@router.post("/{case_id}/report")
def prepare(case_id: str, record: records.CaseRecord) -> Report:
    old = records.get_record(case_id)
    if old.decision.confirmed_by and old.decision.report_revision:
        return approved(case_id)
    if old.decision.confirmed_by:
        record = old
    record = records.merge_specialists(old, record)
    if record.decision.confirmed_by and not old.decision.confirmed_by:
        raise HTTPException(422, "Nejprve připravte zprávu bez potvrzení závěru")
    report = build(case_id, record)
    path = _path(case_id, report.revision)
    if path.exists():
        return load(case_id, report.revision)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), "utf-8")
    return report


def validate_confirmation(case_id: str, record: records.CaseRecord) -> None:
    revision = record.decision.report_revision
    if not revision:
        raise HTTPException(409, "Před potvrzením otevřete zprávu ke kontrole")
    report = load(case_id, revision)
    if report.revision != build(case_id, record).revision:
        raise HTTPException(409, "Podklady nebo závěr se změnily. Otevřete aktuální zprávu znovu.")


def approved(case_id: str) -> Report:
    record = records.get_record(case_id)
    if not record.decision.confirmed_by or not record.decision.report_revision:
        raise HTTPException(
            409, "Zpráva nemá potvrzenou revizi. Je nutná kontrola před potvrzením."
        )
    return load(case_id, record.decision.report_revision)


@router.get("/{case_id}/report")
def get_report(case_id: str) -> Report:
    return approved(case_id)


def _url(report: Report, name: str) -> str:
    return f"urn:uuid:{uuid5(NAMESPACE_URL, f'{report.case_id}/{report.revision}/{name}')}"


def fhir_bundle(report: Report, decision: records.Decision) -> dict:
    """Local R4 document, preserving evidence rather than declaring unvalidated mCODE profiles."""
    entries = []
    refs = {
        f"{r['resourceType']}/{r['id']}": _url(report, f"{r['resourceType']}/{r['id']}")
        for r in report.resources
    }
    for name in ("composition", "plan", "team", "software", "approval"):
        refs[name] = _url(report, name)
    for i, task in enumerate(report.record.tasks):
        refs[f"task-{i}"] = _url(report, f"task-{i}")

    def reference(name: str) -> dict:
        return {"reference": refs[name]}

    def add(name: str, resource: dict):
        entries.append({"fullUrl": refs[name], "resource": resource})

    def rewrite(value):
        if isinstance(value, dict):
            return {
                k: refs.get(v, v) if k == "reference" and isinstance(v, str) else rewrite(v)
                for k, v in value.items()
            }
        return [rewrite(v) for v in value] if isinstance(value, list) else value

    patient = reference(report.patient)
    at = decision.confirmed_at
    if at is None:
        raise HTTPException(409, "Chybí čas potvrzení zprávy")
    time = at.isoformat()
    composition = {
        "resourceType": "Composition",
        "status": "final",
        "type": {"text": "Záznam multidisciplinárního onkologického konzilia"},
        "subject": patient,
        "date": time,
        "author": [{"display": decision.confirmed_by}],
        "title": f"Závěr MDT – {report.label}",
        "attester": [
            {"mode": "professional", "time": time, "party": {"display": decision.confirmed_by}}
        ],
        "section": [
            {
                "title": section.title,
                "text": {
                    "status": "generated",
                    "div": '<div xmlns="http://www.w3.org/1999/xhtml">'
                    + "".join(
                        f"<p>{escape(s.text)}"
                        + (" [AI; potvrzeno v rámci závěru]" if s.origin == "ai" else "")
                        + "</p>"
                        for s in section.items
                    )
                    + "</div>",
                },
            }
            for section in report.sections
        ]
        + [
            {
                "title": "Strukturovaný záznam a původní podklady",
                "entry": [reference(name) for name in refs if name != "composition"],
            }
        ],
    }
    add("composition", composition)
    for resource in report.resources:
        original = f"{resource['resourceType']}/{resource['id']}"
        resource = rewrite(resource)
        resource.pop("meta", None)  # source version is retained in assembly provenance below
        resource["id"] = refs[original].removeprefix("urn:uuid:")
        add(original, resource)
    add(
        "team",
        {
            "resourceType": "CareTeam",
            "status": "active",
            "subject": patient,
            "name": report.board or "MDT",
            "participant": [
                {"role": [{"text": m.specialty}], "member": {"display": m.name or m.specialty}}
                for m in report.record.board
            ],
        },
    )
    add(
        "software",
        {
            "resourceType": "Device",
            "deviceName": [{"name": "MDT Copilot", "type": "user-friendly-name"}],
            "version": [{"value": VERSION}],
        },
    )
    add(
        "plan",
        {
            "resourceType": "CarePlan",
            "status": "active",
            "intent": "proposal",
            "subject": patient,
            "title": f"Závěr MDT: {report.record.decision.intent}",
            "description": report.record.decision.plan,
            "note": [{"text": report.record.decision.rationale}],
            "careTeam": [reference("team")],
            "addresses": [
                reference(f"Condition/{r['id']}")
                for r in report.resources
                if r["resourceType"] == "Condition"
            ],
            "activity": [
                {"reference": reference(f"task-{i}")} for i in range(len(report.record.tasks))
            ],
        },
    )
    for i, task in enumerate(report.record.tasks):
        resource = {
            "resourceType": "Task",
            "status": "completed" if task.done else "requested",
            "intent": "proposal",
            "description": task.what,
            "for": patient,
            "basedOn": [reference("plan")],
        }
        if task.who:
            resource["owner"] = {"display": task.who}
        if task.due:
            end = dt.datetime.combine(task.due, dt.time(23, 59, 59), ZoneInfo("Europe/Prague"))
            resource["restriction"] = {"period": {"end": end.isoformat()}}
        add(f"task-{i}", resource)
    add(
        "approval",
        {
            "resourceType": "Provenance",
            "target": [reference("composition"), reference("plan")],
            "recorded": time,
            "occurredDateTime": time,
            "activity": {"text": "Potvrzení přesné revize zprávy a závěru MDT (demo)"},
            "agent": [
                {"type": {"text": "attester"}, "who": {"display": decision.confirmed_by}},
                {"type": {"text": "assembler"}, "who": reference("software")},
            ],
            "entity": [
                {
                    "role": "source",
                    "what": reference(f"{r['resourceType']}/{r['id']}"),
                    "extension": [
                        {
                            "url": "https://rakathon.example.org/fhir/StructureDefinition/source-version",
                            "valueString": str(r.get("meta", {}).get("versionId", "unknown")),
                        }
                    ],
                }
                for r in report.resources
            ],
        },
    )
    for si, section in enumerate(report.sections):
        for ii, statement in enumerate(section.items):
            if statement.origin != "ai":
                continue
            name = f"ai-{si}-{ii}"
            refs[name] = _url(report, name)
            add(
                name,
                {
                    "resourceType": "Provenance",
                    "target": [reference("composition")],
                    "recorded": time,
                    "activity": {
                        "text": "AI tvrzení schválené potvrzením závěru; "
                        "čas generování není v původním Statement uložen"
                    },
                    "agent": [
                        {"type": {"text": "author"}, "who": reference("software")},
                        {"type": {"text": "attester"}, "who": {"display": decision.confirmed_by}},
                    ],
                    "entity": [
                        {"role": "source", "what": reference(source.reference.split("#")[0])}
                        for source in statement.sources
                        if source.reference.split("#")[0] in refs
                    ],
                    "extension": [
                        {
                            "url": "https://rakathon.example.org/fhir/StructureDefinition/approved-ai-claim",
                            "extension": [
                                {"url": "section", "valueInteger": si},
                                {"url": "item", "valueInteger": ii},
                                {"url": "model", "valueString": statement.model},
                                {"url": "claim", "valueString": statement.text},
                                {
                                    "url": "sources",
                                    "valueString": json.dumps(
                                        [s.model_dump(mode="json") for s in statement.sources],
                                        ensure_ascii=False,
                                    ),
                                },
                            ],
                        }
                    ],
                },
            )
    # Every resource is explicit document content, including per-claim provenance.
    composition["section"][-1]["entry"] = [{"reference": entry["fullUrl"]} for entry in entries[1:]]
    bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "identifier": {"system": "urn:ietf:rfc:3986", "value": _url(report, "document")},
        "timestamp": time,
        "entry": entries,
    }

    def compact(value):
        if isinstance(value, dict):
            return {
                k: compact(v) for k, v in value.items() if v is not None and v != [] and v != {}
            }
        return [compact(v) for v in value] if isinstance(value, list) else value

    return compact(bundle)


@router.get("/{case_id}/zaver.fhir.json")
def download(case_id: str) -> Response:
    report = approved(case_id)
    decision = records.get_record(case_id).decision
    return Response(
        json.dumps(fhir_bundle(report, decision), ensure_ascii=False, sort_keys=True),
        media_type="application/fhir+json",
        headers={"Content-Disposition": f'attachment; filename="zaver-mdt-{case_id}.fhir.json"'},
    )
