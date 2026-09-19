from statistics import mean

def analyze_phrase(events):
    if not events:
        return {
            "event_count": 0,
            "pitch_range": 0,
            "avg_leap": 0.0,
            "large_leap_ratio": 0.0,
            "phase_counts": {},
            "cadence_resolves": False,
        }

    pitches=[e["midi"] for e in events]
    leaps=[abs(b-a) for a,b in zip(pitches,pitches[1:])]
    phase_counts={}
    for e in events:
        phase=e.get("phrase_phase","unknown")
        phase_counts[phase]=phase_counts.get(phase,0)+1

    cadence_resolves=False
    if len(events)>=2:
        a,b=events[-2],events[-1]
        cadence_resolves=(a.get("transform")=="cadential_2" and b.get("transform")=="cadential_1")

    return {
        "event_count": len(events),
        "pitch_range": max(pitches)-min(pitches),
        "avg_leap": mean(leaps) if leaps else 0.0,
        "large_leap_ratio": (
            sum(1 for x in leaps if x>7)/len(leaps) if leaps else 0.0
        ),
        "phase_counts": phase_counts,
        "cadence_resolves": cadence_resolves,
    }
