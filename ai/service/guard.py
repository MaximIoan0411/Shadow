"""Verificările făcute în cod după ce modelul a răspuns (nu doar cerute în prompt).

  * întrebările din afara sănătății în misiune primesc un răspuns fix;
  * un răspuns care numește un medicament, o doză sau un diagnostic e înlocuit cu recomandarea din catalog;
  * citările sunt doar sursele numerotate pe care răspunsul le-a folosit efectiv ([1], [2]…), renumerotate în
    ordinea în care apar, ca să se potrivească cu lista de surse din aplicație;
  * răspunsul se taie la o lungime maximă.
"""
import re

from rag.retrieve import Passage, tokens

from .schemas import AiCitation, AiOpenAlert, AiRecommendation

OFF_TOPIC = "I can only help with questions about your health on the mission."
NO_RECOMMENDATION = "I don't have a catalog recommendation for this question. If something worries you, notify the crew medical officer."
MAX_CHARS = 900
SNIPPET_CHARS = 280

HEALTH_WORDS = (
    "pulse", "heart", "sleep", "tired", "fatigue", "temperat", "fever", "pressure", "bone", "muscle", "radiat", "shelter",
    "alert", "typing", "stress", "symptom", "exercis", "workout", "dose", "dizzy", "health", "body", "pain", "cough",
    "immune", "infection", "mood", "reaction", "baseline", "medical", "doctor", "storm", "solar", "strength", "train",
    "ache", "head", "nause", "vomit", "rash", "sore", "breath", "chest", "eat", "meal", "food", "drink", "weight",
    "sick", "ill", "feel", "anxi", "lonel", "sad", "focus", "memory", "vision", "eye", "skin", "cold",
    "puls", "somn", "obosi", "tensiun", "inim", "oase", "mușchi", "muschi", "adăpost", "adapost", "tast", "febr",
    "simptom", "exerci", "doz", "ameț", "durere", "sănăt", "sanat",
    # întrebări despre propria stare, fără un cuvânt medical („How am I doing today?”)
    "how am i", "how do i look", "my data", "my stat", "my number", "my score", "my zone", "my status", "my result",
    "my progress", "my level", "improve", "wellbeing", "well-being",
)
# medicamente, doze și diagnostice: textul aplicației nu le numește niciodată
FORBIDDEN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|μg|iu)\b"
    r"|\b(?:take|taking)\s+(?:\d+|one|two)\s+(?:tablets?|pills?|capsules?)\b"
    r"|\b(?:paracetamol|acetaminophen|ibuprofen|aspirin|naproxen|antibiotics?|antihistamines?|antivirals?|melatonin|"
    r"zolpidem|modafinil|acyclovir|valacyclovir|bisphosphonates?|alendronate|zoledron\w*|potassium iodide|steroids?|"
    r"corticosteroids?|painkillers?|sleeping pills?)\b"
    r"|\byou (?:have|are suffering from|probably have|likely have|must have)\s+(?:a |an )?(?:infection|covid|flu|"
    r"influenza|virus|pneumonia|cancer|shingles|herpes|disease|disorder|syndrome)\b",
    re.I,
)
# „urgența ascunsă”: un răspuns care spune că totul e în regulă, cu o alertă deschisă
ALL_CLEAR = re.compile(
    r"\b(?:you are|you're|you seem|you look)\s+(?:doing\s+)?(?:well|fine|ok|okay|healthy|good|great)\b"
    r"|\beverything\s+(?:is|looks|seems)\s+(?:normal|fine|good|ok|okay)\b"
    r"|\bnothing\s+(?:to worry|needs to be done|to do)\b"
    r"|\bno\s+(?:need|reason)\s+to\s+(?:notify|worry|tell|inform)\b"
    r"|\ball\s+(?:your\s+)?(?:zones|values|data|readings)\s+(?:are\s+)?(?:within|normal)\b",
    re.I,
)
MARKER = re.compile(r"\[(\d{1,2})\]")
# „gândirea” modelului scăpată în răspuns (un bloc <think> neînchis, din cauza limitei de lungime)
THINKING_LEAK = re.compile(r"<think|thinking process|^\s*analy[sz]e the request", re.I | re.M)
# fără marcaje [n]: o sursă e considerată folosită dacă cel puțin atâtea cuvinte din răspuns vin din ea
MIN_OVERLAP = 0.3
MAX_IMPLICIT = 2
SENTENCE = re.compile(r"(?<=[.!?])\s+")


# fiecare cuvânt de mai sus e începutul unui cuvânt din întrebare („sleep” prinde „sleeping”, dar „ill” nu prinde „will”)
HEALTH = re.compile(r"\b(?:" + "|".join(map(re.escape, HEALTH_WORDS)) + ")", re.I)


def looks_off_topic(message: str, topic: str | None, passages: list[Passage]) -> bool:
    return topic is None and not passages and not HEALTH.search(message)


def violates_rules(answer: str) -> bool:
    return bool(FORBIDDEN.search(answer) or THINKING_LEAK.search(answer))


def hides_open_alert(answer: str, open_alerts: list[AiOpenAlert]) -> bool:
    """True = răspunsul spune că totul e în regulă, deși astronautul are o alertă deschisă."""
    return bool(open_alerts) and bool(ALL_CLEAR.search(answer))


def catalog_answer(rec: AiRecommendation | None, evidence: list[str]) -> str:
    """Reformularea fixă a recomandării: folosită fără model sau când răspunsul modelului încalcă regulile."""
    if rec is None:
        return NO_RECOMMENDATION
    observed = "; ".join(evidence) or "your data have moved away from your own normal"
    return f"What was observed: {observed}. What you can do now: {rec.action}"


def catalog_citation(rec: AiRecommendation) -> AiCitation:
    return AiCitation(title=rec.source_citation, url=rec.source_url, snippet=rec.trigger)


def open_alerts_answer(open_alerts: list[AiOpenAlert]) -> str:
    """La o întrebare generală, fără sursă: alertele deschise și ce spune catalogul pentru cea mai gravă."""
    top = open_alerts[0]
    names = "; ".join(f"{alert.title} (level {alert.level})" for alert in open_alerts)
    return f"Your open alerts: {names}. For the first one, the catalog says: {top.action}"


def fallback(rec: AiRecommendation | None, evidence: list[str], passages: list[Passage], question: str,
             open_alerts: list[AiOpenAlert] | None = None) -> tuple[str, list[AiCitation]]:
    """Răspunsul fără model (mock) sau în locul unui răspuns respins: recomandarea din catalog, altfel fraza cea mai
    potrivită din prima sursă găsită, altfel alertele deschise, altfel mesajul fix."""
    if rec is not None:
        return catalog_answer(rec, evidence), [catalog_citation(rec)]
    if not passages:
        return (open_alerts_answer(open_alerts) if open_alerts else NO_RECOMMENDATION), []
    top = passages[0]
    quote = snippet(top, question)
    return f"From the sources: {quote} [1]", [AiCitation(title=top.title, url=top.url, snippet=quote)]


def snippet(passage: Passage, answer: str) -> str:
    """Propoziția din fragment care se potrivește cel mai bine cu răspunsul."""
    wanted = set(tokens(answer))
    sentences = [part.strip() for part in SENTENCE.split(passage.text) if len(part.split()) >= 6] or [passage.text]
    best = max(sentences, key=lambda sentence: len(wanted & set(tokens(sentence))))
    return best if len(best) <= SNIPPET_CHARS else best[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"


def attach_citations(answer: str, passages: list[Passage], rec: AiRecommendation | None) -> tuple[str, list[AiCitation]]:
    order: list[int] = []
    for match in MARKER.finditer(answer):
        number = int(match.group(1))
        if 1 <= number <= len(passages) and number not in order:
            order.append(number)
    renumber = {old: new for new, old in enumerate(order, 1)}

    def rewrite(match: re.Match) -> str:
        number = int(match.group(1))
        return f"[{renumber[number]}]" if number in renumber else ""

    text = re.sub(r"\s+([.,;])", r"\1", MARKER.sub(rewrite, answer))
    citations = [AiCitation(title=passages[number - 1].title, url=passages[number - 1].url, snippet=snippet(passages[number - 1], text))
                 for number in order]
    if not citations and passages:
        # modelul n-a pus marcaje: se citează sursele din care vine o bună parte din răspuns
        words = set(tokens(text))
        shared = sorted(((len(words & set(tokens(passage.text))) / max(len(words), 1), number) for number, passage in enumerate(passages)), reverse=True)
        citations = [AiCitation(title=passages[number].title, url=passages[number].url, snippet=snippet(passages[number], text))
                     for overlap, number in shared[:MAX_IMPLICIT] if overlap >= MIN_OVERLAP]
    if not citations and rec is not None:
        citations = [catalog_citation(rec)]
    return text, citations


def clip(answer: str) -> str:
    text = re.sub(r"\*\*|__|^#+\s*|^\s*[-*]\s+", "", answer, flags=re.M).strip()
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > 0 else cut.rsplit(" ", 1)[0] + "…"
